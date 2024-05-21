import json
import logging
import os
import aiohttp
import asyncio
from contextlib import suppress
from dotenv import load_dotenv
from quart import Quart, jsonify, request
from telethon import TelegramClient, events
from telethon.errors import RPCError, ChatAdminRequiredError, ChannelPrivateError
from telethon.tl.types import PeerChannel
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import GPT4AllEmbeddings
from langchain_core.prompts import PromptTemplate
from langchain_community.llms import Ollama
from langchain.callbacks.manager import CallbackManager
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
from langchain.chains import RetrievalQA
from langchain.docstore.document import Document
from hypercorn.config import Config
from hypercorn.asyncio import serve
import time

# Configure logging
os.makedirs('logs', exist_ok=True)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s', handlers=[
    logging.FileHandler("logs/app.log"),
    logging.StreamHandler()
])

start_time = time.time()

# Load environment variables
load_dotenv()
api_id = os.getenv('API_ID')
api_hash = os.getenv('API_HASH')
bot_token = os.getenv('BOT_TOKEN')
intercom_token = os.getenv('INTERCOM_TOKEN')
chat_id = int(os.getenv('CHAT_ID'))

app = Quart(__name__)

client = TelegramClient('logs/tg_chat', api_id, api_hash)

vectorstore = None
qa_chain = None

template = """Answer the question based on the provided context. Do not include introductory phrases. If the question is unclear or unrelated to the context, ask the user to rephrase or provide more details.

Context:
{context}

Question:
{question}

Answer:"""

QA_CHAIN_PROMPT = PromptTemplate(
    input_variables=["context", "question"],
    template=template,
)

llm = Ollama(model="trojan-chat-bot", callback_manager=CallbackManager([StreamingStdOutCallbackHandler()]))

async def fetch_all_pages():
    url = 'https://api.intercom.io/articles'
    headers = {
        'Authorization': f'Bearer {intercom_token}',
        'Accept': 'application/json'
    }
    all_documents = []
    all_data = []
    async with aiohttp.ClientSession() as session:
        while url:
            async with session.get(url, headers=headers) as response:
                if response.status != 200:
                    logging.error(f"Failed to fetch data: {response.status}")
                    break
                data = await response.json()
                all_data.extend(data.get('data', []))
                if 'data' in data and data['data']:
                    documents = [Document(page_content=article["body"]) for article in data["data"] if article["body"].strip()]
                    all_documents.extend(documents)
                url = data.get('pages', {}).get('next', None)
    with open('info.json', 'w') as f:
        json.dump(all_data, f, indent=2)
    logging.info(f"Total records received: {len(all_data)}")
    return all_documents

async def rebuild_vectorstore():
    global documents, vectorstore, qa_chain
    try:
        documents = await fetch_all_pages()
        if documents:
            vectorstore = Chroma.from_documents(documents=documents, embedding=GPT4AllEmbeddings())
            logging.info("Documents processed and vector store rebuilt.")
            qa_chain = RetrievalQA.from_chain_type(
                llm,
                retriever=vectorstore.as_retriever(),
                chain_type_kwargs={"prompt": QA_CHAIN_PROMPT},
            )
        else:
            logging.error("No valid documents with non-empty body found.")
    except Exception as e:
        logging.error(f"Error rebuilding vector store: {str(e)}")

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

@app.route('/intercom', methods=['POST'])
async def intercom_handler():
    data = await request.get_json()
    query = data.get("body")
    if query:
        result = await handle_query(query)
        response = result["response"]
        time_taken = result["time_taken"]
        return jsonify({"response": response, "time_taken": time_taken}), 200
    else:
        logging.error("No query provided in the request")
        return jsonify({"error": "No query provided"}), 400

@app.route('/rebuild_vectorstore', methods=['POST'])
async def rebuild_vectorstore_handler():
    await rebuild_vectorstore()
    return jsonify({"message": "Vector store rebuilt"}), 200

@client.on(events.NewMessage(pattern=r'^\.x (.+)', func=lambda e: e.text.lower().startswith('.x ')))
async def answer_query(event):
    query = event.pattern_match.group(1)
    logging.info(f"Received query: {query}")
    result = await handle_query(query)
    response = result["response"]
    time_taken = result["time_taken"]
    await event.respond(f"```{response}```\n**Time to generate: {time_taken:.2f} seconds**", parse_mode='Markdown')

@client.on(events.NewMessage(pattern='/rebuild'))
async def rebuild_vectorstore_command(event):
    logging.info("Received /rebuild command. Rebuilding the vector store...")
    await event.respond("Rebuilding database...")
    await rebuild_vectorstore()
    await event.respond("Database rebuilt.")

async def run_server():
    global start_time
    config = Config()
    config.bind = ["0.0.0.0:5001"]
    
    async def custom_serve():
        end_time = time.time()
        time_to_boot = end_time - start_time
        await send_message(chat_id, f'<span style="color:red">Bot Online, Time to boot: {time_to_boot:.2f} seconds</span>')
        await serve(app, config)

    await custom_serve()

async def send_message(chat_id, message):
    try:
        entity = await client.get_entity(PeerChannel(chat_id))
        await client.send_message(entity, message, parse_mode='html')
    except ChatAdminRequiredError:
        logging.error(f"Failed to send message to {chat_id}: Bot lacks admin rights.")
    except ChannelPrivateError:
        logging.error(f"Failed to send message to {chat_id}: Channel is private.")
    except RPCError as e:
        logging.error(f"Failed to send message to {chat_id}: {str(e)}")

async def start():
    try:
        await client.start(bot_token=bot_token)
        logging.info("Telegram client connected.")
        await rebuild_vectorstore()
        await run_server()
    except Exception as e:
        logging.error(f"Error occurred: {str(e)}. Retrying in 5 seconds...")
        await asyncio.sleep(5)
        await start()

async def main():
    try:
        await start()
    except KeyboardInterrupt:
        logging.info("Script interrupted by user.")
        await send_message(chat_id, '<span style="color:red">Shutting Down</span>')
    finally:
        logging.info("Shutting down...")
        await client.disconnect()
        logging.info("Client disconnected.")
        pending = [task for task in asyncio.all_tasks() if not task done() and task is not asyncio.current_task()]
        for task in pending:
            task.cancel()
        await asyncio.gather(*pending, return_exceptions=True)
        loop.stop()
        loop.close()
        logging.info("Script stopped.")

if __name__ == '__main__':
    try:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(main())
    except RuntimeError as e:
        logging.error(f"Runtime error: {str(e)}")
    finally:
        if not loop.is_closed():
            loop.close()
