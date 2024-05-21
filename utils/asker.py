import json
import logging
import os
import requests
import asyncio
import pandas as pd
import time
from dotenv import load_dotenv
from quart import Quart, jsonify, request
from telethon import TelegramClient, events
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import GPT4AllEmbeddings
from langchain_core.prompts import PromptTemplate
from langchain_community.llms import Ollama
from langchain.callbacks.manager import CallbackManager
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
from langchain.chains import RetrievalQA
from langchain.docstore.document import Document

os.makedirs('logs', exist_ok=True)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

load_dotenv()

intercom_token = os.getenv('INTERCOM_TOKEN')

vectorstore = None

def fetch_all_pages():
    url = 'https://api.intercom.io/articles'
    headers = {
        'Authorization': f'Bearer {intercom_token}',
        'Accept': 'application/json'
    }
    all_documents = []
    while url:
        response = requests.get(url, headers=headers)
        data = response.json()
        logging.info(f"Fetched data: {json.dumps(data, indent=2)}")
        if 'data' in data and data['data']:
            documents = [Document(page_content=article["body"]) for article in data["data"] if article["body"].strip()]
            all_documents.extend(documents)
        if 'pages' in data and 'next' in data['pages']:
            url = data['pages']['next']
        else:
            break
    return all_documents

documents = fetch_all_pages()
if documents:
    vectorstore = Chroma.from_documents(documents=documents, embedding=GPT4AllEmbeddings())
    logging.info("Documents processed and vector store initialized.")
else:
    logging.error("No valid documents with non-empty body found.")

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

qa_chain = None
if vectorstore:
    qa_chain = RetrievalQA.from_chain_type(
        llm,
        retriever=vectorstore.as_retriever(),
        chain_type_kwargs={"prompt": QA_CHAIN_PROMPT},
    )

async def handle_query(query):
    if qa_chain is None:
        return {"response": "Initialization error: Vector store not available. Check log for details.", "id": "1234"}

    result = qa_chain.invoke(query)
    logging.info(f"Query result: {result}")

    if isinstance(result, dict):
        if 'result' in result:
            result = result['result']
        else:
            result = "No result field found in response."
    elif isinstance(result, str):
        result = result.strip()
    else:
        result = str(result).strip()

    if not result:
        result = "I apologize, but I don't have enough information to provide a helpful answer."

    return {"response": result, "id": "1234"}

questions_df = pd.read_csv('questions.csv')

if 'question' not in questions_df.columns:
    logging.error(f"'question' column not found in CSV. Available columns: {questions_df.columns}")
    raise KeyError(f"'question' column not found in CSV. Available columns: {questions_df.columns}")

questions = questions_df['question'].tolist()

async def test_questions_and_save_to_spreadsheet(questions):
    start_time = time.time()  # Start timing
    results = []
    for question in questions:
        result = await handle_query(question)
        response = result["response"]
        results.append({"question": question, "response": response, "id": result["id"]})
    
    df = pd.DataFrame(results)
    df.to_excel("responses.xlsx", index=False)

    end_time = time.time()
    duration = end_time - start_time

    print(f"Processed {len(questions)} questions in {duration:.2f} seconds.")

asyncio.run(test_questions_and_save_to_spreadsheet(questions))
