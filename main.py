from flask import Flask, request
import requests
import os

app = Flask(__name__)

VERIFY_TOKEN = "123456"
PAGE_ACCESS_TOKEN = os.environ.get("PAGE_ACCESS_TOKEN")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")

# نخزن المحادثة لكل مستخدم
user_histories = {}
user_personas = {}

# الرد الذكي من OpenRouter
def get_ai_reply(sender_id, message):
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }

    # إعداد المحادثة إذا جديدة
    if sender_id not in user_histories:
        user_histories[sender_id] = []
        user_personas[sender_id] = "جاوب باللهجة الجزائرية بطريقة ودودة مع شوية إيموجيات."

    # تحليل الرسالة وتغيير الأسلوب تلقائيًا
    lowered = message.lower()
    if "ما تردش بإيموجيات" in lowered or "بدون ايموجي" in lowered:
        user_personas[sender_id] = "جاوب باللهجة الجزائرية بدون أي إيموجيات وبأسلوب رسمي."
    elif "خلي الأسلوب يكون رسمي" in lowered:
        user_personas[sender_id] = "جاوب بالعربية الفصحى وبأسلوب محترم ورسمي."
    elif "حكيلي كأنك إنسان" in lowered:
        user_personas[sender_id] = "جاوب وكأنك إنسان حقيقي، بطريقة مفهومة، واقعية وبها تفاعل طبيعي."
    elif "ضحكني" in lowered or "حاول تضحكني" in lowered:
        user_personas[sender_id] = "جاوب بطريقة مضحكة، فيها مزاح وإيموجيات مضحكة."

    # تحديث system message
    system_prompt = f"أنت مساعد ذكي. {user_personas[sender_id]}"

    if not any(m["role"] == "system" for m in user_histories[sender_id]):
        user_histories[sender_id].insert(0, {"role": "system", "content": system_prompt})
    else:
        user_histories[sender_id][0]["content"] = system_prompt

    # إضافة الرسالة الأخيرة
    user_histories[sender_id].append({"role": "user", "content": message})

    data = {
        "model": "openai/gpt-3.5-turbo",  # غيّرها لـ gpt-4-turbo إذا تحب
        "messages": user_histories[sender_id]
    }

    try:
        response = requests.post(url, headers=headers, json=data)
        reply = response.json()["choices"][0]["message"]["content"]
        user_histories[sender_id].append({"role": "assistant", "content": reply})
        return reply
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

# Webhook تاع فيسبوك
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

# تشغيل التطبيق
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
