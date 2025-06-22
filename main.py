from flask import Flask, request
import requests
import os

app = Flask(__name__)

VERIFY_TOKEN = "123456"
PAGE_ACCESS_TOKEN = os.environ.get("PAGE_ACCESS_TOKEN")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")

# نخزنو المحادثات لكل مستخدم
user_histories = {}

def get_ai_reply(sender_id, message):
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }

    # نجيبو المحادثة السابقة
    if sender_id not in user_histories:
        user_histories[sender_id] = [
            {"role": "system", "content": "أنت مساعد ذكي يتحدث باللهجة الجزائرية بطريقة ودودة، ويستعمل الإيموجيات في ردوده. جاوب كأنك إنسان واقعي يفهم السياق ويطوّل في الردود باش تكون مفهومة."}
        ]

    # نزيدو الرسالة الجديدة
    user_histories[sender_id].append({"role": "user", "content": message})

    data = {
        "model": "openai/gpt-3.5-turbo",  # ولا gpt-4-turbo لو تحب
        "messages": user_histories[sender_id]
    }

    try:
        response = requests.post(url, headers=headers, json=data)
        reply = response.json()["choices"][0]["message"]["content"]
        user_histories[sender_id].append({"role": "assistant", "content": reply})
        return reply
    except Exception as e:
        return "⚠️ خطأ في الاتصال بـ OpenRouter"

def send_message(recipient_id, message_text):
    url = f"https://graph.facebook.com/v16.0/me/messages?access_token={PAGE_ACCESS_TOKEN}"
    headers = {"Content-Type": "application/json"}
    data = {
        "recipient": {"id": recipient_id},
        "message": {"text": message_text}
    }
    requests.post(url, headers=headers, json=data)

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
                            ai_reply = get_ai_reply(sender_id, message_text)
                            send_message(sender_id, ai_reply)
        return "OK", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
