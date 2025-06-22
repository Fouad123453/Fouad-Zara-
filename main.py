from flask import Flask, request
import os, requests

app = Flask(__name__)

VERIFY_TOKEN = "123456"
PAGE_ACCESS_TOKEN = os.getenv("PAGE_ACCESS_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# تخزين المحادثة لكل مستخدم
user_histories = {}

def get_ai_reply(user_id, message):
    if user_id not in user_histories:
        user_histories[user_id] = [
            {
                "role": "system",
                "content": (
                    "أنت مساعد ذكي يُجيب بالعربية الفصحى فقط، دون استخدام كلمات أجنبية، ويُراعي المشاعر الإنسانية. "
                    "افهم الإيموجيات وتفاعل معها. جاوب بدقة، وبلغة واضحة، وابقَ ضمن نفس الموضوع كلما أمكن."
                )
            }
        ]

    user_histories[user_id].append({"role": "user", "content": message})

    data = {
        "model": "llama3-70b-8192",
        "messages": user_histories[user_id]
    }

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers,
            json=data,
            timeout=20
        )
        reply = response.json()["choices"][0]["message"]["content"]
        user_histories[user_id].append({"role": "assistant", "content": reply})
        user_histories[user_id] = user_histories[user_id][-12:]  # الحفاظ على الذاكرة قصيرة
        return reply
    except Exception as e:
        return "⚠️ حدث خطأ أثناء التواصل مع خدمة الذكاء الاصطناعي."

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
                for msg_event in entry["messaging"]:
                    if msg_event.get("message"):
                        sender_id = msg_event["sender"]["id"]
                        msg_text = msg_event["message"].get("text")
                        if msg_text:
                            reply = get_ai_reply(sender_id, msg_text)
                            send_message(sender_id, reply)
        return "OK", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
