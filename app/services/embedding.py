from google import generativeai as genai
import os

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

def get_embedding(text: str):
    model = genai.GenerativeModel("embedding-001")

    response = model.embed_content(
        content=text,
        task_type="retrieval_query"
    )

    return response["embedding"]