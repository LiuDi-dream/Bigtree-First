import os
import json
import lark_oapi as lark
from lark_oapi.api.im.v1 import *
from lark_oapi.adapter.flask import *


def send_feishu_msg(open_id: str, text: str):
    """向飞书用户发消息的封装函数。"""
    try:
        APP_ID = os.getenv("FEISHU_APP_ID", "")
        APP_SECRET = os.getenv("FEISHU_APP_SECRET", "")
        lark_client = lark.Client.builder().app_id(APP_ID).app_secret(APP_SECRET).build()
        request = CreateMessageRequest.builder().receive_id_type("open_id") \
            .request_body(CreateMessageRequestBody.builder().receive_id(open_id).msg_type("text").content(json.dumps({"text": text})).build()).build()
        lark_client.im.v1.message.create(request)
    except Exception as e:
        print(f"❌ 飞书消息发送失败: {e}")
