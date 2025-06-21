from flask import Flask, request
import requests
import os

app = Flask(__name__)

VERIFY_TOKEN = "123456"  # رمز تحقق Webhook
PAGE_ACCESS_TOKEN = os.environ.get("PAGE_ACCESS_TOKEN")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")

# الرد الذكي من OpenRouter GPT-4 Turbo
def get_ai_reply(message):
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://yourappname.onrender.com",  # بدلها برابط موقعك على Render
        "X-Title": "Facebook Messenger AI Bot"
    }
    data = {
        "model": "openrouter/openai/gpt-4-turbo",
        "messages": [
            {"role": "user", "content": message}
        ]
    }
    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except Exception as e:
        return "⚠️ خطأ في الاتصال بـ OpenRouter"

# إرسال الرد للفيسبوك
def send_message(recipient_id, message_text):
    url = f"https://graph.facebook.com/v16.0/me/messages?access_token={PAGE_ACCESS_TOKEN}"
    headers = {"Content-Type": "application/json"}
    data = {
        "recipient": {"id": recipient_id},
        "message": {"text": message_text}
    }
    requests.post(url, headers=headers, json=data)

# التحقق من Webhook
@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        if request.args.get("hub.verify_token") == VERIFY_TOKEN:
            return request.args.get("hub.challenge")
        return "رمز التحقق غير صحيح"
    
    elif request.method == "POST":
        data = request.get_json()
        if data["object"] == "page":
            for entry in data["entry"]:
                for messaging_event in entry["messaging"]:
                    if messaging_event.get("message"):
                        sender_id = messaging_event["sender"]["id"]
                        message_text = messaging_event["message"].get("text")
                        if message_text:
                            ai_reply = get_ai_reply(message_text)
                            send_message(sender_id, ai_reply)
        return "OK", 200

# تشغيل التطبيق
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
