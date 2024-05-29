# data_processor.py
import aiohttp
import json
import logging

async def fetch_all_pages(intercom_token):
    url = 'https://api.intercom.io/articles'
    headers = {
        'Authorization': f'Bearer {intercom_token}',
        'Accept': 'application/json'
    }
    all_data = []

    async with aiohttp.ClientSession() as session:
        while url:
            async with session.get(url, headers=headers) as response:
                if response.status != 200:
                    logging.error(f"Failed to fetch data: {response.status}")
                    break
                data = await response.json()
                articles = data.get('data', [])
                all_data.extend(articles)
                url = data.get('pages', {}).get('next', None)

    # Check to ensure all_data is a list of dictionaries
    if not all(isinstance(item, dict) for item in all_data):
        logging.error("Fetched data is not a list of dictionaries.")
        return None

    with open('info.json', 'w') as f:
        json.dump(all_data, f, indent=2)

    logging.info(f"Total records received: {len(all_data)}")
    return 'info.json'
