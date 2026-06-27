import os
import re
import json
import datetime
from openai import OpenAI
import config
from brain import memory_manager
from brain import rollback_manager
from api import feishu_api

# 🌟 引入我们刚刚写的圣遗物匹配模块
from skills.artifact_match import get_domain_by_user_intent

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
    """
    根据 .env 配置文件选择对应的大模型 API 提供商，返回 OpenAI 兼容客户端。
    支持: deepseek, github, openai, nvidia, custom, local
    """
    provider = os.getenv("LLM_PROVIDER", "github").lower()
    
    if provider == "deepseek":
        api_key = os.getenv("DEEPSEEK_API_KEY", "")
        if not api_key:
            raise ValueError("DEEPSEEK_API_KEY 未配置")
        base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
        return OpenAI(base_url=base_url, api_key=api_key)

    if provider == "github":
        token = os.getenv("GITHUB_TOKEN", "")
        if not token:
            raise ValueError("❌ GITHUB_TOKEN 未配置")
        return OpenAI(base_url="https://models.inference.ai.azure.com", api_key=token)
    
    elif provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY", "")
        if not api_key:
            raise ValueError("❌ OPENAI_API_KEY 未配置")
        base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        return OpenAI(base_url=base_url, api_key=api_key)
    
    elif provider == "nvidia":
        api_key = os.getenv("NVIDIA_API_KEY", "")
        if not api_key:
            raise ValueError("❌ NVIDIA_API_KEY 未配置")
        base_url = os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")
        return OpenAI(base_url=base_url, api_key=api_key)
    
    elif provider == "custom":
        api_key = os.getenv("CUSTOM_API_KEY", "")
        base_url = os.getenv("CUSTOM_BASE_URL", "")
        if not api_key or not base_url:
            raise ValueError("❌ CUSTOM_API_KEY 或 CUSTOM_BASE_URL 未配置")
        return OpenAI(base_url=base_url, api_key=api_key)
    
    elif provider == "local":
        base_url = os.getenv("LOCAL_BASE_URL", "")
        if not base_url:
            raise ValueError("❌ LOCAL_BASE_URL 未配置。请先启动本地模型服务 (如 ollama、vLLM 等)")
        api_key = os.getenv("LOCAL_API_KEY", "local")
        print(f"🏠 正在连接本地模型服务: {base_url}")
        return OpenAI(base_url=base_url, api_key=api_key)
    
    else:
        raise ValueError(f"❌ 不支持的 LLM_PROVIDER: {provider}，支持值: deepseek, github, openai, nvidia, custom, local")


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

        # 查找 JSON 指令
        json_match = re.search(r'```json\n(.*?)\n```', ai_reply, re.DOTALL)
        if json_match:
            try:
                bgi_cmd = json.loads(json_match.group(1))
                checkpoint_id = rollback_manager.create_checkpoint(
                    store,
                    reason="feishu_task_proposal",
                )
                
                # ==========================================
                # 🌟 核心拦截层：圣遗物意图转化
                # ==========================================
                if "energy_task" in bgi_cmd and bgi_cmd["energy_task"].get("action") == "run_artifact":
                    raw_target = bgi_cmd["energy_task"].get("target", "")
                    
                    # 动态读取原始 JSON 字典文件
                    # 动态读取原始 JSON 字典文件
                    raw_data_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "memory", "artifact_get_methods_raw.json")
                    real_domain = "未找到对应副本"
                    
                    try:
                        if os.path.exists(raw_data_path):
                            with open(raw_data_path, "r", encoding="utf-8") as f:
                                raw_json_data = json.load(f)
                            # 调用神器：转化为真实副本名
                            real_domain = get_domain_by_user_intent(raw_target, raw_json_data)
                        else:
                            print(f"⚠️ 找不到圣遗物原始字典: {raw_data_path}")
                    except Exception as e:
                        print(f"❌ 圣遗物映射发生错误: {e}")
                    
                    # 如果匹配成功，悄悄覆写 JSON 给外挂服用
                    if real_domain != "未找到对应副本":
                        print(f"🔄 圣遗物字典映射触发：将【{raw_target}】转化为副本【{real_domain}】")
                        bgi_cmd["energy_task"]["target"] = real_domain
                        bgi_cmd["energy_task"]["action"] = "run_domain" # 转化为物理外挂认识的指令
                    else:
                        print(f"⚠️ 无法映射圣遗物【{raw_target}】，将原样下发测试。")

                # 生成发送给用户的审批文本 (增加最终解析目标的提示)
                target_domain = bgi_cmd.get("energy_task", {}).get("target", "无")
                approval_msg = ai_reply + "\n\n" + "="*20 + f"\n🛑 [系统拦截] 请确认是否执行上述计划？\n🎯 最终解析目标：{target_domain}\n👉 回复 'y' 批准执行\n👉 回复 't' 仅测试\n👉 直接回复其他内容进行反驳/修改"
                
                # persist assistant reply after the checkpoint is safely captured
                messages.append({"role": "assistant", "content": ai_reply})
                messages = memory_manager.trim_history(messages)
                store["messages"] = messages
                memory_manager.save_chat_store(store)

                feishu_api.send_feishu_msg(open_id, approval_msg)

                store["pending_task"] = {
                    "bgi_cmd": bgi_cmd,
                    "open_id": open_id,
                    "uid": uid,
                    "rollback_checkpoint_id": checkpoint_id,
                }
                memory_manager.save_chat_store(store)
                
            except json.JSONDecodeError:
                messages.append({"role": "assistant", "content": ai_reply})
                messages = memory_manager.trim_history(messages)
                store["messages"] = messages
                memory_manager.save_chat_store(store)
                feishu_api.send_feishu_msg(open_id, ai_reply + "\n(解析 JSON 失败)")
        else:
            messages.append({"role": "assistant", "content": ai_reply})
            messages = memory_manager.trim_history(messages)
            store["messages"] = messages
            memory_manager.save_chat_store(store)
            feishu_api.send_feishu_msg(open_id, ai_reply)

    except Exception as e:
        feishu_api.send_feishu_msg(open_id, f"❌ 大脑出错: {str(e)}")
