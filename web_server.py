# web_server.py
from quart import Quart, jsonify, request
from hypercorn.config import Config
from hypercorn.asyncio import serve
import logging

app = Quart(__name__)

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

async def run_server():
    config = Config()
    config.bind = ["0.0.0.0:5001"]
    await serve(app, config)