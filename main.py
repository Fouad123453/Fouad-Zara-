from flask import Flask, request
import requests
import os

app = Flask(__name__)

VERIFY_TOKEN = "123456"
PAGE_ACCESS_TOKEN = os.environ.get("PAGE_ACCESS_TOKEN")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")

user_histories = {}
user_personas = {}  # هذي نخزنو فيها البرومبت الديناميكي لكل مستخدم

def build_system_prompt(instruction):
    return f"أنت مساعد ذكي باللهجة الجزائرية. {instruction} جاوب بطريقة واقعية وتفاعلية وتفهم السياق مليح."

def get_ai_reply(sender_id, message):
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }

    # إعدادات أولية
    if sender_id not in user_histories:
        user_histories[sender_id] = []
        user_personas[sender_id] = "جاوب بإسلوب ودي وبشوش مع شوية إيموجيات."

    # نسمحو للمستخدم يبدل الأسلوب
    if message.lower().startswith("غير الأسلوب إلى"):
        style = message.replace("غير الأسلوب إلى", "").strip()
        user_personas[sender_id] = style
        return f"✅ تم تغيير الأسلوب إلى: {style}"

    # تحديث system prompt
    system_prompt = build_system_prompt(user_personas[sender_id])

    # لو مازال ما دخلناش system role
    if not any(m["role"] == "system" for m in user_histories[sender_id]):
        user_histories[sender_id].insert(0, {"role": "system", "content": system_prompt})
    else:
        user_histories[sender_id][0]["content"] = system_prompt

    # نضيف رسالة المستخدم
    user_histories[sender_id].append({"role": "user", "content": message})

    data = {
        "model": "openai/gpt-3.5-turbo",  # بدلها إلى gpt-4-turbo لو تحب
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
