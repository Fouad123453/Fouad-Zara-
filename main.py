from flask import Flask, request
import requests
import os

app = Flask(__name__)

VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN")
PAGE_ACCESS_TOKEN = os.environ.get("PAGE_ACCESS_TOKEN")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        # التحقق من الـ Webhook
        if request.args.get("hub.verify_token") == VERIFY_TOKEN:
            return request.args.get("hub.challenge")
        return "الرمز غير صحيح"
    
    elif request.method == "POST":
        data = request.get_json()
        if data.get("object") == "page":
            for entry in data.get("entry", []):
                messaging = entry.get("messaging", [])
                for message in messaging:
                    sender_id = message["sender"]["id"]
                    if "message" in message and "text" in message["message"]:
                        user_msg = message["message"]["text"]
                        bot_reply = ask_openai(user_msg)
                        send_message(sender_id, bot_reply)
        return "OK", 200

def ask_openai(user_input):
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "gpt-3.5-turbo",
        "messages": [{"role": "user", "content": user_input}]
    }
    response = requests.post(url, headers=headers, json=payload)
    if response.status_code == 200:
        return response.json()["choices"][0]["message"]["content"].strip()
    else:
        return "⚠️ خطأ في الاتصال بـ OpenAI"

def send_message(recipient_id, text):
    url = f"https://graph.facebook.com/v17.0/me/messages?access_token={PAGE_ACCESS_TOKEN}"
    payload = {
        "recipient": {"id": recipient_id},
        "message": {"text": text}
    }
    headers = {"Content-Type": "application/json"}
    requests.post(url, headers=headers, json=payload)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
