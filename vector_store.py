# vector_store.py
import logging
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
        loader = JSONLoader(
            file_path=json_file_path,
            jq_schema='.[]',
            content_key="body",
            metadata_func=metadata_func
        )
        data = loader.load()

        valid_documents = []
        invalid_documents = []
        for d in data:
            if d.page_content and d.page_content.strip():
                stripped_content = strip_html(d.page_content)
                if stripped_content.strip():
                    page_content_with_id = f"ID: {d.metadata['id']}\n{stripped_content}"
                    valid_documents.append(Document(page_content=page_content_with_id, metadata=d.metadata))
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
        logging.error(f"Error rebuilding vector store: {str(e)}")

    return qa_chain
