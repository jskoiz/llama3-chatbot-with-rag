import os
import requests
import json
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

url = 'https://api.intercom.io/articles'
headers = {
    'Authorization': f"Bearer {os.getenv('INTERCOM_TOKEN')}",
    'Accept': 'application/json'
}

response = requests.get(url, headers=headers)

# Ensure the directory where you're running this script has write permissions
with open('info.json', 'w') as file:
    json.dump(response.json(), file, indent=4)
