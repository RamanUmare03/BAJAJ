from langchain_google_genai import GoogleGenerativeAIEmbeddings
import os

google_api_key = os.getenv("GOOGLE_API_KEY")  # Make sure it's set in your .env file

if not google_api_key:
    raise ValueError("GOOGLE_API_KEY is not set in environment variables")

embedding = GoogleGenerativeAIEmbeddings(
    model="models/embedding-001",
    google_api_key=google_api_key
)
