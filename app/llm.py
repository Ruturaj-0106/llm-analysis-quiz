import os
import json
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

SYSTEM_PROMPT = """
You are a helper that reads quiz pages and extracts the final answer.
You MUST always respond with valid JSON only, no extra text.

Format:
{
  "answer": <the final answer value: number, string, or boolean>
}
"""

def llm_extract_answer(page_text: str) -> dict | None:
    try:
        resp = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": page_text},
            ],
            temperature=0,
        )
        content = resp.choices[0].message.content
        return json.loads(content)
    except Exception as e:
        print("LLM error:", repr(e))
        return None
