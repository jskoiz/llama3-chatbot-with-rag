#admin_bot.py
import logging
import os
import subprocess
import time
import requests
import json
import re
from dotenv import load_dotenv
from telethon import TelegramClient, events, Button
import psutil  # Add psutil to manage subprocesses

# Load environment variables
load_dotenv()

# Variables used
admin_api_id = os.getenv('ADMIN_API_ID')
admin_api_hash = os.getenv('ADMIN_API_HASH')
admin_bot_token = os.getenv('ADMIN_BOT_TOKEN')
intercom_token = os.getenv('INTERCOM_TOKEN')

# Variable check
if not admin_api_id or not admin_api_hash or not admin_bot_token:
    raise ValueError("Your ADMIN_API_ID, ADMIN_API_HASH, or ADMIN_BOT_TOKEN is not set in the .env file")

client = TelegramClient('admin_bot', admin_api_id, admin_api_hash)
client.start(bot_token=admin_bot_token)

MAIN_BOT_SCRIPT = 'main.py'

# Setup logging
log_capture = []
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s', datefmt='%H:%M:%S')

class LogCaptureHandler(logging.Handler):
    def emit(self, record):
        message = self.format(record)
        if ' - ' in message:
            message = message.split(' - ', 1)[1]  # Remove the timestamp if the delimiter is found
        message = message.replace('https://docs.trychroma.com/telemetry', '')  # Remove the URL
        
        # Define patterns to match the desired log lines
        patterns = [
            "Starting the bot...",
            "Starting ollama serve and ngrok tunnel",
            r"Total records received: \d+",
            r"Total records received from remote: \d+",
            r"Total records received from supplemental: \d+",
            r"Total valid documents: \d+",
            r"Total invalid documents: \d+",
            r"Total embeddings generated: \d+",
            "Vector store successfully rebuilt.",
            r"Connection to \d+\.\d+\.\d+\.\d+:\d+/TcpFull complete!",
            "Telegram client connected.",
            "Bot started."
        ]
        
        # Check if the message matches any of the patterns
        if any(re.search(pattern, message) for pattern in patterns):
            log_capture.append(message)

# Setup log capture handler
log_capture_handler = LogCaptureHandler()
log_capture_handler.setLevel(logging.INFO)
log_capture_handler.setFormatter(logging.Formatter('%(message)s'))

# Add log capture handler to root logger
logging.getLogger().addHandler(log_capture_handler)

# Ensure the standard logging output still goes to the terminal
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s', datefmt='%H:%M:%S'))
logging.getLogger().addHandler(console_handler)

stats = {
    "start_time": time.time(),
    "last_restart": "Never",
    "last_rebuild": "Never",
    "total_queries": 0,
    "articles_pulled": 0
}

article_deletion_state = {}
add_info_state = {}

@client.on(events.NewMessage(pattern='/admin'))
async def admin_command(event):
    logging.info("Admin command received")
    
    message = (
        "<b>Admin Bot for the Chat Bot is a management tool designed to allow easy rebooting and other basic management options of the main AI Chat Bot.</b>\n\n"
        "🚀 <b>Start</b>:\nStart the main bot. Use .x followed by your query to use the AI chat bot.\n\n"
        "🔄 <b>Reboot</b>:\nRestart the main bot. Useful if the responses start getting weird.\n\n"
        "💾 <b>Download DB</b>:\nDownload the database. Downloads an info.json file and shares it in this chat. Contains all intercom articles currently being used by the AI chat bot.\n\n"
        "🗑️ <b>Delete Article</b>:\nDelete an article from Intercom, works for both draft and live articles. You can find the article ID from the article's URL and grabbing the string of numbers from it. Just respond to the bot after clicking 'Delete Article' with the correct Article ID and it will be deleted.\n\n"
        "➕ <b>Add Info</b>:\nAdd a new question and answer to the supplemental database."
    )

    await event.respond(message, parse_mode='html')

    buttons = [
        [Button.inline("🚀 Start", b"start_bot"), Button.inline("🔄 Reboot", b"reboot_bot")],
        [Button.inline("💾 Download DB", b"download_db"), Button.inline("🗑️ Delete Article", b"delete_article")],
        [Button.inline("➕ Add Info", b"add_info")]
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
    elif data == "add_info":
        await add_info_prompt(event)

async def start_bot(event):
    logging.info("Starting the bot...")
    await event.respond("Starting the bot...")

    start_time = time.time()
    process = subprocess.Popen(['python3', MAIN_BOT_SCRIPT], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

    while True:
        line = process.stdout.readline()
        if not line:
            break
        logging.info(line.strip())
        if "Running on http://0.0.0.0:5001 (CTRL + C to quit)" in line:
            break

    end_time = time.time()
    elapsed_time = end_time - start_time

    # Capture logs and send to chat
    log_messages = "\n".join(log_capture)
    if log_messages:
        await event.respond(log_messages)

    await event.respond(f"Bot started in {elapsed_time:.2f} seconds.")
    logging.info(f"Bot started in {elapsed_time:.2f} seconds.")

def is_bot_running():
    """Check if the bot is running by looking for specific log entries or process checks."""
    return True  # Placeholder: Replace with actual check

def stop_all_subprocesses():
    """Stop all subprocesses associated with the bot."""
    logging.info("Stopping all subprocesses...")
    subprocess.run(['pkill', '-f', MAIN_BOT_SCRIPT])
    # Add any other subprocesses that need to be stopped here
    # Example: subprocess.run(['pkill', '-f', 'ollama serve'])
    # Example: subprocess.run(['pkill', '-f', 'ngrok'])

async def stop_bot(event):
    logging.info("Stopping the bot...")
    await event.respond("Stopping the bot...")
    stop_all_subprocesses()
    await event.respond("Bot stopped.")

async def reboot_bot(event):
    logging.info("Rebooting the bot...")
    await event.respond("Rebooting the bot...")

    # Stop the bot and all related subprocesses
    stop_all_subprocesses()

    # Ensure all instances of main.py are terminated
    for proc in psutil.process_iter():
        if 'python3' in proc.name() and MAIN_BOT_SCRIPT in proc.cmdline():
            proc.terminate()
            proc.wait()

    # Start the bot
    start_time = time.time()
    process = subprocess.Popen(['python3', MAIN_BOT_SCRIPT], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

    while True:
        line = process.stdout.readline()
        if not line:
            break
        logging.info(line.strip())
        if "Running on http://0.0.0.0:5001 (CTRL + C to quit)" in line:
            break

    end_time = time.time()
    elapsed_time = end_time - start_time

    stats["last_restart"] = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
    await event.respond("Bot rebooted.")
    logging.info("Bot rebooted.")

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
    elif sender_id in add_info_state:
        state = add_info_state[sender_id]
        if state["step"] == "ask_question":
            state["question"] = event.text.strip()
            state["step"] = "ask_answer"
            await event.respond("Enter the correct answer:")
        elif state["step"] == "ask_answer":
            state["answer"] = event.text.strip()
            await add_info_to_db(sender_id, state["question"], state["answer"])
            del add_info_state[sender_id]
            await event.respond("The question and answer have been added to the supplemental database.")

async def add_info_prompt(event):
    sender_id = event.sender_id
    add_info_state[sender_id] = {"step": "ask_question"}
    await event.respond("Enter the question:")

async def add_info_to_db(sender_id, question, answer):
    supplemental_info = {
        "question": question,
        "answer": answer
    }
    file_path = 'supplemental_info.json'
    
    if os.path.exists(file_path):
        with open(file_path, 'r') as file:
            data = json.load(file)
    else:
        data = []

    data.append(supplemental_info)

    with open(file_path, 'w') as file:
        json.dump(data, file, indent=4)

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
