import azure.functions as func
import logging
import os
from openai import AzureOpenAI
#from dotenv import load_dotenv
from telebot import TeleBot, types
import requests
import json
import shutil
import re
from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient


app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

@app.route(route="http_trigger", auth_level=func.AuthLevel.ANONYMOUS)
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
                connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
                blob_service_client = BlobServiceClient.from_connection_string(conn_str=connection_string)
                blob_client = blob_service_client.get_blob_client("history", f'{fileprefix}_history.txt')
                
                    
        
                message_next(chat_id, bot_token,update['message']['text'], fileprefix, blob_client)
                logging.info(f'Update has a message = {update["message"]["text"]}')
                return func.HttpResponse(status_code=200)
        except Exception as e:
                logging.error(f'Oops, we got an exception in http_trigger: {e}')
                return func.HttpResponse(status_code=200)
    else:
        return func.HttpResponse("This is a bot server.", status_code=200)
    

def message_next(chat_id, bot_token, text, fileprefix,blob_client):
        logging.info(f'Update has a next message = {text}, fileprefix: {fileprefix}')
        bot = TeleBot(bot_token)
        conversation = []
        querry = []
        #combine history and prompt to pass to openai
        if blob_client.exists():
            if text == '/startover':
                blob_client.delete_blob()
                bot.send_message(chat_id, "Okay, let's start over")
                logging.info(f'{fileprefix}_history.txt deleted')
                return func.HttpResponse("This is a bot server.", status_code=200)
            else:
                conversation = blob_client.download_blob().readall().decode('utf-8')
                lines = conversation.split('\n')
                conversation = [json.loads(line) for line in lines]
                # Check if the previous user input is the same as the current one
                if conversation[-2]["content"] == text:
                    logging.warn('The text is the same as the previous user content in the history file')
                    return func.HttpResponse(status_code=200)


        conversation.append({"role": "user", "content": text})
        conversation = conversation[-16:]
        with open(f'prompt_cocktails.txt', 'r') as f:
                querry=[{"role": "system", "content": f.read().strip()}]
                querry.extend(conversation)

        logging.info(f'Conversation is ready to pass to openai = {querry}')
        response = get_response(querry)
        bot.send_message(chat_id, response)
        conversation.append({"role": "assistant", "content": response})
        conversation = [json.dumps(message) for message in conversation]
        conversation = "\n".join(conversation)
        blob_client.upload_blob(conversation, overwrite=True)
        
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
                prompt=f'''5 Amusingly tipsy laboratory cartoon rats, donned in lab coats, gaze curiously and happily at the cocktail {cocktailname} they just invented, but refrain from touching it. 
                The cocktail is depicted with remarkable realism, accurately showcasing its usual ingredients and garnishes. 
                The glass mirrors the typical vessel used for this cocktail. 
                Importantly, it refrains from portraying a milky appearance if the cocktail does not traditionally contain milk or cream. Oil painting style. Romanticism.''',
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
    logging.info(f'Response = {text}')
    return text
