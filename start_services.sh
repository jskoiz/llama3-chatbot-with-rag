#!/bin/bash

# Function to kill a process by name
kill_process() {
    local process_name=$1
    pgrep -f "$process_name" | xargs -r kill -9
    if [ $? -eq 0 ]; then
        echo "Successfully killed $process_name processes"
    else
        echo "No running $process_name processes found"
    fi
}

# Kill existing processes
kill_process "ollama serve"
sleep 1
kill_process "ngrok http --domain=boom.ngrok.app 127.0.0.1:5001"
sleep 1
kill_process "python3 chatbot.py"
sleep 1
kill_process "python3 tg_post.py"
sleep 1

# Start new instances
# Start Ollama
echo "Starting Ollama..."
nohup ollama serve > logs/ollama.log 2>&1 &
echo "Ollama started."
sleep 2

# Start Ngrok Tunnel
echo "Starting Ngrok..."
nohup ngrok http --domain=boom.ngrok.app 127.0.0.1:5001 > logs/ngrok.log 2>&1 &
echo "Ngrok started."
sleep 2

# Start Chatbot
echo "Starting Chatbot..."
nohup python3 chatbot.py > logs/chatbot.log 2>&1 &
echo "Chatbot started."
sleep 2

# Start Posting Interface
echo "Starting Posting Interface..."
nohup python3 tg_post.py > logs/tg_post.log 2>&1 &
echo "Posting Interface started."
sleep 2

echo "All services started."

