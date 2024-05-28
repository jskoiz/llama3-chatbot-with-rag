# main.py
import asyncio
import logging
import time
from data_processor import fetch_all_pages
from vector_store import rebuild_vectorstore
from telegram_bot import start_telegram_client, send_message
from web_server import run_server
from dotenv import load_dotenv
import os
import subprocess

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

async def start_subprocess(command):
    process = await asyncio.create_subprocess_shell(
        command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    return process

async def main():
    global client, ollama_process, ngrok_process
    try:
        # Start ollama serve and ngrok tunnel
        ollama_process = await start_subprocess('ollama serve')
        ngrok_process = await start_subprocess('ngrok http --domain=boom.ngrok.app 127.0.0.1:5001')

        qa_chain = await rebuild_vectorstore(json_file_path, prompt_template, embedding_log_file)
        client = await start_telegram_client(api_id, api_hash, bot_token, chat_id, qa_chain)
        await fetch_all_pages(intercom_token)  # Call fetch_all_pages and wait for it to complete
        await run_server()
    except KeyboardInterrupt:
        logging.info("Script interrupted by user.")
        await send_message(client, chat_id, '<span style="color:red">Shutting Down</span>')
    finally:
        logging.info("Shutting down...")
        if client:
            await client.disconnect()
            logging.info("Client disconnected.")

        # Terminate ollama and ngrok processes
        if ollama_process:
            ollama_process.terminate()
            await ollama_process.wait()
            logging.info("ollama process terminated.")

        if ngrok_process:
            ngrok_process.terminate()
            await ngrok_process.wait()
            logging.info("ngrok process terminated.")

        subprocess.run(['pkill', 'ollama'])
        subprocess.run(['pkill', 'ngrok'])

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(main())
    except Exception as e:
        logging.error(f"Error: {str(e)}")
    finally:
        pending = asyncio.all_tasks(loop)
        for task in pending:
            task.cancel()
        group = asyncio.gather(*pending, return_exceptions=True)
        loop.run_until_complete(group)
        loop.run_until_complete(loop.shutdown_asyncgens())
        loop.close()
        logging.info("Script stopped.")
