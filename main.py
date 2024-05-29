# main.py
import asyncio
import logging
import time
import os
import subprocess
import signal
import sys
from dotenv import load_dotenv
from telethon import TelegramClient
from data_processor import fetch_all_pages
from vector_store import rebuild_vectorstore
from telegram_bot import start_telegram_client, send_message
from web_server import run_server

# Load environment variables
load_dotenv()
api_id = os.getenv('API_ID')
api_hash = os.getenv('API_HASH')
bot_token = os.getenv('BOT_TOKEN')
chat_id = int(os.getenv('CHAT_ID'))
intercom_token = os.getenv('INTERCOM_TOKEN')

json_file_path = 'info.json'
prompt_template = os.getenv('PROMPT_TEMPLATE')
embedding_log_file = 'logs/embeddings_log.txt'

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s', handlers=[
    logging.FileHandler("logs/app.log"),
    logging.StreamHandler()
])

start_time = time.time()
client = None

ollama_process = None
ngrok_process = None
tg_post_process = None

def handle_signal(signal, frame):
    asyncio.run(shutdown())

async def shutdown():
    global client, ollama_process, ngrok_process, tg_post_process
    logging.info("Shutting down...")
    if client:
        await client.disconnect()
        logging.info("Client disconnected.")

    # Terminate processes
    if ollama_process:
        ollama_process.terminate()
        await ollama_process.wait()
        logging.info("ollama process terminated.")

    if ngrok_process:
        ngrok_process.terminate()
        await ngrok_process.wait()
        logging.info("ngrok process terminated.")

    if tg_post_process:
        tg_post_process.terminate()
        await tg_post_process.wait()
        logging.info("tg_post process terminated.")

    # Ensure all processes are terminated before closing the event loop
    subprocess.run(['pkill', 'ollama'])
    subprocess.run(['pkill', 'ngrok'])
    subprocess.run(['pkill', 'tg_post.py'])
    
    pending = asyncio.all_tasks()
    for task in pending:
        task.cancel()
    await asyncio.gather(*pending, return_exceptions=True)
    await asyncio.sleep(0.1)  # Give time for all tasks to complete

    loop = asyncio.get_event_loop()
    loop.stop()
    loop.close()

    sys.exit(0)


async def start_subprocess(command):
    process = await asyncio.create_subprocess_shell(
        command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    return process

async def main():
    global client, ollama_process, ngrok_process, tg_post_process
    try:
        logging.info("Starting ollama serve and ngrok tunnel")
        # Start ollama serve and ngrok tunnel
        ollama_process = await start_subprocess('ollama serve')
        ngrok_process = await start_subprocess('ngrok http --domain=boom.ngrok.app 127.0.0.1:5001')

        logging.info("Fetching data and rebuilding vector store")
        await fetch_all_pages(intercom_token)  # Ensure data is fetched correctly
        qa_chain = await rebuild_vectorstore(json_file_path, prompt_template, embedding_log_file)
        
        logging.info("Starting Telegram client")
        client = await start_telegram_client(api_id, api_hash, bot_token, chat_id, qa_chain)
        
        logging.info("Running web server")
        await run_server()
    except Exception as e:
        logging.error(f"Error in main: {str(e)}", exc_info=True)
        await send_message(client, chat_id, '<span style="color:red">Shutting Down</span>')
    finally:
        await shutdown()

if __name__ == '__main__':
    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(main())
    except Exception as e:
        logging.error(f"Error: {str(e)}", exc_info=True)
    finally:
        pending = asyncio.all_tasks(loop)
        for task in pending:
            task.cancel()
        group = asyncio.gather(*pending, return_exceptions=True)
        loop.run_until_complete(group)
        loop.run_until_complete(loop.shutdown_asyncgens())
        loop.close()
        logging.info("Script stopped.")

