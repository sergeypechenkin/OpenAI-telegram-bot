#### From Source

Function:
    Deploy tools to test localy
    func start --useHttps --cert .\server.pfx --password 1111 --port 7443
    Use ngrok.com to create https tunnel in terminal: ngrok http https://localhost:7443             
    update localsettings.json with URL
    locally set webhook https://localhost:7443/api/Bot_1_General
    check webhook
        https://api.telegram.org/bot{bot-token is .env}}/getWebhookInfo
    