from fastapi import APIRouter, Security, HTTPException, Header
from pydantic import BaseModel, HttpUrl
from typing import List, Annotated
from .utils import build_retriever_from_url
from .llm import process_single_query
import os
import asyncio
from dotenv import load_dotenv
load_dotenv()


API_KEY = "7ae90faf72ce42e929314a6192e64395286019a5982e85589efeab8312d6061f"
BEARER_TOKEN = f"Bearer {API_KEY}"

router = APIRouter()

class HackRxRequest(BaseModel):
    documents: HttpUrl
    questions: List[str]

async def get_api_key(authorization: Annotated[str | None, Header()] = None):
    if authorization is None:
        raise HTTPException(status_code=401, detail="Authorization header is missing")
    if authorization != BEARER_TOKEN:
        raise HTTPException(status_code=403, detail="Invalid API Key")

@router.post("/api/v1/hackrx/run")
async def handle_hackrx_request(
    request_data: HackRxRequest,
    api_key: str = Security(get_api_key),
):
    document_url = request_data.documents
    ensemble_retriever, temp_file_path = build_retriever_from_url(document_url)

    tasks = [process_single_query(ensemble_retriever, query) for query in request_data.questions]
    answers = await asyncio.gather(*tasks)

    if os.path.exists(temp_file_path):
        os.remove(temp_file_path)

    return {"answers": answers}
