from fastapi import APIRouter, Security, HTTPException, Header
from pydantic import BaseModel, HttpUrl
from typing import List, Annotated
from .utils import build_retriever_from_url
from .llm import process_single_query
import os
import asyncio

API_KEY = "50255bc08e08f6431861bace6cb7232a1a9c317758fc6afd177cfd01ba3cff9a"
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
