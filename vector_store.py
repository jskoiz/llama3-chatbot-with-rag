import json
import logging
import os  # Ensure this import is present
import time  # Add this import statement
from bs4 import BeautifulSoup
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import GPT4AllEmbeddings
from langchain.chains import RetrievalQA
from langchain.docstore.document import Document
from langchain_core.prompts import PromptTemplate
from langchain_community.document_loaders import JSONLoader
from langchain_community.llms import Ollama
from langchain.callbacks.manager import CallbackManager
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
from langchain_community.vectorstores.utils import filter_complex_metadata

def metadata_func(record: dict, metadata: dict) -> dict:
    metadata["title"] = record.get("title")
    metadata["author_id"] = record.get("author_id")
    metadata["created_at"] = record.get("created_at")
    metadata["id"] = record.get("id")
    return metadata

def strip_html(content):
    """Strips HTML tags from content using BeautifulSoup."""
    soup = BeautifulSoup(content, "html.parser")
    return soup.get_text()

def clean_metadata(metadata):
    """Ensure metadata values are strings, ints, floats, or bools."""
    cleaned_metadata = {}
    for k, v in metadata.items():
        if isinstance(v, (str, int, float, bool)):
            cleaned_metadata[k] = v
        elif isinstance(v, list):
            cleaned_metadata[k] = ', '.join(map(str, v))  # Convert list to a comma-separated string
        elif v is None:
            cleaned_metadata[k] = ''  # Replace None with empty string
        else:
            cleaned_metadata[k] = str(v)  # Convert other types to string
    return cleaned_metadata

class CustomGPT4AllEmbeddings(GPT4AllEmbeddings):
    def __call__(self, input):
        return self.embed_documents(input)

llm = Ollama(model="trojan-chat-bot", callback_manager=CallbackManager([StreamingStdOutCallbackHandler()]))

async def rebuild_vectorstore(json_file_path, prompt_template, embedding_log_file):
    QA_CHAIN_PROMPT = PromptTemplate(
        input_variables=["context", "question"],
        template=prompt_template,
    )

    try:
        with open(json_file_path, 'r') as f:
            data = json.load(f)

        logging.info(f"Total records received from remote: {len(data)}")

        # Load supplemental info if available
        supplemental_file_path = 'supplemental_info.json'
        if os.path.exists(supplemental_file_path) and os.path.getsize(supplemental_file_path) > 0:
            with open(supplemental_file_path, 'r') as f:
                supplemental_data = json.load(f)
                logging.info(f"Total records received from supplemental: {len(supplemental_data)}")
                # Convert supplemental data to the format expected by the vector store
                for item in supplemental_data:
                    data.append({
                        "id": f"supplemental_{int(time.time())}",
                        "type": "article",
                        "workspace_id": "supplemental",
                        "parent_id": None,
                        "parent_type": None,
                        "parent_ids": [],
                        "title": item["question"],
                        "description": item["question"],
                        "body": item["answer"],
                        "author_id": None,
                        "state": "published",
                        "created_at": int(time.time()),
                        "updated_at": int(time.time()),
                        "url": None
                    })

        # Ensure the data is a list of dictionaries
        if not isinstance(data, list) or not all(isinstance(item, dict) for item in data):
            raise ValueError(f"Expected a list of dictionaries, but got {type(data)} with content {data}")

        valid_documents = []
        invalid_documents = []
        for d in data:
            if d.get("body") and d["body"].strip():
                stripped_content = strip_html(d["body"])
                if stripped_content.strip():
                    page_content_with_id = f"ID: {d.get('id')}\n{stripped_content}"
                    metadata = clean_metadata(d)
                    valid_documents.append(Document(page_content=page_content_with_id, metadata=metadata))
                else:
                    invalid_documents.append(d)
            else:
                invalid_documents.append(d)

        logging.info(f"Total valid documents: {len(valid_documents)}")
        logging.info(f"Total invalid documents: {len(invalid_documents)}")
        for invalid in invalid_documents:
            logging.warning(f"Invalid document: {invalid}")

        if valid_documents:
            embedder = CustomGPT4AllEmbeddings(model="all-MiniLM-L6-v2.gguf")
            logging.info("Generating embeddings for documents...")
            embeddings = embedder.embed_documents([doc.page_content for doc in valid_documents])

            with open(embedding_log_file, 'w') as f:
                for doc, embedding in zip(valid_documents, embeddings):
                    f.write(f"Document ID: {doc.metadata['id']}\n")
                    f.write(f"Document Content: {doc.page_content}\n")
                    f.write(f"Embedding: {embedding}\n\n")

            logging.info(f"Total embeddings generated: {len(embeddings)}")
            vectorstore = Chroma.from_documents(documents=valid_documents, embedding=embedder)
            logging.info("Vector store successfully rebuilt.")

            retriever = vectorstore.as_retriever(search_type="similarity", k=5)
            qa_chain = RetrievalQA.from_chain_type(
                llm=llm,
                chain_type="stuff",
                retriever=retriever,
                chain_type_kwargs={"prompt": QA_CHAIN_PROMPT, "document_variable_name": "context"}
            )
            logging.info("QA chain initialized successfully.")
        else:
            logging.error("No valid documents with non-empty body found.")
    except Exception as e:
        logging.error(f"Error rebuilding vector store: {str(e)}", exc_info=True)
        raise

    return qa_chain
