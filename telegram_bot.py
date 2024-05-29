# telegram_bot.py
from telethon import TelegramClient, events, Button
from telethon.errors import RPCError, ChatAdminRequiredError, ChannelPrivateError
from telethon.tl.types import PeerChannel
import logging
import time
import subprocess
import os

qa_chain = None 

async def start_telegram_client(api_id, api_hash, bot_token, chat_id, qa_chain_instance):
    global qa_chain
    qa_chain = qa_chain_instance

    client = TelegramClient('logs/tg_chat', api_id, api_hash)

    @client.on(events.NewMessage(pattern=r'^\.x (.+)', func=lambda e: e.text.lower().startswith('.x ')))
    async def answer_query(event):
        query = event.pattern_match.group(1)
        logging.info(f"Received query: {query}")
        result = await handle_query(query)
        response = result["response"]
        time_taken = result["time_taken"]
        await event.respond(f"`{response}`\n**Time to generate: {time_taken:.2f} seconds**", parse_mode='Markdown')

    @client.on(events.NewMessage(pattern='/rebuild'))
    async def rebuild_vectorstore_command(event):
        logging.info("Received /rebuild command. Rebuilding the vector store...")
        await event.respond("Rebuilding database...")
        await rebuild_vectorstore()
        await event.respond("Database rebuilt.")

    @client.on(events.NewMessage(pattern='/start'))
    async def start_command(event):
        buttons = [
            [Button.inline("Start Bot", b"start_bot"), Button.inline("Stop Bot", b"stop_bot"), Button.inline("Reboot Bot", b"reboot_bot")],
            [Button.inline("Write Article", b"write_article"), Button.inline("Rebuild DB", b"rebuild_db")],
            [Button.inline("Download DB", b"download_db"), Button.inline("Delete Article", b"delete_article")]
        ]
        await event.respond("Choose an action:", buttons=buttons)

    @client.on(events.CallbackQuery())
    async def callback_handler(event):
        data = event.data.decode('utf-8')

        if data == "start_bot":
            await start_bot(event)
        elif data == "stop_bot":
            await stop_bot(event)
        elif data == "reboot_bot":
            await reboot_bot(event)
        elif data == "write_article":
            await write_article(event)
        elif data == "rebuild_db":
            await rebuild_db(event)
        elif data == "download_db":
            await download_db(event)
        elif data == "delete_article":
            await delete_article(event)

    async def start_bot(event):
        await event.respond("Starting the bot...")
        subprocess.Popen(['python3', 'main.py'])
        await event.respond("Bot started.")

    async def stop_bot(event):
        await event.respond("Stopping the bot...")
        subprocess.run(['pkill', '-f', 'main.py'])
        await event.respond("Bot stopped.")

    async def reboot_bot(event):
        await event.respond("Rebooting the bot...")
        subprocess.run(['pkill', '-f', 'main.py'])
        subprocess.Popen(['python3', 'main.py'])
        await event.respond("Bot rebooted.")

    async def write_article(event):
        await event.respond("Starting article creation...")
        subprocess.Popen(['python3', 'tg_post.py'])
        await event.respond("Article creation script started.")

    async def rebuild_db(event):
        await event.respond("Rebuilding the database...")
        subprocess.Popen(['python3', 'rebuild_db_script.py'])
        await event.respond("Database rebuild initiated.")

    async def download_db(event):
        await event.respond("Downloading the database...")
        # Implement download logic here
        await event.respond("Database downloaded.")

    async def delete_article(event):
        await event.respond("Deleting an article...")
        # Implement delete article logic here
        await event.respond("Article deletion initiated.")

    await client.start(bot_token=bot_token)
    logging.info("Telegram client connected.")

    return client

async def send_message(client, chat_id, message):
    try:
        entity = await client.get_entity(PeerChannel(chat_id))
        await client.send_message(entity, message, parse_mode='html')
    except ChatAdminRequiredError:
        logging.error(f"Failed to send message to {chat_id}: Bot lacks admin rights.")
    except ChannelPrivateError:
        logging.error(f"Failed to send message to {chat_id}: Channel is private.")
    except RPCError as e:
        logging.error(f"Failed to send message to {chat_id}: {str(e)}")

async def handle_query(query):
    if qa_chain is None:
        logging.error("QA chain is not initialized.")
        return {"response": "Initialization error: Vector store not available. Check log for details.", "time_taken": 0}

    start_time = time.time()
    try:
        result = qa_chain.invoke(query)
    except Exception as e:
        logging.error(f"Error during query handling: {str(e)}")
        return {"response": "An error occurred while processing the query.", "time_taken": 0}

    end_time = time.time()
    time_taken = end_time - start_time

    logging.info(f"Query result: {result}")

    if isinstance(result, dict):
        result = result.get('result', "No result field found in response.")
    elif isinstance(result, str):
        result = result.strip()
    else:
        result = str(result).strip()

    if not result:
        result = "I apologize, but I don't have enough information to provide a helpful answer."

    return {"response": result, "time_taken": time_taken}
