import requests
from flask import Flask, request, Response, jsonify
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
import os
import PIL.Image

app = Flask(__name__)

telegram_bot_token = os.environ.get('BOT_TOKEN')
GOOGLE_API_KEY = os.environ.get('GOOGLE_API_KEY')
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel('models/gemini-1.5-flash', system_instruction="You are a chatbot which generates compliments for users. You can also answer questions and have a conversation with users.") 
last_prompt = 'Empty'
chat = model.start_chat(history=[])

def generate_answer(chat_id, question):
    try:
        response = chat.send_message(question, safety_settings={
        HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
        })
        print(response)
        return response.text
    except Exception as e:
        print(f"Error: {e}")
        return "Something went wrong generating the response"

def message_parser(message):
    try:
        chat_id = message['message']['chat']['id']
        text = message['message'].get('text', '__NONE__')
    except Exception as e:
        print(f"Error parsing message: {e}")
        chat_id = -1
        text = '__NONE__'
    print("Chat ID: ", chat_id)
    print("Message: ", text)
    return chat_id, text

def save_image(file_id):
    # Get the file path from Telegram
    file_path_url = f"https://api.telegram.org/bot{telegram_bot_token}/getFile?file_id={file_id}"
    file_path_response = requests.get(file_path_url).json()
    file_path = file_path_response['result']['file_path']

    # Download the image
    file_url = f"https://api.telegram.org/file/bot{telegram_bot_token}/{file_path}"
    image_data = requests.get(file_url).content

    # Save the image
    image_name = os.path.basename(file_path)
    save_path = os.path.join('downloads', image_name)
    with open(save_path, 'wb') as image_file:
        image_file.write(image_data)

    return save_path

def send_message_telegram(chat_id, text):
    url = f'https://api.telegram.org/bot{telegram_bot_token}/sendMessage'
    payload = {
        'chat_id': chat_id,
        'text': text,
        'parse_mode': 'Markdown'
    }
    response = requests.post(url, json=payload)
    return response

def get_image_response(image_path):
    image = PIL.Image.open(image_path)
    prompt = "Give me a slightly naughty compliment based on this image"
    response = model.generate_content([prompt, image])
    return response.text

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        msg = request.get_json()
        chat_id, incoming_que = message_parser(msg)
        
        if chat_id != -1:
            if 'photo' in msg['message']:
                photo = msg['message']['photo'][-1]
                file_id = photo['file_id']
                saved_image_path = save_image(file_id)
                answer = get_image_response(saved_image_path)
                send_message_telegram(chat_id, answer)
            elif incoming_que.strip() == '/start':
                start_msg = "Hi there!"
                send_message_telegram(chat_id, start_msg)
            elif incoming_que == '__NONE__':
                send_message_telegram(chat_id, 'Sorry, I can only interact with text right now :\(')
            else:
                answer = generate_answer(chat_id, incoming_que)
                send_message_telegram(chat_id, answer)
        
        return Response('ok', status=200)
    else:
        return "<h1>GET Request Made</h1>"

if __name__ == '__main__':
    if not os.path.exists('downloads'):
        os.makedirs('downloads')
    app.run()