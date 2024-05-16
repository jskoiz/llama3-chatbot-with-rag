

## Scripts Description

### Telegram/Intercom Chat Bot (`chatbot.py`)
Usesthe LangChain + Ollama/Llama 3 for language model processing and RAG. The script pulls current articles from the specified repository and builds a new vectordb to pull answers from.


## Clone Repo
Clone the repository
```bash
git clone <repository-url>
cd <repository-directory>
```

## GitHub CLI Installation
Set up keyrings and repository:
```bash
sudo mkdir -p -m 755 /etc/apt/keyrings &&
wget -qO- https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo tee /etc/apt/keyrings/githubcli-archive-keyring.gpg > /dev/null &&
sudo chmod go+r /etc/apt/keyrings/githubcli-archive-keyring.gpg &&
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null &&
sudo apt update &&
sudo apt install gh -y
```

## Ollama Setup
Install Ollama and download the Llama3 Model:
```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull llama3
```
Create Trojan Chat Bot from Modelfile (trojan-bot file in root directory):
```bash
ollama create trojan-chat-bot -f trojan-bot
```

## Ngrok Installation
Set up repository and install Ngrok:
```bash
curl -s https://ngrok-agent.s3.amazonaws.com/ngrok.asc | sudo tee /etc/apt/trusted.gpg.d/ngrok.asc >/dev/null &&
echo "deb https://ngrok-agent.s3.amazonaws.com buster main" | sudo tee /etc/apt/sources.list.d/ngrok.list &&
sudo apt update &&
sudo apt install ngrok
```
Authenticate Ngrok (replace `<TOKEN>` with your actual token):
```bash
ngrok config add-authtoken <TOKEN>
```

## Environment Setup
Install text editor (optional) and create environment variables file:
```bash
sudo apt install nano
echo -e "API_ID=<API_ID>
API_HASH=<API_HASH>
BOT_TOKEN=<BOT_TOKEN>
OUTPUT_CHANNEL_ID=@YourChannel
INTERCOM_TOKEN=<INTERCOM_TOKEN>" > .env
```

## Start Chatbot
Install Python dependencies and start services:
```bash
pip install -r requirements.txt &
ngrok http --domain=boom.ngrok.app 127.0.0.1:5001 &
ollama serve > logs/ollama.log 2>&1 &
python3 chatbot.py > logs/chatbot.log 2>&1 &

```

## Stop All Services
```bash
pkill python3
pkill ngrok
pkill ollama
```

## View Logs
```bash
tail -f logs/chatbot.log
```

## To-Do List
```bash
Build unified start-up/reboot process.
Refine initial install approach
Stress test 
Redo scripts to regularly pull new articles without reboot
Refine tg_post.py
```