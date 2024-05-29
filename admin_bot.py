import logging
import os
import subprocess
import time
import requests
import json
from dotenv import load_dotenv
from telethon import TelegramClient, events, Button

# Load environment variables
load_dotenv()

# Ensure these variables are set in your .env file
admin_api_id = os.getenv('ADMIN_API_ID')
admin_api_hash = os.getenv('ADMIN_API_HASH')
admin_bot_token = os.getenv('ADMIN_BOT_TOKEN')
intercom_token = os.getenv('INTERCOM_TOKEN')

# Check if the environment variables are loaded correctly
if not admin_api_id or not admin_api_hash or not admin_bot_token:
    raise ValueError("Your ADMIN_API_ID, ADMIN_API_HASH, or ADMIN_BOT_TOKEN is not set in the .env file")

client = TelegramClient('admin_bot', admin_api_id, admin_api_hash)
client.start(bot_token=admin_bot_token)

# Define the main bot control script path
MAIN_BOT_SCRIPT = 'main.py'

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

# Initialize stats
stats = {
    "start_time": time.time(),
    "last_restart": "Never",
    "last_rebuild": "Never",
    "total_queries": 0,
    "articles_pulled": 0
}

article_deletion_state = {}

@client.on(events.NewMessage(pattern='/admin'))
async def admin_command(event):
    logging.info("Admin command received")
    
    # Construct the message
    message = (
        "<b>🔧 Admin Bot Instructions</b>\n\n"
        "🚀 <b>Start Bot</b>:\nStart the main bot. Use .x followed by your query to use the AI chat bot.\n\n"
        "🛑 <b>Stop Bot</b>:\nStop the main bot. The admin bot is always running, you can bring this menu up again with /admin\n\n"
        "🔄 <b>Reboot Bot</b>:\nRestart the main bot. Useful if the responses start getting weird.\n\n"
        "💾 <b>Download DB</b>:\nDownload the database. Downloads a info.json file and shares it in this chat. Contains all intercom articles currently being used by the AI chat bot.\n\n"
        "🗑️ <b>Delete Article</b>:\nDelete an article from Intercom, works for both draft and live articles. You can find the article ID from the article's URL and grabbing the string of numbers from it. Just respond to the bot after clicking 'Delete Article' with the correct Article ID and it will be deleted."
    )

    await event.respond(message, parse_mode='html')

    buttons = [
        [Button.inline("🚀 Start Bot", b"start_bot"), Button.inline("🛑 Stop Bot", b"stop_bot"), Button.inline("🔄 Reboot Bot", b"reboot_bot")],
        [Button.inline("💾 Download DB", b"download_db"), Button.inline("🗑️ Delete Article", b"delete_article")]
    ]

    await event.respond("**Choose an action:**", buttons=buttons)

@client.on(events.CallbackQuery())
async def callback_handler(event):
    data = event.data.decode('utf-8')
    logging.info(f"Callback received: {data}")

    if data == "start_bot":
        await start_bot(event)
    elif data == "stop_bot":
        await stop_bot(event)
    elif data == "reboot_bot":
        await reboot_bot(event)
    elif data == "download_db":
        await download_db(event)
    elif data == "delete_article":
        await delete_article_prompt(event)

async def start_bot(event):
    logging.info("Starting the bot...")
    await event.respond("Starting the bot...")

    start_time = time.time()
    process = subprocess.Popen(['python3', MAIN_BOT_SCRIPT])

    # Poll the process and wait until it's fully started
    while True:
        time.sleep(1)
        if process.poll() is not None:
            break
        if is_bot_running():
            break

    end_time = time.time()
    elapsed_time = end_time - start_time

    await event.respond(f"Bot started in {elapsed_time:.2f} seconds.")
    logging.info(f"Bot started in {elapsed_time:.2f} seconds.")

def is_bot_running():
    """Check if the bot is running by looking for specific log entries or process checks."""
    # Implement your logic to check if the bot has started properly.
    # This could be checking the existence of a specific log entry or the process status.
    return True  # Placeholder: Replace with actual check

async def stop_bot(event):
    logging.info("Stopping the bot...")
    await event.respond("Stopping the bot...")
    subprocess.run(['pkill', '-f', MAIN_BOT_SCRIPT])
    await event.respond("Bot stopped.")

async def reboot_bot(event):
    logging.info("Rebooting the bot...")
    await event.respond("Rebooting the bot...")

    # Stop the bot
    subprocess.run(['pkill', '-f', MAIN_BOT_SCRIPT])

    # Start the bot
    start_time = time.time()
    process = subprocess.Popen(['python3', MAIN_BOT_SCRIPT])

    # Poll the process and wait until it's fully started
    while True:
        time.sleep(1)
        if process.poll() is not None:
            break
        if is_bot_running():
            break

    end_time = time.time()
    elapsed_time = end_time - start_time

    stats["last_restart"] = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
    await event.respond(f"Bot rebooted in {elapsed_time:.2f} seconds.")
    logging.info(f"Bot rebooted in {elapsed_time:.2f} seconds.")

async def download_db(event):
    logging.info("Downloading the database...")
    await event.respond("Downloading the database...")
    
    url = 'https://api.intercom.io/articles'
    headers = {
        'Authorization': f"Bearer {intercom_token}",
        'Accept': 'application/json'
    }
    
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        with open('info.json', 'w') as file:
            json.dump(response.json(), file, indent=4)
        
        await event.respond("Database downloaded successfully.")
        await client.send_file(event.chat_id, 'info.json', caption="Here is the downloaded database.")
    else:
        logging.error(f"Failed to download the database. Status code: {response.status_code}")
        await event.respond("Failed to download the database.")

async def delete_article_prompt(event):
    sender_id = event.sender_id
    article_deletion_state[sender_id] = {"step": "ask_id"}
    await event.respond("Please enter the article ID to delete:")

@client.on(events.NewMessage())
async def handle_new_message(event):
    sender_id = event.sender_id
    if sender_id in article_deletion_state and article_deletion_state[sender_id]["step"] == "ask_id":
        article_id = event.text.strip()
        await delete_article(event, article_id)
        del article_deletion_state[sender_id]

async def delete_article(event, article_id):
    url = f"https://api.intercom.io/articles/{article_id}"
    headers = {
        "Intercom-Version": "2.9",
        "Authorization": f"Bearer {intercom_token}"
    }

    response = requests.delete(url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        if data.get('deleted'):
            await event.respond(f"Article with ID {article_id} deleted successfully.")
        else:
            await event.respond(f"Failed to delete article with ID {article_id}.")
    elif response.status_code == 404:
        await event.respond(f"Article with ID {article_id} not found.")
    else:
        logging.error(f"Failed to delete article with ID {article_id}. Status code: {response.status_code}")
        await event.respond(f"Failed to delete article with ID {article_id}. Status code: {response.status_code}")

client.run_until_disconnected()
