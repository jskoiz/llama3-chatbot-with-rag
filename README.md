# Llama3 RAG Enabled Chatbot

## Overview

The bot uses a vector store to provide relevant answers based on the data fetched from Intercom articles. It also serves a web server and utilizes ngrok for exposing the local server to the internet.

## Repository Structure

- `main.py`: The main script to start the bot, server, and manage subprocesses for `ollama` and `ngrok`.
- `telegram_bot.py`: Handles Telegram bot functionality and communication.
- `data_processor.py`: Fetches and processes data from Intercom.
- `utils.py`: Utility functions including HTML stripping.
- `vector_store.py`: Manages the vector store and embedding generation.
- `web_server.py`: Serves the web API using Quart and Hypercorn.

## Setup

### Prerequisites

- Python 3.10+
- `pip` package manager
- An Intercom account and API token
- Telegram Bot API credentials
- `ngrok` for exposing the local server

### Installation

1. Clone the repository:

    ```bash
    git clone https://github.com/your-username/custom-intercom-bot.git
    cd custom-intercom-bot
    ```

2. Create and activate a virtual environment:

    ```bash
    python3 -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3. Install the required dependencies:

    ```bash
    pip install -r requirements.txt
    ```

4. Create a `.env` file in the root directory and add your environment variables:

    ```ini
    API_ID=your_telegram_api_id
    API_HASH=your_telegram_api_hash
    BOT_TOKEN=your_telegram_bot_token
    CHAT_ID=your_chat_id
    INTERCOM_TOKEN=your_intercom_token
    PROMPT_TEMPLATE="Your prompt template here"
    ```

4. Create an Ollama modelfile.

    ```bash
    ollama pull llama3
    ollama create custom-chat-bot -f custom-bot
    ```

## Usage

To start the bot and the server, run:

```bash
python3 main.py
