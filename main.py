from flask import Flask, request
import requests
import os

app = Flask(__name__)

VERIFY_TOKEN = "123456"  # نفس verify token اللي درتو في فيسبوك
PAGE_ACCESS_TOKEN = os.environ.get("PAGE_ACCESS_TOKEN")  # تحطو في المتغيرات

@app.route('/')
def home():
    return 'Facebook Messenger Bot is Live!'

@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    if request.method == 'GET':
        token_sent = request.args.get("hub.verify_token")
        return verify_fb_token(token_sent)
    else:
        output = request.get_json()
        for event in output['entry']:
            messaging = event['messaging']
            for message in messaging:
                if message.get('message'):
                    recipient_id = message['sender']['id']
                    if message['message'].get('text'):
                        user_message = message['message']['text']
                        send_message(recipient_id, "👋 مرحبا! شكراً على رسالتك ❤️")
        return "Message Processed"

def verify_fb_token(token_sent):
    if token_sent == VERIFY_TOKEN:
        return request.args.get("hub.challenge")
    return 'Invalid verification token'

def send_message(recipient_id, response_text):
    payload = {
        'recipient': {'id': recipient_id},
        'message': {'text': response_text}
    }
    auth = {'access_token': PAGE_ACCESS_TOKEN}
    response = requests.post('https://graph.facebook.com/v17.0/me/messages', params=auth, json=payload)
    return response.json()

if __name__ == "__main__":
    app.run(debug=True)
