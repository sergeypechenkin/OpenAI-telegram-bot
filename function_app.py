import azure.functions as func
import logging
import os
import openai
from dotenv import load_dotenv
import telebot
import requests

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)


@app.route(route="Bot_1_General")
def Bot_1_General(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')
    webhookconstruct = constructwebhook()
    logging.info(webhookconstruct)
    name = req.params.get('name')
    if not name:
        try:
            req_body = req.get_json()
        except ValueError:
            pass
        else:
            name = req_body.get('name')

    if name:
        return func.HttpResponse(f"Hello, {name}. This HTTP triggered function executed successfully.")
    else:
        return func.HttpResponse(
             "This HTTP triggered function executed successfully. Pass a name in the query string or in the request body for a personalized response.",
             status_code=200
        )






def constructwebhook():
    # Construct the webhook URL
    webhook_url = f'https://api.telegram.org/bot{bot_token}/setWebhook?url={function_url}'
    # Make the request
    response = requests.get(webhook_url)
    # Check the response
    if response.status_code == 200:
        return('Webhook set successfully.')
    else:
        return('Failed to set webhook:', response.content, webhook_url)
            