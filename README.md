# Psagot
Simple script that automates the monitoring of your finance products in your "Psagot Trade" ("פסגות טרייד") account.
  

  
## Usage
First, create `.env` file with your configuration or just edit the environment on `docker-compose.yml`

| Field      | Description |
| ----------- | ----------- |
| PSAGOT_USERNAME      | The username you use to login the spark psagot system|
| PSAGOT_PASSWORD   | The password use to login the spark psagot system|
| PSAGOT_ACCOUNT_KEY (Optional)   | Your psagot spark account key (should be something like: 'ACC_XXX-YYYYYY'). If you don't know it the script will try to figure it out for you |
| TELEGRAM_TOKEN   | Telegram token for your bot|
| TELEGRAM_CHAT_ID   | Telegram chat id to send the results summary to|
| TELEGRAM_DISABLED   | If set, the result won't be published to the Telegram channel|
| VERBOSE   | If set, the logger severity will be set to debug|

  

Now, you can simply run:
```
docker-compose up --remove-orphans
```