import os
import json
import config


def load_chat_store():
    """加载持久化对话存储。"""
    default_wallet = {"mora": 0, "exp_books": 0, "boss_mats": {}}

    HISTORY_FILE = config.HISTORY_FILE
    DEFAULT_UID = config.DEFAULT_UID

    if not os.path.exists(HISTORY_FILE):
        return {
            "uid": DEFAULT_UID,
            "env_context": "",
            "messages": [],
            "wallet": default_wallet,
            "pending_task": None,
        }

    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            raw = json.load(f)

        if isinstance(raw, list):
            return {
                "uid": DEFAULT_UID,
                "env_context": "",
                "messages": raw,
                "wallet": default_wallet,
                "pending_task": None,
            }

        loaded_wallet = raw.get("wallet", {})
        merged_wallet = {**default_wallet, **loaded_wallet}

        if not isinstance(merged_wallet.get("boss_mats"), dict):
            merged_wallet["boss_mats"] = {}

        pending_task = raw.get("pending_task")
        if isinstance(pending_task, dict):
            if not all(k in pending_task for k in ["bgi_cmd", "open_id", "uid"]):
                pending_task = None
        elif isinstance(pending_task, (list, tuple)) and len(pending_task) == 3:
            pending_task = {
                "bgi_cmd": pending_task[0],
                "open_id": pending_task[1],
                "uid": pending_task[2],
            }
        else:
            pending_task = None

        return {
            "uid": str(raw.get("uid", DEFAULT_UID)),
            "env_context": raw.get("env_context", ""),
            "messages": raw.get("messages", []),
            "wallet": merged_wallet,
            "pending_task": pending_task,
        }
    except Exception:
        return {
            "uid": DEFAULT_UID,
            "env_context": "",
            "messages": [],
            "wallet": default_wallet,
            "pending_task": None,
        }


def save_chat_store(store):
    """保存持久化对话存储。"""
    HISTORY_FILE = config.HISTORY_FILE
    os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(store, f, ensure_ascii=False, indent=2)


def trim_history(messages, max_messages=None):
    """限制历史长度，避免上下文无限增长。"""
    if max_messages is None:
        max_messages = config.MAX_HISTORY_MESSAGES
    if len(messages) <= max_messages:
        return messages
    return messages[-max_messages:]
