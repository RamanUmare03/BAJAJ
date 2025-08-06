import os
import zipfile

# Define project structure and files
project_name = "hackrx-api"
base_path = f"/mnt/data/{project_name}"

# File content mapping
files_content = {
    f"{base_path}/app/__init__.py": "",
    f"{base_path}/app/main.py": """import uvicorn
from app.api import app

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
""",
    f"{base_path}/app/api.py": """from fastapi import FastAPI, Header, HTTPException, Security
from pydantic import BaseModel, HttpUrl
from typing import List, Annotated
import asyncio
from .llm import llm
from .utils import build_retriever_from_url

API_KEY = "50255bc08e08f6431861bace6cb7232a1a9c317758fc6afd177cfd01ba3cff9a"
BEARER_TOKEN = f"Bearer {API_KEY}"

class HackRxRequest(BaseModel):
    documents: HttpUrl
    questions: List[str]

app = FastAPI(
    title="HackRx API Processor",
    description="API for processing documents and answering questions.",
    version="1.0.0",
)

async def get_api_key(authorization: Annotated[str | None, Header()] = None):
    if authorization is None:
        raise HTTPException(status_code=401, detail="Authorization header missing")
    if authorization != BEARER_TOKEN:
        raise HTTPException(status_code=403, detail="Invalid API Key")

async def process_single_query(retriever, llm, query: str) -> str:
    docs = await retriever.ainvoke(query)
    context = "\\n\\n---\\n\\n".join([doc.page_content for doc in docs])
    prompt = f\"\"\"
    You are an assistant that answers strictly from the provided context.
    Rules:
    - Use ONLY the given context. Do not use external knowledge.
    - Answer in ONE sentence with all conditions.
    - If the answer is not in the context, say 'Not found in document.'

    Context:
    {context}

    Question:
    {query}

    Answer:
    \"\"\"
    response = await llm.ainvoke(prompt)
    return response.content

@app.post("/api/v1/hackrx/run")
async def handle_request(request_data: HackRxRequest, api_key: str = Security(get_api_key)):
    retriever = build_retriever_from_url(request_data.documents, use_semantic_chunking=True)
    tasks = [process_single_query(retriever, llm, q) for q in request_data.questions]
    answers = await asyncio.gather(*tasks)
    return {"answers": answers}
""",
    f"{base_path}/app/llm.py": """import os
from langchain_groq import ChatGroq

llm = ChatGroq(
    api_key=os.getenv("GROK_API_KEY"),
    model="meta-llama/llama-4-scout-17b-16e-instruct",
    temperature=0
)
""",
    f"{base_path}/app/embedding.py": """import os
from langchain_google_genai import GoogleGenerativeAIEmbeddings

embedding = GoogleGenerativeAIEmbeddings(
    model="models/embedding-001",
    google_api_key=os.getenv("GOOGLE_API_KEY"),
)
""",
    f"{base_path}/app/utils.py": """import os
import pickle
import tempfile
import requests
from langchain_community.document_loaders import (
    PyPDFLoader, UnstructuredWordDocumentLoader, UnstructuredEmailLoader
)
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_experimental.text_splitter import SemanticChunker
from langchain_community.retrievers import BM25Retriever
from langchain_community.vectorstores import FAISS
from langchain.retrievers.ensemble import EnsembleRetriever
from .embedding import embedding

CACHE_DIR = "cache"
os.makedirs(CACHE_DIR, exist_ok=True)

def get_loader_from_url(url: str):
    file_ext = url.split("?")[0].split(".")[-1].lower()
    response = requests.get(url)
    if not response.ok:
        raise ValueError(f"Failed to download file: {url}")

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=f".{file_ext}")
    tmp.write(response.content)
    tmp.close()

    if file_ext == "pdf":
        return PyPDFLoader(tmp.name), tmp.name
    elif file_ext in ["doc", "docx"]:
        return UnstructuredWordDocumentLoader(tmp.name), tmp.name
    elif file_ext in ["eml", "msg"]:
        return UnstructuredEmailLoader(tmp.name), tmp.name
    else:
        raise ValueError(f"Unsupported file type: .{file_ext}")

def build_retriever_from_url(url, use_semantic_chunking=True):
    cache_id = url.split("/")[-1].split("?")[0]
    vectordb_path = os.path.join(CACHE_DIR, f"faiss_{cache_id}")
    splits_path = os.path.join(CACHE_DIR, f"splits_{cache_id}.pkl")

    if os.path.exists(vectordb_path) and os.path.exists(splits_path):
        print(f"📦 Loading from cache: {cache_id}")
        vectordb = FAISS.load_local(vectordb_path, embedding, allow_dangerous_deserialization=True)
        with open(splits_path, "rb") as f:
            splits = pickle.load(f)
    else:
        print(f"🔍 Building retriever for {cache_id}...")
        loader, temp_path = get_loader_from_url(url)
        pages = loader.load()
        full_text = "\\n".join([page.page_content for page in pages])

        if use_semantic_chunking:
            try:
                print("🔍 Using Semantic Chunking...")
                splitter = SemanticChunker(embedding)
                splits = splitter.create_documents([full_text])
            except Exception as e:
                print(f"⚠ Semantic Chunking failed: {e}. Falling back to RecursiveCharacterTextSplitter...")
                splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
                splits = splitter.create_documents([full_text])
        else:
            splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
            splits = splitter.create_documents([full_text])

        vectordb = FAISS.from_documents(splits, embedding=embedding)
        vectordb.save_local(vectordb_path)

        with open(splits_path, "wb") as f:
            pickle.dump(splits, f)

    faiss_retriever = vectordb.as_retriever(search_kwargs={"k": 3})
    bm25_retriever = BM25Retriever.from_documents(splits)
    bm25_retriever.k = 3

    ensemble_retriever = EnsembleRetriever(
        retrievers=[faiss_retriever, bm25_retriever],
        weights=[0.5, 0.5],
    )

    return ensemble_retriever
""",
    f"{base_path}/requirements.txt": """fastapi
uvicorn
langchain
langchain-community
langchain-experimental
langchain-google-genai
langchain-cohere
langchain-groq
faiss-cpu
requests
python-dotenv
""",
    f"{base_path}/README.md": """# HackRx API with FastAPI & LangChain

This project provides an API to:
✅ Download a document  
✅ Chunk text using Semantic Chunking (with fallback)  
✅ Build FAISS & BM25 retrievers for hybrid search  
✅ Answer questions using Groq LLaMA  
✅ Cache FAISS index  

---

## Setup
```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
