from fastapi import FastAPI
from .routes import router

app = FastAPI(
    title="HackRx API Processor",
    description="API to process documents and answer questions",
    version="1.0.0"
)

app.include_router(router)

@app.post("/api/v1/hackrx/run")
async def root():
    return {"message": "HackRx API is running!"}
