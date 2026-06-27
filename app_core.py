from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dotenv import set_key

import config
from brain import memory_manager, rollback_manager
from skills.env_reader import fetch_enka_data


PROVIDER_SPECS = {
    "github": {
        "label": "GitHub",
        "required_keys": ["GITHUB_TOKEN"],
        "optional_keys": ["MODEL_NAME"],
        "hint": "GitHub Models 通道",
    },
    "deepseek": {
        "label": "DeepSeek",
        "required_keys": ["DEEPSEEK_API_KEY"],
        "optional_keys": ["DEEPSEEK_BASE_URL", "MODEL_NAME"],
        "hint": "DeepSeek 兼容接口",
    },
}

CORE_COMMANDS = {
    "status",
    "rollback",
    "refresh",
    "history",
    "clear",
}


@dataclass
class CoreResult:
    ok: bool
    title: str
    message: str
    payload: dict[str, Any] | None = None


def _env_file() -> str:
    return config.ENV_FILE if hasattr(config, "ENV_FILE") else os.path.join(config.BASE_DIR, ".env")


def _ensure_env_file() -> str:
    env_file = _env_file()
    Path(env_file).parent.mkdir(parents=True, exist_ok=True)
    if not Path(env_file).exists():
        Path(env_file).write_text("", encoding="utf-8")
    return env_file


def _mask_secret(value: str | None) -> str:
    if not value:
        return "未配置"
    if len(value) <= 6:
        return value[0] + "*" * max(0, len(value) - 1)
    return f"{value[:3]}…{value[-2:]}"


def current_provider() -> str:
    return os.getenv("LLM_PROVIDER", "github").strip().lower() or "github"


def provider_snapshot() -> dict[str, Any]:
    provider = current_provider()
    github_token = os.getenv("GITHUB_TOKEN", "")
    deepseek_api_key = os.getenv("DEEPSEEK_API_KEY", "")
    deepseek_base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    model_name = os.getenv("MODEL_NAME", "gpt-4o-mini")
    return {
        "provider": provider,
        "provider_label": PROVIDER_SPECS.get(provider, {"label": provider}).get("label", provider),
        "provider_hint": PROVIDER_SPECS.get(provider, {}).get("hint", ""),
        "github_token_masked": _mask_secret(github_token),
        "deepseek_api_key_masked": _mask_secret(deepseek_api_key),
        "deepseek_base_url": deepseek_base_url,
        "model_name": model_name,
        "github_ready": bool(github_token),
        "deepseek_ready": bool(deepseek_api_key),
    }


def _save_env_value(key: str, value: str) -> None:
    env_file = _ensure_env_file()
    set_key(env_file, key, value, quote_mode="always")
    os.environ[key] = value


def set_provider(provider: str, *, github_token: str = "", deepseek_api_key: str = "", deepseek_base_url: str = "", model_name: str = "") -> CoreResult:
    provider = provider.strip().lower()
    if provider not in PROVIDER_SPECS:
        return CoreResult(False, "provider", f"不支持的 provider: {provider}")

    if provider == "github":
        token = github_token.strip() or os.getenv("GITHUB_TOKEN", "").strip()
        if not token:
            return CoreResult(False, "provider", "切换到 GitHub 需要先配置 GITHUB_TOKEN")
        _save_env_value("LLM_PROVIDER", "github")
        _save_env_value("GITHUB_TOKEN", token)
        if model_name.strip():
            _save_env_value("MODEL_NAME", model_name.strip())
        return CoreResult(True, "provider", "已切换到 GitHub 模型通道", provider_snapshot())

    token = deepseek_api_key.strip() or os.getenv("DEEPSEEK_API_KEY", "").strip()
    if not token:
        return CoreResult(False, "provider", "切换到 DeepSeek 需要先配置 DEEPSEEK_API_KEY")

    base_url = deepseek_base_url.strip() or os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    _save_env_value("LLM_PROVIDER", "deepseek")
    _save_env_value("DEEPSEEK_API_KEY", token)
    _save_env_value("DEEPSEEK_BASE_URL", base_url)
    if model_name.strip():
        _save_env_value("MODEL_NAME", model_name.strip())
    return CoreResult(True, "provider", "已切换到 DeepSeek 模型通道", provider_snapshot())


def load_store() -> dict[str, Any]:
    return memory_manager.load_chat_store()


def save_store(store: dict[str, Any]) -> None:
    memory_manager.save_chat_store(store)


def set_uid(uid: str) -> CoreResult:
    cleaned = str(uid).strip()
    if not cleaned:
        return CoreResult(False, "uid", "UID 不能为空")
    if not cleaned.isdigit():
        return CoreResult(False, "uid", "UID 只能包含数字")
    store = load_store()
    store["uid"] = cleaned
    save_store(store)
    return CoreResult(True, "uid", f"UID 已绑定为 {cleaned}", {"uid": cleaned})


def refresh_env_context(uid: str) -> str:
    env_data = fetch_enka_data(uid)
    return f"以下是玩家 UID {uid} 的最新展柜数据（JSON）：\n{env_data}"


def store_snapshot() -> dict[str, Any]:
    store = load_store()
    return {
        "uid": store.get("uid", config.DEFAULT_UID),
        "message_count": len(store.get("messages", [])),
        "has_env_context": bool(store.get("env_context")),
        "has_pending_task": bool(store.get("pending_task")),
        "wallet": store.get("wallet", {}),
    }


def rollback_snapshot() -> dict[str, Any]:
    summary = rollback_manager.get_checkpoint_summary()
    return {
        "pending_count": summary.get("pending_count", 0),
        "committed_count": summary.get("committed_count", 0),
        "has_committed": summary.get("has_committed", False),
        "latest_committed": summary.get("latest_committed"),
        "latest_pending": summary.get("latest_pending"),
    }


def clear_memory() -> CoreResult:
    store = {
        "uid": config.DEFAULT_UID,
        "env_context": "",
        "messages": [],
        "wallet": {"mora": 0, "exp_books": 0, "boss_mats": {}},
        "pending_task": None,
    }
    save_store(store)
    return CoreResult(True, "clear", "记忆已清空", store_snapshot())


def _format_status() -> str:
    provider = provider_snapshot()
    store = store_snapshot()
    rollback = rollback_snapshot()
    return (
        f"Provider: {provider['provider_label']} ({provider['provider']})\n"
        f"Model: {provider['model_name']}\n"
        f"UID: {store['uid']}\n"
        f"Messages: {store['message_count']}\n"
        f"Pending task: {'yes' if store['has_pending_task'] else 'no'}\n"
        f"Committed checkpoints: {rollback['committed_count']}\n"
        f"Pending checkpoints: {rollback['pending_count']}"
    )


def dispatch_command(text: str) -> CoreResult:
    raw = (text or "").strip()
    if not raw:
        return CoreResult(False, "empty", "输入为空")

    parts = raw.split()
    command = parts[0].lower()

    if command in ("status", "状态"):
        return CoreResult(True, "status", _format_status(), {"provider": provider_snapshot(), "store": store_snapshot(), "rollback": rollback_snapshot()})

    if command == "rollback":
        restored = rollback_manager.rollback_last_committed()
        if restored is None:
            return CoreResult(False, "rollback", "当前没有可回滚的已提交快照")
        return CoreResult(True, "rollback", f"已回滚，UID={restored.get('uid', config.DEFAULT_UID)}", restored)

    if command == "refresh":
        store = load_store()
        uid = str(store.get("uid", config.DEFAULT_UID))
        try:
            store["env_context"] = refresh_env_context(uid)
            save_store(store)
            return CoreResult(True, "refresh", f"展柜上下文已刷新，UID={uid}", {"uid": uid})
        except Exception as exc:
            return CoreResult(False, "refresh", f"刷新失败: {exc}")

    if command == "history":
        store = load_store()
        messages = store.get("messages", [])
        return CoreResult(True, "history", f"当前历史消息数量: {len(messages)}", {"messages": messages})

    if command == "clear":
        return clear_memory()

    if command == "provider" and len(parts) >= 2:
        provider = parts[1]
        kwargs: dict[str, str] = {}
        if provider == "github" and len(parts) >= 3:
            kwargs["github_token"] = parts[2]
        if provider == "deepseek":
            if len(parts) >= 3:
                kwargs["deepseek_api_key"] = parts[2]
            if len(parts) >= 4:
                kwargs["deepseek_base_url"] = parts[3]
        result = set_provider(provider, **kwargs)
        return result

    if command == "uid" and len(parts) >= 2:
        store = load_store()
        store["uid"] = parts[1]
        save_store(store)
        return CoreResult(True, "uid", f"UID 已切换为 {parts[1]}", {"uid": parts[1]})

    return CoreResult(
        False,
        "unknown",
        "未知命令。可用命令: status, rollback, refresh, history, clear, provider <github|deepseek>, uid <value>",
    )
