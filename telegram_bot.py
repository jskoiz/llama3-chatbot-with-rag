from telethon import TelegramClient, events
import logging
import time

qa_chain = None 

async def start_telegram_client(api_id, api_hash, bot_token, qa_chain_instance):
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

    await client.start(bot_token=bot_token)
    logging.info("Telegram client connected.")

    return client

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
