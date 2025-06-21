from flask import Flask, request
import os, requests

app = Flask(__name__)

VERIFY_TOKEN      = "123456"                          # استعمله نفسه في Meta
PAGE_ACCESS_TOKEN = os.getenv("PAGE_ACCESS_TOKEN")    # ضعه في متغيرات Render

@app.route("/")
def home():
    return "✅ Bot up!"

@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    # تحقق من Webhook (Facebook يرسل GET أول مرة)
    if request.method == "GET":
        token = request.args.get("hub.verify_token")
        challenge = request.args.get("hub.challenge")
        if token == VERIFY_TOKEN:
            return challenge
        return "Token mismatch", 403

    # استقبال رسائل POST
    data = request.get_json()
    if data and data.get("object") == "page":
        for entry in data["entry"]:
            for event in entry["messaging"]:
                if "message" in event and "text" in event["message"]:
                    sender_id = event["sender"]["id"]
                    send_message(sender_id, "👋 مرحبا! البوت يخدم ✅")
    return "OK", 200

def send_message(recipient_id, text):
    url = f"https://graph.facebook.com/v17.0/me/messages?access_token={PAGE_ACCESS_TOKEN}"
    payload = {
        "recipient": {"id": recipient_id},
        "message":   {"text": text}
    }
    requests.post(url, json=payload)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
