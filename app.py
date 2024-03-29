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
import threading
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
         {"role": "system", "content": "你是一位智能小幫手，協助處理問題，請說繁體中文，數學公式請直接寫純數字"},
         {"role": "user", "content": text},
    ]
    response = openai.ChatCompletion.create(engine="gpt-4-0125", messages=messages_text, temperature=0.9, max_tokens=1000,top_p=0.95)
    return response['choices'][0]['message']['content']


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
# 定義一個全局字典來追蹤每個用戶的呼叫次數
user_calls = {}

# 修改 handle_message 函數
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    # 獲取用戶 ID
    user_id = event.source.user_id
    # 獲取客戶端 IP 地址
    client_ip = request.remote_addr

    # 檢查用戶 ID 是否已在字典中
    if user_id in user_calls:
        # 為這個用戶增加呼叫次數
        user_calls[user_id] += 1
    else:
        # 如果沒有，初始化計數為 1
        user_calls[user_id] = 1

    # 檢查請求是否來自相同的客戶端 IP
    if request.remote_addr == client_ip:
        # 檢查這是否是該用戶的第一次或第二次呼叫
        if user_calls[user_id] <= 2:
            # 回復 '請稍等，我們正在處理您的訊息...'
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text='請稍等，我們正在處理您的訊息...')
            )
        # 啟動一個新的線程來處理請求
        threading.Thread(target=process_request, args=(event.message.text, user_id)).start()
    else:
        # 如果客戶端 IP 不匹配，發送錯誤訊息
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text='處理訊息時發生錯誤')
        )

# 其餘代碼保持不變

def process_request(msg, user_id):
    # 模擬伺服器處理時間
    # 計算完成後，發送回答
    GPT_answer = GPT_response(msg)
    # 使用 LINE Messaging API 的 push_message 方法發送訊息給用戶
    line_bot_api.push_message(user_id, TextSendMessage(text=GPT_answer))
        

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
