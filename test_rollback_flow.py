#!/usr/bin/env python3
"""
Regression test for the client rollback flow.

This script exercises the rollback manager end to end:
1. Capture a checkpoint for chat memory and tracked config files.
2. Mutate those files and the persisted memory.
3. Commit the checkpoint.
4. Roll back the committed checkpoint.
5. Verify both file state and chat memory return to the snapshot.

Run it with:
  .\\venv\\Scripts\\python.exe test_rollback_flow.py
"""

from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path

import config
from brain import memory_manager, rollback_manager


def _write_json(path: str, payload) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_text(path: str, content: str) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")


def _assert_equal(actual, expected, message: str) -> None:
    if actual != expected:
        raise AssertionError(f"{message}\nExpected: {expected!r}\nActual:   {actual!r}")


def main() -> None:
    base = Path(tempfile.mkdtemp(prefix="rollback-flow-", dir=str(Path.cwd())))
    original_paths = {
        "history": config.HISTORY_FILE,
        "one_dragon": config.BGI_ONE_DRAGON_CONFIG,
        "map": config.BGI_MAP_CONFIG,
        "global": config.BGI_GLOBAL_CONFIG,
        "boss": config.BGI_BOSS_CONFIG,
        "checkpoint_root": rollback_manager.CHECKPOINT_ROOT,
        "checkpoint_journal": rollback_manager.CHECKPOINT_JOURNAL,
    }

    try:
        config.HISTORY_FILE = str(base / "memory" / "chat_context.json")
        config.BGI_ONE_DRAGON_CONFIG = str(base / "BetterGI" / "User" / "OneDragon" / "default_test.json")
        config.BGI_MAP_CONFIG = str(base / "BetterGI" / "User" / "ScriptGroup" / "map_assets.json")
        config.BGI_GLOBAL_CONFIG = str(base / "BetterGI" / "User" / "config.json")
        config.BGI_BOSS_CONFIG = str(base / "BetterGI" / "User" / "boss_assets" / "config" / "config.json")
        rollback_manager.CHECKPOINT_ROOT = base / ".vibelign" / "checkpoints"
        rollback_manager.CHECKPOINT_JOURNAL = rollback_manager.CHECKPOINT_ROOT / "journal.json"

        initial_store = {
            "uid": "u1",
            "env_context": "before",
            "messages": [{"role": "user", "content": "A"}],
            "wallet": {"mora": 1, "exp_books": 2, "boss_mats": {"x": 1}},
            "pending_task": {"bgi_cmd": "one", "open_id": "o", "uid": "u1"},
        }

        _write_json(config.HISTORY_FILE, initial_store)
        _write_text(config.BGI_ONE_DRAGON_CONFIG, "file-a-before")
        _write_text(config.BGI_MAP_CONFIG, "file-b-before")
        _write_text(config.BGI_GLOBAL_CONFIG, "file-c-before")
        if Path(config.BGI_BOSS_CONFIG).exists():
            Path(config.BGI_BOSS_CONFIG).unlink()

        store = memory_manager.load_chat_store()
        checkpoint_id = rollback_manager.create_checkpoint(store, reason="integration_test")

        # Mutate tracked files and the persisted memory after the snapshot.
        _write_json(
            config.HISTORY_FILE,
            {
                "uid": "u2",
                "env_context": "after",
                "messages": [{"role": "assistant", "content": "B"}],
                "wallet": {"mora": 999, "exp_books": 0, "boss_mats": {}},
                "pending_task": None,
            },
        )
        _write_text(config.BGI_ONE_DRAGON_CONFIG, "file-a-after")
        _write_text(config.BGI_MAP_CONFIG, "file-b-after")
        _write_text(config.BGI_GLOBAL_CONFIG, "file-c-after")
        _write_text(config.BGI_BOSS_CONFIG, "file-d-after")

        # Commit + rollback should restore the snapshot and clear the committed entry.
        committed = rollback_manager.commit_checkpoint(checkpoint_id)
        _assert_equal(committed, True, "Checkpoint should commit successfully")

        restored = rollback_manager.rollback_last_committed()
        _assert_equal(restored["uid"], "u1", "Rolled back store should restore uid")
        _assert_equal(restored["env_context"], "before", "Rolled back store should restore env_context")
        _assert_equal(restored["messages"][0]["content"], "A", "Rolled back store should restore messages")
        _assert_equal(restored["wallet"]["mora"], 1, "Rolled back store should restore wallet")
        _assert_equal(restored["pending_task"]["bgi_cmd"], "one", "Rolled back store should restore pending_task")
        _assert_equal(rollback_manager.has_committed_checkpoint(), False, "Committed history should be empty after rollback")

        persisted_store = json.loads(Path(config.HISTORY_FILE).read_text(encoding="utf-8"))
        _assert_equal(persisted_store, restored, "Persisted store should match returned store")
        _assert_equal(Path(config.BGI_ONE_DRAGON_CONFIG).read_text(encoding="utf-8"), "file-a-before", "OneDragon file should restore")
        _assert_equal(Path(config.BGI_MAP_CONFIG).read_text(encoding="utf-8"), "file-b-before", "Map file should restore")
        _assert_equal(Path(config.BGI_GLOBAL_CONFIG).read_text(encoding="utf-8"), "file-c-before", "Global file should restore")
        _assert_equal(Path(config.BGI_BOSS_CONFIG).exists(), False, "Missing file should be removed again")

        print("Rollback regression test passed.")
        print(f"Checkpoint: {checkpoint_id}")
        print(f"Workspace: {base}")
    finally:
        config.HISTORY_FILE = original_paths["history"]
        config.BGI_ONE_DRAGON_CONFIG = original_paths["one_dragon"]
        config.BGI_MAP_CONFIG = original_paths["map"]
        config.BGI_GLOBAL_CONFIG = original_paths["global"]
        config.BGI_BOSS_CONFIG = original_paths["boss"]
        rollback_manager.CHECKPOINT_ROOT = original_paths["checkpoint_root"]
        rollback_manager.CHECKPOINT_JOURNAL = original_paths["checkpoint_journal"]
        shutil.rmtree(base, ignore_errors=True)


if __name__ == "__main__":
    main()
