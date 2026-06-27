import copy
import datetime as _dt
import hashlib
import json
import os
import shutil
import uuid
from pathlib import Path

import config
from brain import memory_manager


BASE_DIR = Path(__file__).resolve().parent.parent
CHECKPOINT_ROOT = BASE_DIR / ".vibelign" / "checkpoints"
CHECKPOINT_JOURNAL = CHECKPOINT_ROOT / "journal.json"


def _default_journal():
    return {"pending": [], "committed": []}


def _load_journal():
    if not CHECKPOINT_JOURNAL.exists():
        return _default_journal()
    try:
        with open(CHECKPOINT_JOURNAL, "r", encoding="utf-8") as f:
            raw = json.load(f)
    except Exception:
        return _default_journal()

    if not isinstance(raw, dict):
        return _default_journal()

    pending = raw.get("pending", [])
    committed = raw.get("committed", [])
    if not isinstance(pending, list):
        pending = []
    if not isinstance(committed, list):
        committed = []
    return {"pending": pending, "committed": committed}


def _save_journal(journal):
    os.makedirs(CHECKPOINT_JOURNAL.parent, exist_ok=True)
    with open(CHECKPOINT_JOURNAL, "w", encoding="utf-8") as f:
        json.dump(journal, f, ensure_ascii=False, indent=2)


def _snapshot_targets():
    return [
        config.HISTORY_FILE,
        config.BGI_ONE_DRAGON_CONFIG,
        config.BGI_MAP_CONFIG,
        config.BGI_GLOBAL_CONFIG,
        config.BGI_BOSS_CONFIG,
    ]


def _safe_backup_name(target_path: str) -> str:
    digest = hashlib.sha1(target_path.encode("utf-8")).hexdigest()[:10]
    basename = Path(target_path).name or "snapshot"
    return f"{digest}_{basename}"


def _snapshot_dir(checkpoint_id: str) -> Path:
    return CHECKPOINT_ROOT / checkpoint_id


def _context_hash(store: dict) -> str:
    payload = {
        "uid": store.get("uid"),
        "env_context": store.get("env_context", ""),
        "messages": store.get("messages", []),
        "pending_task": store.get("pending_task"),
        "wallet": store.get("wallet", {}),
    }
    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    return hashlib.sha1(serialized.encode("utf-8")).hexdigest()


def create_checkpoint(store: dict, reason: str = "") -> str:
    """Capture both chat state and file state before a mutation."""
    journal = _load_journal()
    sequence = len(journal["pending"]) + len(journal["committed"]) + 1
    checkpoint_id = f"turn-{sequence:05d}_{uuid.uuid4().hex[:8]}"
    root = _snapshot_dir(checkpoint_id)
    files_root = root / "files"
    os.makedirs(files_root, exist_ok=True)

    store_copy = copy.deepcopy(store)
    with open(root / "store.json", "w", encoding="utf-8") as f:
        json.dump(store_copy, f, ensure_ascii=False, indent=2)

    file_entries = []
    for target in _snapshot_targets():
        target_path = Path(target)
        entry = {
            "target": str(target_path),
            "existed": target_path.exists(),
            "backup": None,
        }
        if target_path.exists():
            backup_name = _safe_backup_name(str(target_path))
            backup_path = files_root / backup_name
            os.makedirs(backup_path.parent, exist_ok=True)
            shutil.copy2(target_path, backup_path)
            entry["backup"] = str(backup_path)
        file_entries.append(entry)

    journal["pending"].append(
        {
            "id": checkpoint_id,
            "sequence": sequence,
            "created_at": _dt.datetime.now().isoformat(timespec="seconds"),
            "reason": reason,
            "status": "pending",
            "snapshot_dir": str(root),
            "store_backup": str(root / "store.json"),
            "context_hash": _context_hash(store_copy),
            "message_count": len(store_copy.get("messages", [])),
            "files": file_entries,
        }
    )
    _save_journal(journal)
    return checkpoint_id


def _find_entry(journal, checkpoint_id: str):
    for bucket in ("pending", "committed"):
        for idx, entry in enumerate(journal[bucket]):
            if entry.get("id") == checkpoint_id:
                return bucket, idx, entry
    return None, None, None


def commit_checkpoint(checkpoint_id: str) -> bool:
    if not checkpoint_id:
        return False

    journal = _load_journal()
    bucket, idx, entry = _find_entry(journal, checkpoint_id)
    if entry is None:
        return False

    if bucket == "committed":
        return True

    entry = dict(entry)
    entry["status"] = "committed"
    entry["committed_at"] = _dt.datetime.now().isoformat(timespec="seconds")
    journal["pending"].pop(idx)
    journal["committed"].append(entry)
    _save_journal(journal)
    return True


def discard_checkpoint(checkpoint_id: str) -> bool:
    if not checkpoint_id:
        return False

    journal = _load_journal()
    bucket, idx, entry = _find_entry(journal, checkpoint_id)
    if entry is None:
        return False

    journal[bucket].pop(idx)
    _save_journal(journal)
    _cleanup_snapshot_dir(entry)
    return True


def _cleanup_snapshot_dir(entry: dict):
    snapshot_dir = entry.get("snapshot_dir")
    if not snapshot_dir:
        return
    shutil.rmtree(snapshot_dir, ignore_errors=True)


def _restore_file_entry(file_entry: dict):
    target = Path(file_entry["target"])
    existed = bool(file_entry.get("existed"))
    backup = file_entry.get("backup")

    if existed:
        if not backup or not os.path.exists(backup):
            raise FileNotFoundError(f"Missing backup for {target}")
        os.makedirs(target.parent, exist_ok=True)
        shutil.copy2(backup, target)
    else:
        if target.exists():
            if target.is_file() or target.is_symlink():
                target.unlink()
            elif target.is_dir():
                shutil.rmtree(target, ignore_errors=True)


def rollback_last_committed():
    """Restore the latest committed checkpoint and remove it from history."""
    journal = _load_journal()
    if not journal["committed"]:
        return None

    entry = journal["committed"][-1]
    snapshot_dir = Path(entry["snapshot_dir"])
    store_backup = snapshot_dir / "store.json"

    for file_entry in entry.get("files", []):
        _restore_file_entry(file_entry)

    if not store_backup.exists():
        raise FileNotFoundError(f"Missing store backup: {store_backup}")
    with open(store_backup, "r", encoding="utf-8") as f:
        restored_store = json.load(f)

    memory_manager.save_chat_store(restored_store)
    journal["committed"].pop()
    _save_journal(journal)
    _cleanup_snapshot_dir(entry)
    return restored_store


def has_committed_checkpoint() -> bool:
    journal = _load_journal()
    return bool(journal["committed"])
