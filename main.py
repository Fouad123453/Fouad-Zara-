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
    state = user_states.get(sender_id, {"emojis": True, "style": "natural"})

    if "حبس الايموجي" in lowered or "بدون ايموجي" in lowered:
        state["emojis"] = False
    elif "رجع الايموجي" in lowered or "استعمل الايموجي" in lowered:
        state["emojis"] = True
    elif "خلي ردودك رسمية" in lowered or "الأسلوب الرسمي" in lowered:
        state["style"] = "formal"
    elif "رجع الأسلوب عادي" in lowered or "تكلم عادي" in lowered:
        state["style"] = "natural"

    user_states[sender_id] = state
    return state

def build_system_prompt(state):
    """بناء برومبت ذكي حسب الحالة"""
    base_prompt = (
        "أنت مساعد ذكي وودود، تفهم جميع اللهجات العربية (الجزائرية، الفصحى، العامية...). "
        "تجاوب بطريقة مفهومة، مركزة، وتحافظ على نفس الموضوع. "
        "إذا طلب المستخدم تنفيذ أمر، حاول تنفذه أو تجاوب عليه بوضوح. "
        "إذا كانت الرسالة فكاهية، جاوب بروح مرحة. "
        "إذا كانت عاطفية، جاوب بتعاطف. "
        "ردك لازم يكون طبيعي وواقعي وكأنك إنسان."
    )

    if not state["emojis"]:
        base_prompt += " لا تستخدم الإيموجيات في الردود."
    else:
        base_prompt += " يمكن إضافة إيموجيات مناسبة فقط."

    if state["style"] == "formal":
        base_prompt += " استخدم اللغة العربية الفصحى بشكل رسمي."

    return base_prompt

def get_ai_reply(sender_id, message):
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }

    # تحديث حالة المستخدم
    state = update_user_state(sender_id, message)
    system_prompt = build_system_prompt(state)

    # إعداد المحادثة
    if sender_id not in user_histories:
        user_histories[sender_id] = []

    if not any(msg["role"] == "system" for msg in user_histories[sender_id]):
        user_histories[sender_id].insert(0, {"role": "system", "content": system_prompt})
    else:
        user_histories[sender_id][0]["content"] = system_prompt

    user_histories[sender_id].append({"role": "user", "content": message})

    data = {
        "model": "openai/gpt-3.5-turbo",  # تقدر تبدلو بـ gpt-4-turbo إذا تحب
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
