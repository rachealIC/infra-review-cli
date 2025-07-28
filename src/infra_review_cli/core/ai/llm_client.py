# src/infra_review_cli/ai/llm_client.py

import os
from dotenv import load_dotenv
import google.generativeai as genai

from openai import OpenAI

load_dotenv()

# Configure Gemini
try:
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    GEMINI = genai.GenerativeModel("gemini-2.5-flash")
except Exception:
    GEMINI = None

# Configure OpenAI
try:
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    print(f"keys {client}")
except Exception:
    client = None


def call_gemini(prompt: str) -> str:
    if not GEMINI:
        raise RuntimeError("Gemini not configured.")
    return GEMINI.generate_content(prompt).text.strip()


def call_openai(prompt: str, model="gpt-4o-mini") -> str:

    if not client:
        raise RuntimeError("OpenAI not configured.")
    try:
        response = client.responses.create(
            model=model,
            instructions="You are a cloud infrastructure expert. Your answers are direct and professional.",
            input=prompt
        )
        return response.output_text.strip()
    except Exception as e:
        print(f"⚠️ OpenAI fallback failed: {e}")
        return "AI fallback failed."