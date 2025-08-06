import requests
import tempfile
import os
import pickle
from langchain_community.document_loaders import PyPDFLoader, UnstructuredWordDocumentLoader, UnstructuredEmailLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_experimental.text_splitter import SemanticChunker
from langchain_community.vectorstores import FAISS
from langchain_community.retrievers import BM25Retriever
from langchain.retrievers.ensemble import EnsembleRetriever
from .embedding import embedding

def get_loader_from_url(url: str):
    url_str = str(url)
    file_ext = url_str.split("?")[0].split(".")[-1].lower()

    response = requests.get(url_str)
    if not response.ok:
        raise ValueError(f"Failed to download file: {url_str}")

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

def build_retriever_from_url(url: str):
    loader, temp_path = get_loader_from_url(url)
    pages = loader.load()
    full_text = "\n".join([page.page_content for page in pages])

    # ✅ Semantic Chunking
    splitter = SemanticChunker(embedding, breakpoint_threshold_type="interquartile", buffer_size=2)
    splits = splitter.split_text(full_text)

    # Convert splits into LangChain Document objects
    from langchain.docstore.document import Document
    docs = [Document(page_content=chunk) for chunk in splits]

    # ✅ Build FAISS Vector DB
    vectordb = FAISS.from_documents(docs, embedding=embedding)

    # ✅ Ensemble Retriever (FAISS + BM25)
    faiss_retriever = vectordb.as_retriever(search_kwargs={"k": 3})
    bm25_retriever = BM25Retriever.from_documents(docs)
    bm25_retriever.k = 3

    ensemble_retriever = EnsembleRetriever(
        retrievers=[faiss_retriever, bm25_retriever],
        weights=[0.5, 0.5],
    )

    return ensemble_retriever, temp_path
