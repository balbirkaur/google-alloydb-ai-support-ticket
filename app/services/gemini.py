from google import generativeai as genai
import os

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

def summarize_text(text: str):
    response = genai.GenerativeModel("gemini-1.5-flash").generate_content(
        f"Summarize this support issue in 1-2 lines:\n{text}"
    )
    return response.text