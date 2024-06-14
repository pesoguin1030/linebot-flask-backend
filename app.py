from flask import Flask, request, abort, jsonify
import firebase_admin
from firebase_admin import credentials, auth
import requests
from flask_cors import CORS
from linebot import LineBotApi
from linebot.exceptions import LineBotApiError
import warnings
from linebot import LineBotSdkDeprecatedIn30

# Initialize Firebase Admin
cred = credentials.Certificate(r"D:\碳權平台\linebot\flask-backend\carbon-sms-firebase-adminsdk-au55u-50b657eb5c.json")
firebase_admin.initialize_app(cred)

# This will serve as in-memory storage for development purposes only.
#users_data = {}

from linebot.v3 import (
    WebhookHandler
)
from linebot.v3.exceptions import (
    InvalidSignatureError
)
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    ReplyMessageRequest,
    TextMessage
)
from linebot.v3.webhooks import (
    MessageEvent,
    TextMessageContent
)


#baseURL = "http://localhost:4000"
baseURL = "http://192.168.137.1:4000"
sms_react_url  = "http://192.168.137.1:3000"


app = Flask(__name__)
#CORS(app, resources={r"/verify_and_get_phone": {"origins": "http://localhost:3000"}})
CORS(app, resources={r"/verify_and_get_phone": {"origins": "https://192.168.137.1:3001"}})

CORS(app)

configuration = Configuration(access_token='bLy2uCiWvwIzOxEKvwTwM9e3L+5QkH+1TB2rcESN+fRoflWZqI+pf7jGMks+LO9FcyxQmHrGK01HVUyvlIaGH9pWZ7Tgpauzpda/XfnFpjFJTDmblR+ga4ENSyHRAa1uoevyypVMAgirchnWn6vTLgdB04t89/1O/w1cDnyilFU=')
handler = WebhookHandler('0be1f3b412cb785db1d0af39ee94b81d')
line_bot_api = LineBotApi('bLy2uCiWvwIzOxEKvwTwM9e3L+5QkH+1TB2rcESN+fRoflWZqI+pf7jGMks+LO9FcyxQmHrGK01HVUyvlIaGH9pWZ7Tgpauzpda/XfnFpjFJTDmblR+ga4ENSyHRAa1uoevyypVMAgirchnWn6vTLgdB04t89/1O/w1cDnyilFU=')

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
        app.logger.info("Invalid signature. Please check your channel access token/channel secret.")
        abort(400)

    return 'OK'

@app.route('/verify_and_get_phone', methods=['POST'])
def verify_token():
    data = request.json
    token = data.get('token')
    #phone_number = data.get('phone_number')
    line_user_id = data.get('line_user_id')  # 直接从请求数据中获取 line_user_id
    try:

        # Check the token's validity using Firebase Admin SDK
        decoded_token = auth.verify_id_token(token)
        uid = decoded_token['uid']
        phone_number = decoded_token['phone_number']

        # Store uid and phone number in the dictionary
        #users_data[uid] = phone_number

        

        #print(f"UID: {uid}, Phone Number: {phone_number}")
        # 在这里调用另一个API
        activation_url = f"{baseURL}/carbonExternal/external/linebotActivation"
        phone_number = decoded_token['phone_number']  # 从前面解码的 token 中获取电话号码
        #line_user_id = decoded_token['line_user_id']  # 从前面解码的 token 中获取line user id

        # 檢查是否以'+886'開頭，並替換成'0'
        if phone_number.startswith('+886'):
            phone_number = '0' + phone_number[4:]

        payload = {'user_phone': phone_number,'line_user_id':line_user_id}  # 准备POST数据
        headers = {'Content-Type': 'application/json'}

        # 发送请求到目标API
        response = requests.post(activation_url, json=payload, headers=headers)
        response = response.json()

        # 确认响应
        if response["code"] == 200:
            #return jsonify({"message": "Token verified and linebot activated", "uid": uid}), 200
            return jsonify({"message": "Token verified and linebot activated", "uid": uid}), 200
        elif response["code"] == 404:
            return jsonify({"error": "Failed to activate linebot, phone number not found in db"}), response["code"]
        else:
            return jsonify({"error": "Failed to activate linebot"}), response["code"]


        #return jsonify({"message": "Token verified", "uid": uid}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):

    # 准备要发送给 Node.js API 的数据
    if event.message.text == "點數查詢":
        # userAddress = "0x921db87f8e0a889e8f1c245ebae96b179be12605"
        # userToken = "U2FsdGVkX1/gbFPx27PaO3n8LhUAaVV/G0uN+ujhiqQ="

        # 调用 Node.js API
        #response = getCurrentPoint(userAddress, userToken)
        response = requests.post(baseURL + "/carbonExternal/external/getPointByLineID", json={"line_user_id": event.source.user_id}).json()
        
        if response:
            # 处理 Node.js API 的响应
            #replyContent = "在錢包地址: \n" + userAddress + "\n中存有: " + response["message"] + " 點碳權點數。"
            if response["type"] == "balance":
                replyContent = "在錢包地址: \n" + response["address"] + "\n中存有: " + response["message"] + " 點碳權點數。"
            elif response["type"] == "temp_points":
                replyContent = "您目前尚未綁定錢包, 於手機號碼 " + str(response["phone"])+" 中存有 " + str(response["message"]) + " 點暫存點數"
            with ApiClient(configuration) as api_client:
                line_bot_api = MessagingApi(api_client)
                line_bot_api.reply_message_with_http_info(
                    ReplyMessageRequest(
                        reply_token=event.reply_token,
                        messages=[TextMessage(text=replyContent)]
                    )
                )
        else:
            print("Failed to call Node.js API")
    elif event.message.text == "手機綁定":
        user_id = event.source.user_id
        replyContent = "請點擊以下連結進行簡訊驗證\n"
        verification_url = rf"{sms_react_url}/{user_id}"
        with ApiClient(configuration) as api_client:
            line_bot_api = MessagingApi(api_client)
            line_bot_api.reply_message_with_http_info(
                ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=replyContent+verification_url)]
                )
            )


if __name__ == "__main__":
    warnings.filterwarnings("ignore", category=LineBotSdkDeprecatedIn30)
    app.run(host='0.0.0.0', port=5000, debug=True)
    #app.run()

# 需要有兩個public ip：
#
# 1. LineBot回覆訊息用的Webhook url
# 2. LineBot圖文選單中連結到碳權平台網頁的url
#
# 可使用ngrok
# 測試時手機有連到電腦的wifi，但可能不用
# 需要./ngrok http 192.168.0.105:5000  並且把 192.168.0.105:5000/callback 丟到LineBot後台 webhook url