from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.requests import Request
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
import os
import asyncio

from .browser import get_page_text, get_page_html
from .llm import llm_extract_answer

app = FastAPI()

# basic config
DEFAULT_EMAIL = "23f1001967@ds.study.iitm.ac.in"
DEFAULT_SECRET = "ruturaj-quiz-2025-xyz"

QUIZ_EMAIL = os.getenv("QUIZ_EMAIL", DEFAULT_EMAIL)
QUIZ_SECRET = os.getenv("QUIZ_SECRET", DEFAULT_SECRET)


class QuizRequest(BaseModel):
    email: str
    secret: str
    url: str


def solve_quiz_chain(email: str, secret: str, url: str) -> None:
    import re
    import time
    import json
    from urllib.parse import urlparse, urljoin
    from io import StringIO, BytesIO

    import httpx
    import pandas as pd

    print("quiz start:", email, url)
    start = time.time()
    current_url = url

    while current_url and (time.time() - start) < 170:
        print("\npage:", current_url)

        # grab visible text from the page
        try:
            text = asyncio.run(get_page_text(current_url))
        except Exception as e:
            print("playwright error:", repr(e))
            break

        print("snippet:", text[:200].replace("\n", " ")[:200])

        parsed = urlparse(current_url)
        base_url = f"{parsed.scheme}://{parsed.netloc}"

        # locate submit url
        submit_url = None
        patterns = [
            "Post your answer to",
            "POST your answer to",
            "POST this JSON to",
            "Post this JSON to",
            "POST the secret code back to",
            "Post the secret code back to",
        ]
        for pat in patterns:
            if pat in text:
                tail = text.split(pat, 1)[1]
                m = re.search(r"https?://\S+|/submit\S*", tail)
                if m:
                    raw = m.group(0).strip().rstrip(".")
                    submit_url = raw if raw.startswith("http") else urljoin(base_url, raw)
                    break

        if not submit_url and "/submit" in text:
            submit_url = urljoin(base_url, "/submit")

        print("submit_url:", submit_url)
        if not submit_url:
            break

        # find any direct file url in text
        file_url = None
        m_file = re.search(r"https?://\S+\.(csv|xlsx|json)\S*", text, re.IGNORECASE)
        if m_file:
            file_url = m_file.group(0)
        print("file_url (text):", file_url)

        lowered = text.lower()
        answers_to_try: list = []

        # case 1: simple demo "anything you want"
        if '"answer": "anything you want"' in text or "'answer': 'anything you want'" in text:
            answers_to_try.append("hello-from-ruturaj")
            print("pattern: anything you want")

        # case 2: scrape a secret code
        if not answers_to_try and "scrape " in lowered and "secret code" in lowered:
            scrape_url = None
            m = re.search(r"Scrape\s+(\S+)", text)
            if m:
                rel = m.group(1).strip("()")
                scrape_url = urljoin(base_url, rel)
            print("scrape_url:", scrape_url)

            if scrape_url:
                try:
                    scrape_text = asyncio.run(get_page_text(scrape_url))
                except Exception as e:
                    print("scrape error:", repr(e))
                    break

                print("scrape snippet:", scrape_text[:200].replace("\n", " ")[:200])

                code = None
                m2 = re.search(r"secret code.*?(\d+)", scrape_text, re.IGNORECASE)
                if m2:
                    code = m2.group(1).strip()
                else:
                    m3 = re.search(r"(\d+)", scrape_text)
                    if m3:
                        code = m3.group(1).strip()

                print("secret code:", code)
                if code:
                    answers_to_try.append(int(code) if code.isdigit() else code)

        # case 3: file based (csv/xlsx/json)
        df = None
        cutoff = None
        if not answers_to_try and "csv file" in lowered:
            if not file_url:
                try:
                    html = asyncio.run(get_page_html(current_url))
                    m_html = re.search(r'href="([^"]+\.csv[^"]*)"', html, re.IGNORECASE)
                    if m_html:
                        rel = m_html.group(1)
                        file_url = urljoin(base_url, rel)
                except Exception as e:
                    print("html error:", repr(e))
            print("file_url (html):", file_url)

            if file_url:
                try:
                    with httpx.Client(timeout=120.0) as client:
                        resp = client.get(file_url)
                        resp.raise_for_status()
                        ctype = resp.headers.get("content-type", "").lower()
                except Exception as e:
                    print("download error:", repr(e))
                    break

                try:
                    if file_url.lower().endswith(".csv") or "text/csv" in ctype:
                        df = pd.read_csv(StringIO(resp.text))
                    elif file_url.lower().endswith(".xlsx") or "spreadsheetml" in ctype:
                        df = pd.read_excel(BytesIO(resp.content))
                    elif file_url.lower().endswith(".json") or "application/json" in ctype:
                        df = pd.read_json(StringIO(resp.text))
                except Exception as e:
                    print("dataframe error:", repr(e))
                    df = None

                if df is not None:
                    print("columns:", list(df.columns))

                    m_cut = re.search(r"cutoff\s*[:\-]\s*(\d+)", lowered, re.IGNORECASE)
                    if m_cut:
                        cutoff = int(m_cut.group(1))
                        print("cutoff:", cutoff)

                    num_cols = df.select_dtypes(include="number").columns
                    cand = []

                    if cutoff is not None and len(num_cols) > 0:
                        col = num_cols[0]
                        # try several reasonable aggregates
                        cand.append(int(df[col].sum()))                       # sum all
                        cand.append(int(df[col][df[col] > cutoff].sum()))     # sum >
                        cand.append(int(df[col][df[col] >= cutoff].sum()))    # sum >=
                        cand.append(int(df[col][df[col] < cutoff].sum()))     # sum <
                    elif "value" in df.columns:
                        s = df["value"].sum()
                        cand.append(int(s) if float(s).is_integer() else float(s))

                    # dedupe, keep order
                    seen = set()
                    for c in cand:
                        if c not in seen:
                            seen.add(c)
                            answers_to_try.append(c)

                    print("file candidates:", answers_to_try)

        # LLM fallback if rules didn't produce anything
        if not answers_to_try:
            print("llm fallback...")
            llm_out = llm_extract_answer(text)
            if llm_out and "answer" in llm_out:
                answers_to_try.append(llm_out["answer"])
                print("llm answer:", llm_out["answer"])

        if not answers_to_try:
            print("no candidates, stop")
            break

        # try candidates, stop when accepted or new url given
        for ans in answers_to_try:
            if (time.time() - start) > 170:
                print("time limit hit")
                current_url = None
                break

            payload = {
                "email": email,
                "secret": secret,
                "url": current_url,
                "answer": ans,
            }
            print("submit:", submit_url, "answer:", ans)

            try:
                with httpx.Client(timeout=60.0) as client:
                    r = client.post(submit_url, json=payload)
                    r.raise_for_status()
                    data = r.json()
            except Exception as e:
                print("submit error:", repr(e))
                current_url = None
                break

            print("response:", json.dumps(data, indent=2))

            if data.get("correct"):
                print("accepted")
                current_url = data.get("url")
                break

            if data.get("url"):
                print("new url:", data["url"])
                current_url = data["url"]
                break

        else:
            print("all candidates failed")
            current_url = None

    print("quiz end")


@app.post("/")
def handle_quiz(body: QuizRequest, background_tasks: BackgroundTasks):
    if body.secret != QUIZ_SECRET:
        raise HTTPException(status_code=403, detail="Invalid secret")

    # run solver in background so HTTP response is quick
    background_tasks.add_task(solve_quiz_chain, body.email, body.secret, body.url)

    return {
        "status": "accepted",
        "email": body.email,
        "url": body.url,
    }
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=400,
        content={"detail": "Invalid JSON payload"},
    )

