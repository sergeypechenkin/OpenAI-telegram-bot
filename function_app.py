import azure.functions as func
import logging
import os
from openai import AzureOpenAI
from dotenv import load_dotenv
from telebot import TeleBot, types
import requests
import json
import shutil
import re

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

##@app.route(route="Bot_1_General") For local testing
@app.route(route="http_trigger", auth_level=func.AuthLevel.ANONYMOUS)
#def Bot_1_General(req: func.HttpRequest) -> func.HttpResponse: for local testing
def http_trigger(req: func.HttpRequest) -> func.HttpResponse:
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
#    function_url = os.getenv("FUNCTION_URL") for local testing
#    set_telegram_webhook(bot_token, function_url)    set manually, using info in .env file

    if req.method == 'POST':    
        update = req.get_json()
        
        logging.info(f'POST Update = {update}')


        try:

            if update['message']:

                username = update['message']['from']['first_name']
                user_id = update['message']['from']['id']
                chat_id = update['message']['chat']['id']
                fileprefix = f'{username}_{user_id}'
                logging.log(logging.INFO, f'User {username} with id {user_id} sent a message: {update["message"]["text"]}')
                
                    
                if update['message']['text'] == '/startover':
                    message_startover(chat_id, bot_token, fileprefix)
        
                message_next(chat_id, bot_token,update['message']['text'], fileprefix)
                logging.info(f'Update has a message = {update["message"]["text"]}')
                return func.HttpResponse(status_code=200)
        except Exception as e:
                logging.error(f'Got an exception: {e}')
                return func.HttpResponse(status_code=200)
    else:
        return func.HttpResponse("This is a bot server.", status_code=200)
    
#This should be set once pre function
def set_telegram_webhook(bot_token, function_url):
    set_webhook_url = f"https://api.telegram.org/bot{bot_token}/setWebhook?url={function_url}"
    logging.info(f'Setting the webhook URL to {set_webhook_url}')
    response = requests.post(set_webhook_url)
    return response.json()

def message_startover(chat_id, bot_token, fileprefix):
        bot = TeleBot(bot_token)
        if os.path.exists(f'{fileprefix}_prompt.txt'):
            os.remove(f'{fileprefix}_prompt.txt')
        if os.path.exists(f'{fileprefix}_history.txt'):
            os.remove(f'{fileprefix}_history.txt')
        bot.send_message(chat_id, "Okay, let's start over. What ingridients do you have?")

def message_next(chat_id, bot_token, text, fileprefix):
        logging.info(f'Update has a next message = {text}, fileprefix: {fileprefix}')
        bot = TeleBot(bot_token)

        #create general prompt file if not exists
        if not os.path.exists(f'{fileprefix}_prompt.txt'):
             logging.info(f'Prompt file does not exist. Creating a new one. {fileprefix}_prompt.txt')
             shutil.copyfile('prompt_cocktails.txt', f'{fileprefix}_prompt.txt')
    
        #open history file and add current message
        with open(f'{fileprefix}_history.txt', 'a') as f:
                f.write(json.dumps({"role": "user", "content": text}) + '\n')

        #construct conversation history as prompt+history and pass to openai

        conversation = []
        
        with open(f'{fileprefix}_history.txt', 'r') as f:
                for line in f:
                    conversation.append(json.loads(line))

        with open(f'{fileprefix}_prompt.txt', 'r') as f:
                conversation.append({"role": "system", "content": f.read().strip()})

        # Limit the conversation history to the last 10 messages
        conversation = conversation[-25:]
        response = get_response(conversation)
        bot.send_message(chat_id, response)

        #add response to history file
        with open(f'{fileprefix}_history.txt', 'a') as f:
            f.write(json.dumps({"role": "assistant", "content": response}) + '\n') 
        
        cocktailname = re.findall(r'\*\*(.*?)\*\*', response)
        cocktailname = cocktailname[0] if cocktailname else None
        logging.info(f'cocktailname = {cocktailname}')

        if cocktailname:
            client = AzureOpenAI(
                    api_version="2023-12-01-preview",  
                    api_key=os.environ["DALLE_API_KEY"],  
                    azure_endpoint=os.environ['AZURE_DALLE_ENDPOINT']
)

            result = client.images.generate(
                model="dalle3", # the name of your DALL-E 3 deployment
                prompt=f'5 Amusingly tipsy laboratory cartoon rats, donned in lab coats, gaze curiously at the {cocktailname} cocktail but refrain from touching it. The cocktail is depicted with remarkable realism, accurately showcasing its usual ingredients and garnishes. The glass mirrors the typical vessel used for this cocktail. Importantly, it refrains from portraying a milky appearance if the cocktail does not traditionally contain milk or cream',
                n=1)
            
            image_url = json.loads(result.model_dump_json())['data'][0]['url']
            bot.send_photo(chat_id, image_url)


def get_response(conversation):

    logging.info(f'Conversation = {conversation}')
    client = AzureOpenAI(
    api_key = os.getenv("AZURE_OPENAI_KEY"),  
    api_version = "2023-09-15-preview",
    #api_type = "azure",
    azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    )

    response = client.chat.completions.create(
        model="gpt-4",
        messages=conversation,
)
    
    text = response.choices[0].message.content
    return text