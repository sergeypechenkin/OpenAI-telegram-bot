#Note: The openai-python library support for Azure OpenAI is in preview.
      #Note: This code sample requires OpenAI Python library version 0.28.1 or lower.
      
import os
import openai
from dotenv import load_dotenv
import telebot

load_dotenv()  # take environment variables from .env.
openai.api_type = "azure"
openai.api_base = os.getenv("AZURE_OPENAI_ENDPOINT")
openai.api_version = "2023-07-01-preview"
openai.api_key = os.getenv("OPENAI_API_KEY")
bot = telebot.TeleBot(os.getenv("TELEGRAM_BOT_TOKEN"))

conversation_history = []
prompt = "Отвечай как старый айтишник, на русском языке: "
conversation_history.append({"role": "user", "content": prompt})

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Hello! I'm your bot.")

@bot.message_handler(func=lambda message: True)
def echo_all(message):

    # Add the user's message to the conversation history
    conversation_history.append({"role": "user", "content": message.text})

    # Limit the conversation history to the last 2 messages
    limited_history = conversation_history[-2:]

    # Get the bot's response and add it to the conversation history
    response = get_response(limited_history)
    bot.reply_to(message, response)
    conversation_history.append({"role": "assistant", "content": response})


def get_response(conversation_history):

    response = openai.ChatCompletion.create(
        engine="gpt-4",
        messages = conversation_history,
        temperature=0.7,
        max_tokens=800,
        top_p=0.95,
        frequency_penalty=0.8,
        presence_penalty=0,
        stop=None
    )
    
    text = response['choices'][0]['message']['content']
    return text


bot.polling()
