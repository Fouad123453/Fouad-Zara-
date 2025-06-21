from flask import Flask, request
import os
import requests

app = Flask(__name__)

VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN")
PAGE_ACCESS_TOKEN = os.environ.get("PAGE_ACCESS_TOKEN")


@app.route("/")
def home():
    return "🤖 Facebook Messenger Bot is running!"


@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        # تحقق من Webhook
        token = request.args.get("hub.verify_token")
        challenge = request.args.get("hub.challenge")
        if token == VERIFY_TOKEN:
            return challenge
        return "Error, invalid token", 403

    elif request.method == "POST":
        # رسالة من المستخدم
        data = request.get_json()
        for entry in data.get("entry", []):
            for messaging_event in entry.get("messaging", []):
                sender_id = messaging_event["sender"]["id"]
                if "message" in messaging_event:
                    message_text = messaging_event["message"].get("text", "")
                    send_message(sender_id, "✅ بوت يرد تلقائياً: " + message_text)
        return "ok", 200


def send_message(recipient_id, message_text):
    url = "https://graph.facebook.com/v18.0/me/messages"
    params = {
        "access_token": PAGE_ACCESS_TOKEN
    }
    headers = {
        "Content-Type": "application/json"
    }
    data = {
        "recipient": {"id": recipient_id},
        "message": {"text": message_text}
    }
    requests.post(url, params=params, headers=headers, json=data)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
