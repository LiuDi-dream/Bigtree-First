import os
import re
import json
import datetime
from openai import OpenAI
import config
from brain import memory_manager
from api import feishu_api


def load_system_prompt():
    """读取系统规则，优先 prompts/system_rules.md。"""
    fallback = "你是一个严谨的原神养成助手，回答要简洁、可执行。"
    try:
        with open(config.SYSTEM_RULES_FILE, "r", encoding="utf-8") as f:
            content = f.read().strip()
        return content or fallback
    except Exception:
        return fallback


def build_model_messages(system_prompt, env_context, history_messages):
    return [
        {"role": "system", "content": system_prompt},
        {"role": "system", "content": env_context},
        *history_messages,
    ]


def _make_client():
    token = os.getenv("GITHUB_TOKEN", "")
    return OpenAI(base_url="https://models.inference.ai.azure.com", api_key=token)


def ask_agent(messages, store, uid, open_id):
    """大模型思考、组装上下文、调用 OpenAI、解析 JSON 并发起审批或回复。"""
    try:
        system_prompt = load_system_prompt()

        # --- 日期偏移逻辑 ---
        business_time = datetime.datetime.now() - datetime.timedelta(hours=4)
        weekday_num = business_time.isoweekday()
        weekday_map = {1: "一", 2: "二", 3: "三", 4: "四", 5: "五", 6: "六", 7: "日"}
        today_str = f"星期{weekday_map[weekday_num]}"

        time_notice = f"\n\n【系统实时时间注入】：今天是{today_str}（已对齐凌晨4点刷新）。请严格核对材料的 schedule，不包含今天的绝对不能排期！同时严禁提及任何不在展柜 JSON 数据中的角色。"

        wallet = store.get("wallet", {"mora": 0, "exp_books": 0, "boss_mats": {}})
        boss_mats_str = "、".join([f"{k}: {v}个" for k, v in wallet.get("boss_mats", {}).items()]) or "无"

        wallet_notice = f"\n\n💰 【Agent 虚拟账本】当前已攒下：摩拉 {wallet['mora']}，经验书 {wallet['exp_books']} 本。\n📦 【已刷取Boss材料】：{boss_mats_str}\n（注：这仅代表系统近期的打工收益。规划前请严格对比材料缺口与已刷取数量，若已刷取数量 >= 缺口，必须停止安排该任务！）"

        model_messages = build_model_messages(
            system_prompt=system_prompt,
            env_context=store.get("env_context", "") + time_notice + wallet_notice,
            history_messages=messages,
        )

        client = _make_client()
        model_name = os.getenv("MODEL_NAME", "gpt-4o-mini")
        response = client.chat.completions.create(
            model=model_name,
            messages=model_messages,
            temperature=0.7,
        )
        ai_reply = response.choices[0].message.content

        # persist assistant reply
        messages.append({"role": "assistant", "content": ai_reply})
        messages = memory_manager.trim_history(messages)
        store["messages"] = messages
        memory_manager.save_chat_store(store)

        # 查找 JSON 指令
        json_match = re.search(r'```json\n(.*?)\n```', ai_reply, re.DOTALL)
        if json_match:
            try:
                bgi_cmd = json.loads(json_match.group(1))
                approval_msg = ai_reply + "\n\n" + "="*20 + "\n🛑 [系统拦截] 请确认是否执行上述计划？\n👉 回复 'y' 批准执行\n👉 回复 't' 仅测试\n👉 直接回复其他内容进行反驳/修改"
                feishu_api.send_feishu_msg(open_id, approval_msg)

                store["pending_task"] = {
                    "bgi_cmd": bgi_cmd,
                    "open_id": open_id,
                    "uid": uid,
                }
                memory_manager.save_chat_store(store)
            except json.JSONDecodeError:
                feishu_api.send_feishu_msg(open_id, ai_reply + "\n(解析 JSON 失败)")
        else:
            feishu_api.send_feishu_msg(open_id, ai_reply)

    except Exception as e:
        feishu_api.send_feishu_msg(open_id, f"❌ 大脑出错: {str(e)}")
