from flask import Flask, request

app = Flask(__name__)

VERIFY_TOKEN = "123456"  # لازم يكون نفسو في فيسبوك

@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    if request.method == 'GET':
        token = request.args.get('hub.verify_token')
        challenge = request.args.get('hub.challenge')
        if token == VERIFY_TOKEN:
            return challenge
        return 'Invalid verification token', 403

    elif request.method == 'POST':
        data = request.get_json()
        print("📩 رسالة وصلت من فيسبوك:", data)
        return "OK", 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
