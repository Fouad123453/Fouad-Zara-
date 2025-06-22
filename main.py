from flask import Flask, request
import requests
import os
from PIL import Image
import pytesseract
from io import BytesIO

app = Flask(__name__)

VERIFY_TOKEN = "123456"  # رمز التحقق Webhook
PAGE_ACCESS_TOKEN = os.environ.get("PAGE_ACCESS_TOKEN")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
MODEL = "openai/gpt-3.5-turbo"

# نخزنو المحادثات وحالة الأسلوب لكل مستخدم
user_histories = {}
user_states = {}

def update_user_state(sender_id, message):
    """تحليل الرسالة وتحديث إعدادات المستخدم"""
    lowered = message.lower()
    state = user_states.get(sender_id, {"emojis": True, "style": "arabic"})

    if "حبس الايموجي" in lowered or "بدون ايموجي" in lowered:
        state["emojis"] = False
    elif "رجع الايموجي" in lowered or "استعمل الايموجي" in lowered:
        state["emojis"] = True
    elif "خلي ردودك رسمية" in lowered or "الأسلوب الرسمي" in lowered:
        state["style"] = "formal"
    elif "تكلم جزائري" in lowered or "رجع الأسلوب عادي" in lowered:
        state["style"] = "dz"
    else:
        state["style"] = "arabic"

    user_states[sender_id] = state
    return state

def build_system_prompt(state):
    style = state.get("style", "arabic")
    emojis = state.get("emojis", True)

    prompt = "أنت مساعد ذكي يتحدث مثل الإنسان، ويستخدم اللغة العربية الفصحى أو اللهجة الجزائرية حسب السياق."
    if style == "dz":
        prompt += " جاوب باللهجة الجزائرية بأسلوب واقعي ومفهوم."
    elif style == "formal":
        prompt += " جاوب بلغة عربية رسمية وبدون إيموجيات."
    else:
        prompt += " جاوب بلغة عربية فصحى ودية وقريبة للإنسان و اسمك AI GPTتم تطويرك بواسطة مطورين جزائريين."

    if emojis:
        prompt += " استعمل الإيموجيات المناسبة حسب الحاجة."
    else:
        prompt += " لا تستعمل الإيموجيات."

    return prompt

def get_ai_reply(sender_id, message):
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }

    # تحديث حالة المستخدم
    state = update_user_state(sender_id, message)
    system_prompt = build_system_prompt(state)

    if sender_id not in user_histories:
        user_histories[sender_id] = [{"role": "system", "content": system_prompt}]
    else:
        user_histories[sender_id][0]["content"] = system_prompt

    user_histories[sender_id].append({"role": "user", "content": message})

    data = {
        "model": MODEL,
        "messages": user_histories[sender_id],
        "temperature": 0.7
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

def extract_text_from_image(image_url):
    try:
        response = requests.get(image_url)
        img = Image.open(BytesIO(response.content))
        text = pytesseract.image_to_string(img, lang='ara+eng')
        return text.strip() if text else "ما لقيتش نص واضح في الصورة."
    except Exception as e:
        return "⚠️ ما قدرتش نقرأ النص من الصورة."

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

                        # 📷 معالجة الصور
                        if "attachments" in messaging_event["message"]:
                            for attachment in messaging_event["message"]["attachments"]:
                                if attachment["type"] == "image":
                                    image_url = attachment["payload"]["url"]
                                    text_from_image = extract_text_from_image(image_url)
                                    ai_reply = get_ai_reply(sender_id, f"النص الموجود في الصورة: {text_from_image}")
                                    send_message(sender_id, ai_reply)

                        # 💬 معالجة النصوص
                        elif "text" in messaging_event["message"]:
                            message_text = messaging_event["message"]["text"]
                            ai_reply = get_ai_reply(sender_id, message_text)
                            send_message(sender_id, ai_reply)

        return "OK", 200

if __name__ == "__main__":
    # مسار Tesseract إذا كنت في Windows (إزالة التعليق عند الحاجة)
    # pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
