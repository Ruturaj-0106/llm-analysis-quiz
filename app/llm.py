import os
import json
from openai import OpenAI

# Load key from environment
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# System prompt kept intentionally simple and strict.
SYSTEM_PROMPT = (
    "Read the given quiz page text and extract only the final answer. "
    "Return strictly in JSON: {\"answer\": ...}. No extra text."
)

def llm_extract_answer(page_text: str):
    """
    When a quiz page does not match known patterns,
    this helper asks an LLM to guess the final answer.

    It always expects a JSON reply with an 'answer' field.
    """
    try:
        resp = client.chat.completions.create(
            model="gpt-4.1-mini",   # GPT-5 fallback model
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": page_text},
            ],
            temperature=0
        )

        content = resp.choices[0].message.content
        data = json.loads(content)

        return data
    except Exception as e:
        # Only minimal logging – this file stays simple & readable.
        print("LLM fallback failed:", str(e))
        return None
