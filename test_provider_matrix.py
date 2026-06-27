#!/usr/bin/env python3
"""
Verify both model provider options and the rollback flow.

This script checks two things for each provider:
1. The OpenAI-compatible client can be created from the current env values.
2. The rollback manager can still restore both files and chat memory.
"""

from __future__ import annotations

import json
import os
import shutil
import tempfile
from contextlib import contextmanager
from pathlib import Path

import config
from brain import llm_brain, memory_manager, rollback_manager


@contextmanager
def patched_env(updates: dict[str, str]):
    original = {}
    missing = []
    for key, value in updates.items():
        if key in os.environ:
            original[key] = os.environ[key]
        else:
            missing.append(key)
        os.environ[key] = value
    try:
        yield
    finally:
        for key in updates:
            if key in original:
                os.environ[key] = original[key]
            elif key in os.environ:
                os.environ.pop(key, None)


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


def run_rollback_case(provider_name: str) -> None:
    base = Path(tempfile.mkdtemp(prefix=f"matrix-{provider_name}-", dir=str(Path.cwd())))
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
        checkpoint_id = rollback_manager.create_checkpoint(store, reason=f"matrix_{provider_name}")

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

        committed = rollback_manager.commit_checkpoint(checkpoint_id)
        _assert_equal(committed, True, f"{provider_name}: checkpoint should commit")

        restored = rollback_manager.rollback_last_committed()
        _assert_equal(restored["uid"], "u1", f"{provider_name}: uid should restore")
        _assert_equal(restored["env_context"], "before", f"{provider_name}: env_context should restore")
        _assert_equal(restored["messages"][0]["content"], "A", f"{provider_name}: messages should restore")
        _assert_equal(restored["wallet"]["mora"], 1, f"{provider_name}: wallet should restore")
        _assert_equal(restored["pending_task"]["bgi_cmd"], "one", f"{provider_name}: pending_task should restore")
        _assert_equal(rollback_manager.has_committed_checkpoint(), False, f"{provider_name}: committed journal should clear")

        persisted_store = json.loads(Path(config.HISTORY_FILE).read_text(encoding="utf-8"))
        _assert_equal(persisted_store, restored, f"{provider_name}: persisted store should match restored store")
        _assert_equal(Path(config.BGI_ONE_DRAGON_CONFIG).read_text(encoding="utf-8"), "file-a-before", f"{provider_name}: one-dragon file should restore")
        _assert_equal(Path(config.BGI_MAP_CONFIG).read_text(encoding="utf-8"), "file-b-before", f"{provider_name}: map file should restore")
        _assert_equal(Path(config.BGI_GLOBAL_CONFIG).read_text(encoding="utf-8"), "file-c-before", f"{provider_name}: global file should restore")
        _assert_equal(Path(config.BGI_BOSS_CONFIG).exists(), False, f"{provider_name}: missing boss file should stay removed")

        print(f"[PASS] rollback flow: {provider_name}")
    finally:
        config.HISTORY_FILE = original_paths["history"]
        config.BGI_ONE_DRAGON_CONFIG = original_paths["one_dragon"]
        config.BGI_MAP_CONFIG = original_paths["map"]
        config.BGI_GLOBAL_CONFIG = original_paths["global"]
        config.BGI_BOSS_CONFIG = original_paths["boss"]
        rollback_manager.CHECKPOINT_ROOT = original_paths["checkpoint_root"]
        rollback_manager.CHECKPOINT_JOURNAL = original_paths["checkpoint_journal"]
        shutil.rmtree(base, ignore_errors=True)


def main() -> None:
    provider_matrix = [
        (
            "github",
            {
                "LLM_PROVIDER": "github",
                "GITHUB_TOKEN": "dummy-github-token-for-validation",
            },
        ),
        (
            "deepseek",
            {
                "LLM_PROVIDER": "deepseek",
                "DEEPSEEK_API_KEY": "dummy-key-for-validation",
                "DEEPSEEK_BASE_URL": "https://api.deepseek.com",
            },
        ),
    ]

    for provider_name, env_updates in provider_matrix:
        with patched_env(env_updates):
            client = llm_brain._make_client()
            _assert_equal(type(client).__name__, "OpenAI", f"{provider_name}: client should be OpenAI compatible")
            print(f"[PASS] client creation: {provider_name}")
            run_rollback_case(provider_name)

    print("Provider matrix rollback test passed.")


if __name__ == "__main__":
    main()
