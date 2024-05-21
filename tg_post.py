from telethon import TelegramClient, events, sync, Button
import requests
import json
import os
from dotenv import load_dotenv
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

load_dotenv()

api_id = os.getenv('API_ID')
api_hash = os.getenv('API_HASH')
bot_token = os.getenv('BOT_TOKEN')
intercom_token = os.getenv('INTERCOM_TOKEN')

client = TelegramClient('logs/tg_post', api_id, api_hash)
client.start(bot_token=bot_token)

conversation_state = {}

@client.on(events.NewMessage(pattern='^/start$'))
async def start_article(event):
    sender_id = event.sender_id
    conversation_state[sender_id] = {"step": "title", "data": {}}
    await event.respond("Okay, let's make a new article. Press the button below to enter the article name.",
                        buttons=[Button.inline("Enter Title", "title"), Button.inline("Cancel", "cancel")])

@client.on(events.CallbackQuery())
async def process_article_step(event):
    sender_id = event.sender_id
    data = event.data.decode('utf-8')

    if sender_id in conversation_state:
        step = conversation_state[sender_id]["step"]
        article_data = conversation_state[sender_id]["data"]

        if data == "cancel":
            del conversation_state[sender_id]
            await event.respond("Article creation canceled.")
            return

        if step == "title" and data == "title":
            conversation_state[sender_id]["step"] = "wait_title"
            await event.respond("Please enter the article name:")
        elif step == "description" and data == "description":
            conversation_state[sender_id]["step"] = "wait_description"
            await event.respond("Please enter the article description:")
        elif step == "body" and data == "body":
            conversation_state[sender_id]["step"] = "wait_body"
            await event.respond("Please enter the article body:")
        elif step == "publish":
            article_data["state"] = "published" if data == "publish" else "draft"
            article_data["author_id"] = 7303886  # Default or specified author_id
            await create_article(event, article_data)
            del conversation_state[sender_id]

@client.on(events.NewMessage())
async def process_user_input(event):
    sender_id = event.sender_id
    user_input = event.text

    if sender_id in conversation_state:
        step = conversation_state[sender_id]["step"]
        article_data = conversation_state[sender_id]["data"]

        if step == "wait_title":
            article_data["title"] = user_input
            conversation_state[sender_id]["step"] = "description"
            await event.respond(f"Current Article State:\nTitle: {article_data['title']}\n\nGreat! Now press the button below to enter the article description.",
                                buttons=[Button.inline("Enter Description", "description"), Button.inline("Cancel", "cancel")])
        elif step == "wait_description":
            article_data["description"] = user_input
            conversation_state[sender_id]["step"] = "body"
            await event.respond(f"Current Article State:\nTitle: {article_data['title']}\nDescription: {article_data['description']}\n\nAwesome! Now press the button below to enter the article body.",
                                buttons=[Button.inline("Enter Body", "body"), Button.inline("Cancel", "cancel")])
        elif step == "wait_body":
            article_data["body"] = user_input
            conversation_state[sender_id]["step"] = "publish"
            await event.respond(f"Current Article State:\nTitle: {article_data['title']}\nDescription: {article_data['description']}\nBody: {article_data['body']}\n\nPerfect! Do you want to publish the article or save it as a draft?",
                                buttons=[Button.inline("Publish", "publish"), Button.inline("Draft", "draft"), Button.inline("Cancel", "cancel")])

async def create_article(event, article_data):
    logging.info(f"Creating article with data: {article_data}")

    url = "https://api.intercom.io/articles"
    headers = {
        "Authorization": f"Bearer {intercom_token}",
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Intercom-Version": "2.10"
    }

    response = requests.post(url, headers=headers, json=article_data)
    logging.info(f"HTTP POST Request sent. Status Code: {response.status_code}")

    if response.status_code == 200:
        article_url = response.json()["url"]
        await event.respond(f"Article created successfully. Here's the complete post:\n\nTitle: {article_data['title']}\nDescription: {article_data['description']}\nBody: {article_data['body']}\nURL: {article_url}")
        logging.info("Article created successfully with the response: " + response.text)
    else:
        error_message = f"Failed to create article. Status code: {response.status_code}, Response: {response.text}"
        await event.respond(error_message)
        logging.error(error_message)

client.run_until_disconnected()
