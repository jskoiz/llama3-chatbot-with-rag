import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

url = 'https://api.intercom.io/articles'
headers = {
    'Authorization': f"Bearer {os.getenv('INTERCOM_TOKEN')}",
    'Accept': 'application/json'
}

response = requests.get(url, headers=headers)

with open('info.json', 'w') as file:
    json.dump(response.json(), file, indent=4)
