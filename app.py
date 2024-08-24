import requests
from flask import Flask, request, Response, jsonify
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
import os
from PIL import Image
from io import BytesIO

app = Flask(__name__)

telegram_bot_token = os.environ.get('BOT_TOKEN')
GOOGLE_API_KEY = os.environ.get('GOOGLE_API_KEY')
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel('gemini-1.0-pro')
chats = {}
last_prompt = 'Empty'

def chat_length(chat_id):
    if chat_id in chats.keys():
        return len(chats[chat_id].history)//2
    else:
        return -1
        
def chat_exists(chat_id):
    return chat_id in chats.keys()
        
def create_chat(chat_id):
    if chat_id == -1:
        return
    if not chat_exists(chat_id):
        chats[chat_id] = model.start_chat(history=[])

def generate_answer(chat_id, question):
    try:
        if not chat_exists(chat_id):
            create_chat(chat_id)
        response = chats[chat_id].send_message(question, safety_settings={
        HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
        })
        print(response)
        return response.text
    except:
        return "Something went wrong generating the response"

def generate_image_answer(image_path):
    image = PIL.Image.open(image_path)
    prompt = "Give me a slightly naughty compliment based on this image"
    response = model.generate_content([prompt, image])
    return response.text

def message_parser(message):
    try:
        chat_id = message['message']['chat']['id']
        if 'photo' in message['message']:
            photo = message['message']['photo'][-1]  # Get the highest resolution photo
            file_id = photo['file_id']
            file_info = requests.get(f'https://api.telegram.org/bot{telegram_bot_token}/getFile?file_id={file_id}').json()
            file_path = file_info['result']['file_path']
            image_url = f'https://api.telegram.org/file/bot{telegram_bot_token}/{file_path}'
            image = Image.open(BytesIO(requests.get(image_url).content))
            return chat_id, None, image
        else:
            text = message['message'].get('text', '__NONE__')
            return chat_id, text, None
    except:
        return -1, '__NONE__', None

def send_message_telegram(chat_id, text):
    url = f'https://api.telegram.org/bot{telegram_bot_token}/sendMessage'
    payload = {
        'chat_id': chat_id,
        'text': text,
        'parse_mode' : 'Markdown'
    }
    response = requests.post(url, json=payload)
    return response

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        msg = request.get_json()
        chat_id, incoming_que, image = message_parser(msg)
        if chat_id != -1:
            if image is not None:
                answer = generate_image_answer(chat_id, image)
                send_message_telegram(chat_id, answer)
            elif incoming_que.strip() == '/start':
                create_chat(chat_id)
                start_msg = "Hi there!"
                send_message_telegram(chat_id, start_msg)
            elif incoming_que == '__NONE__':
                send_message_telegram(chat_id, 'Sorry, I can only interact with text right now :(')
            else:
                answer = generate_answer(chat_id, incoming_que)
                send_message_telegram(chat_id, answer)
        return Response('ok', status=200)
    else:
        return "<h1>GET Request Made</h1>"

if __name__ == '__main__':
    app.run()