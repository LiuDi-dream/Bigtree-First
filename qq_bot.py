from __future__ import annotations

import os

from flask import Flask, jsonify, request

from app_core import dispatch_command, provider_snapshot, rollback_snapshot, store_snapshot


app = Flask(__name__)


def _parse_payload() -> tuple[str, str]:
    data = request.get_json(silent=True) or {}
    text = (data.get("text") or request.form.get("text") or request.args.get("text") or "").strip()
    user_id = (data.get("user_id") or request.form.get("user_id") or request.args.get("user_id") or "qq-user").strip()
    return user_id, text


@app.get("/health")
def health():
    return jsonify(
        {
            "ok": True,
            "service": "qq-bot-bridge",
            "provider": provider_snapshot(),
            "store": store_snapshot(),
            "rollback": rollback_snapshot(),
        }
    )


@app.post("/qq/webhook")
@app.post("/message")
def webhook():
    user_id, text = _parse_payload()
    if not text:
        return jsonify({"ok": False, "user_id": user_id, "reply": "empty text"}), 400

    result = dispatch_command(text)
    return jsonify(
        {
            "ok": result.ok,
            "user_id": user_id,
            "command": result.title,
            "reply": result.message,
            "payload": result.payload,
        }
    )


@app.get("/")
def index():
    return jsonify(
        {
            "service": "qq-bot-bridge",
            "hint": "POST /qq/webhook with JSON: {'user_id': '...', 'text': 'status'}",
            "provider": provider_snapshot(),
        }
    )


if __name__ == "__main__":
    port = int(os.getenv("QQ_BOT_PORT", "8088"))
    print(f"QQ message bridge running on http://127.0.0.1:{port}")
    app.run(host="127.0.0.1", port=port, debug=True)
