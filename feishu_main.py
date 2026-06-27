import os

# 🌟 强行让飞书域名走直连，无视本地 Clash 代理，必须放在最上面！
os.environ["NO_PROXY"] = "open.feishu.cn,*.feishu.cn"
os.environ["no_proxy"] = "open.feishu.cn,*.feishu.cn"

import json
import threading
import time
import sys
from flask import Flask
from dotenv import load_dotenv
import lark_oapi as lark
from lark_oapi.api.im.v1 import *
from lark_oapi.adapter.flask import *

# 引入我们刚才拆分出来的各个核心模块
import config
from brain import memory_manager, llm_brain, rollback_manager
from skills import bgi_controller
from api import feishu_api
from skills.env_reader import fetch_enka_data

load_dotenv()

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# ================= 飞书配置与缓存区 =================
VERIFICATION_TOKEN = os.getenv("FEISHU_VERIFICATION_TOKEN", "")
ENCRYPT_KEY = ""  # 没开加密留空

# 🌟 消息去重：记录最近处理过的消息ID和时间戳，防止飞书重试导致重复处理
PROCESSED_MESSAGES = {}
MESSAGE_TTL = 300 

app = Flask(__name__)

# ================= 辅助函数 =================
def is_message_processed(message_id: str) -> bool:
    """检查消息是否已处理过（去重机制）"""
    current_time = time.time()
    
    # 清理过期的消息记录
    expired_ids = [mid for mid, ts in PROCESSED_MESSAGES.items() if current_time - ts > MESSAGE_TTL]
    for mid in expired_ids:
        del PROCESSED_MESSAGES[mid]
    
    if message_id in PROCESSED_MESSAGES:
        print(f"⚠️ 消息 {message_id} 已处理过，跳过重复处理")
        return True
    
    PROCESSED_MESSAGES[message_id] = current_time
    return False

def refresh_env_context(uid):
    """拉取最新展柜数据并组装上下文字符串"""
    env_data = fetch_enka_data(uid)
    data_str = json.dumps(env_data, ensure_ascii=False)
    return f"以下是玩家 UID {uid} 的最新展柜数据（JSON）：\n{data_str}"

# ================= 核心路由与拦截 =================
def _handle_message_impl(msg_content: str, open_id: str) -> None:
    """消息的实际路由处理器"""
    store = memory_manager.load_chat_store()
    uid = store.get("uid", config.DEFAULT_UID)
    messages = store.get("messages", [])

    # 首次启动或被清理后，自动拉取展柜数据
    if not store.get("env_context"):
        try:
            store["env_context"] = refresh_env_context(uid)
        except Exception as e:
            store["env_context"] = f"展柜数据暂不可用：{e}"

    # 🌟 1. 处理系统快捷指令
    user_input = msg_content.lower()

    if user_input in ['exit', 'quit', '退出']:
        feishu_api.send_feishu_msg(open_id, "👋 飞书服务端运行中，无需手动退出。")
        return

    if user_input == 'clear':
        store = {"uid": uid, "env_context": "", "messages": [], "wallet": {"mora": 0, "exp_books": 0, "boss_mats": {}}, "pending_task": None}
        if os.path.exists(config.HISTORY_FILE):
            os.remove(config.HISTORY_FILE)
        print("🧹 记忆已清空。")
        feishu_api.send_feishu_msg(open_id, "🧹 记忆已清空。")
        return

    if user_input == 'rollback':
        restored = rollback_manager.rollback_last_committed()
        if restored is None:
            feishu_api.send_feishu_msg(open_id, "↩️ 当前没有可回滚的已提交快照。")
            return
        feishu_api.send_feishu_msg(open_id, "↩️ 已同步回滚代码快照与对话记忆。")
        return

    if user_input == 'refresh':
        print("🔄 正在刷新最新展柜上下文...")
        try:
            store["env_context"] = refresh_env_context(uid)
            memory_manager.save_chat_store(store)
            feishu_api.send_feishu_msg(open_id, "✅ 展柜上下文已刷新。")
        except Exception as e:
            feishu_api.send_feishu_msg(open_id, f"❌ 刷新失败: {e}")
        return

    if user_input == 'history':
        feishu_api.send_feishu_msg(open_id, f"📚 当前历史消息数：{len(messages)}")
        return

    # 🌟 2. 检查是否有待审批的自动化任务
    pending_task = store.get("pending_task")
    if pending_task:
        bgi_cmd = pending_task.get("bgi_cmd")
        stored_uid = pending_task.get("uid", uid)
        rollback_checkpoint_id = pending_task.get("rollback_checkpoint_id")
        
        if user_input in ['y', 't', 'yes', '确认', '执行']:
            decision_lower = 'y' if user_input in ['y', 'yes', '确认', '执行'] else 't'
            print(f"🛑 收到审批结果: {decision_lower}")
            feishu_api.send_feishu_msg(open_id, "⚙️ 指令已确认，正在下发配置给 BetterGI...")
            
            store["pending_task"] = None
            memory_manager.save_chat_store(store)
            
            # 将物理外挂执行放入后台线程
            threading.Thread(
                target=bgi_controller.execute_bgi_task,
                args=(bgi_cmd, decision_lower, store, open_id, stored_uid, rollback_checkpoint_id),
            ).start()
            return
        else:
            print("\n🚫 审批已驳回。正在将你的要求反馈给大脑重新规划...")
            if rollback_checkpoint_id:
                rollback_manager.discard_checkpoint(rollback_checkpoint_id)
            store["pending_task"] = None
            feedback_msg = f"我拒绝了刚才的执行申请。我的新要求是：{msg_content}。请根据我的新要求重新评估，并输出新的 JSON 指令。"
            messages.append({"role": "user", "content": feedback_msg})
            messages = memory_manager.trim_history(messages)
            store["messages"] = messages
            memory_manager.save_chat_store(store)
            feishu_api.send_feishu_msg(open_id, "🚫 计划已撤销。正在根据您的要求重新评估...")
            # 不 return，继续走到下方的大模型思考逻辑

    # 🌟 3. 普通聊天，存入记忆并交给大脑思考
    if not msg_content:
        return

    if not pending_task:
        messages.append({"role": "user", "content": msg_content})
        messages = memory_manager.trim_history(messages)
        store["messages"] = messages
        memory_manager.save_chat_store(store)

    print("🧠 正在唤醒大模型思考...")
    # 把大模型思考抛到后台，立刻让飞书请求返回 200 OK
    threading.Thread(target=llm_brain.ask_agent, args=(messages, store, uid, open_id)).start()


def process_message_async(data: P2ImMessageReceiveV1) -> None:
    """异步入口，防止阻塞飞书 Webhook 响应"""
    try:
        msg_content = json.loads(data.event.message.content).get("text", "").strip()
        open_id = data.event.sender.sender_id.open_id
        message_id = data.event.message.message_id
        
        if is_message_processed(message_id):
            return
        
        print(f"\n👤 旅行者 (飞书): {msg_content}")
        _handle_message_impl(msg_content, open_id)
    except Exception as e:
        print(f"❌ 异步处理消息时出错: {e}")

# ================= Flask 路由绑定 =================
def handle_message(data: P2ImMessageReceiveV1, **kwargs) -> None:
    threading.Thread(target=process_message_async, args=(data,), daemon=True).start()

event_handler = lark.EventDispatcherHandler.builder(ENCRYPT_KEY, VERIFICATION_TOKEN, lark.LogLevel.DEBUG) \
    .register_p2_im_message_receive_v1(handle_message) \
    .build()

@app.route("/webhook/event", methods=["POST"])
def webhook_event():
    resp = event_handler.do(parse_req())
    return parse_resp(resp)

if __name__ == "__main__":
    print("🚀 原神智能体启动中...")
    print("\n" + "="*40)
    print("✨ Agent 架构重构完成！飞书服务端已启动。")
    print("✨ 已启用：高内聚低耦合模块化 + 异步不阻塞。")
    print("="*40 + "\n")
    app.run(port=5000)
