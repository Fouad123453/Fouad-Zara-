from flask import Flask, request
import requests
import os

app = Flask(__name__)

VERIFY_TOKEN = "123456"
PAGE_ACCESS_TOKEN = os.environ.get("PAGE_ACCESS_TOKEN")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")

# نخزن المحادثة وحالة الأسلوب لكل مستخدم
user_histories = {}
user_states = {}

def update_user_state(sender_id, message):
    """تحليل الرسالة وتحديث إعدادات المستخدم"""
    lowered = message.lower()
    state = user_states.get(sender_id, {"emojis": True, "style": "dz"})

    if "حبس الايموجي" in lowered or "بدون ايموجي" in lowered:
        state["emojis"] = False
    elif "رجع الايموجي" in lowered or "استعمل الايموجي" in lowered:
        state["emojis"] = True
    elif "خلي ردودك رسمية" in lowered or "الأسلوب الرسمي" in lowered:
        state["style"] = "formal"
    elif "رجع الأسلوب عادي" in lowered or "تكلم جزائري" in lowered:
        state["style"] = "dz"

    user_states[sender_id] = state
    return state

def build_system_prompt(state):
    """بناء البرومبت حسب حالة المستخدم"""
    style_prompt = ""
    if state["style"] == "formal":
        style_prompt = "أجب باللغة العربية الفصحى وبشكل رسمي دون استخدام إيموجيات."
    elif state["style"] == "dz":
        style_prompt = "جاوب باللهجة الجزائرية بطريقة واقعية ومفهومة."

    if not state["emojis"]:
        style_prompt += " بدون استخدام الإيموجيات."
    else:
        style_prompt += " وأضف بعض الإيموجيات المناسبة."

    return f"أنت مساعد ذكي. {style_prompt}"

def get_ai_reply(sender_id, message):
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }

    # تحليل وتحديث حالة المستخدم
    state = update_user_state(sender_id, message)
    system_prompt = build_system_prompt(state)

    # إنشاء تاريخ المحادثة
    if sender_id not in user_histories:
        user_histories[sender_id] = []

    # تحديث أو إدراج system message
    if not any(msg["role"] == "system" for msg in user_histories[sender_id]):
        user_histories[sender_id].insert(0, {"role": "system", "content": system_prompt})
    else:
        user_histories[sender_id][0]["content"] = system_prompt

    # إضافة رسالة المستخدم
    user_histories[sender_id].append({"role": "user", "content": message})

    data = {
        "model": "openai/gpt-3.5-turbo",
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
