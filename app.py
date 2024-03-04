from flask import Flask, request, abort

from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import *

#======python的函數庫==========
import tempfile, os
import datetime
import openai
import time
import traceback
#======python的函數庫==========

app = Flask(__name__)

static_tmp_path = os.path.join(os.path.dirname(__file__), 'static', 'tmp')
# Channel Access Token
line_bot_api = LineBotApi(os.getenv('CHANNEL_ACCESS_TOKEN'))
# Channel Secret
handler = WebhookHandler(os.getenv('CHANNEL_SECRET'))
# OPENAI 初始化設定
openai.api_key = os.getenv("AZURE_OPENAI_API_KEY")
openai.api_base = os.getenv("AZURE_OPENAI_ENDPOINT")
openai.api_type = 'azure'
openai.api_version = '2024-02-15-preview'
def GPT_response(text):
    # 接收回應
    print("處理中請稍後")
    messages_text=[
         {"role": "system", "content": "你是一位GPT智能小幫手，使用繁體中文"},
         {"role": "user", "content": text},
    ]
    response = openai.ChatCompletion.create(engine="gpt-4-turbo1", messages=messages_text, temperature=0.9, max_tokens=1000,top_p=0.95,   stream=None)
    # 重組回應
    for resp in response:
    # 檢查每個回應中是否有'choices'列表
        if 'choices' in resp:
            # 遍歷'choices'列表
            for choice in resp['choices']:
                # 檢查'choice'中是否有'delta'和'content'鍵
                if 'delta' in choice and 'content' in choice['delta']:
                    answer =choice['delta']['content']
    return answer


# 監聽所有來自 /callback 的 Post Request
@app.route("/callback", methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']
    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)
    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'


# 處理訊息
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    # 獲取客戶端 IP 地址
    client_ip = request.remote_addr
    msg = event.message.text
    user_id = event.source.user_id  # LINE 使用者的 ID
    if request.remote_addr==client_ip:
        GPT_answer = GPT_response(msg)
        line_bot_api.reply_message(event.reply_token, TextSendMessage(GPT_answer))
    else:
        line_bot_api.reply_message(event.reply_token, TextSendMessage('處理訊息時發生錯誤'))


        

@handler.add(PostbackEvent)
def handle_message(event):
    print(event.postback.data)


@handler.add(MemberJoinedEvent)
def welcome(event):
    uid = event.joined.members[0].user_id
    gid = event.source.group_id
    profile = line_bot_api.get_group_member_profile(gid, uid)
    name = profile.display_name
    message = TextSendMessage(text=f'{name}歡迎加入')
    line_bot_api.reply_message(event.reply_token, message)
        

if __name__ == "__main__":
    app.run()
