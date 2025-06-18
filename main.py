from flask import Flask, request
import os

app = Flask(__name__)

VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "123456")

@app.route('/')
def home():
    return 'Facebook AI Bot is running!'

@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    if request.method == 'GET':
        mode = request.args.get("hub.mode")
        token = request.args.get("hub.verify_token")
        challenge = request.args.get("hub.challenge")
        if mode == "subscribe" and token == VERIFY_TOKEN:
            return challenge, 200
        else:
            return "Token error", 403
    elif request.method == 'POST':
        data = request.get_json()
        print("📩 رسالة من فيسبوك:", data)
        return "OK", 200

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
