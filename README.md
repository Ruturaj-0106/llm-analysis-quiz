# LLM Analysis Quiz – Auto Quiz Solver

## 1. Overview

This project implements an HTTP API endpoint that can automatically solve a sequence of data-related quiz tasks given by a remote server.

The endpoint:
- Validates a secret (to authenticate the student).
- Opens a quiz URL in a **headless browser** (Playwright).
- Reads the page (including JavaScript-rendered content).
- Detects the instructions, data sources, and submit URL.
- Downloads and analyses data files (CSV/Excel/JSON) using **pandas**.
- Submits answers back as JSON.
- Follows a chain of quiz URLs until the quiz finishes or the time limit is reached.

This was implemented as part of the **LLM Analysis Quiz** project.

Student email: `23f1001967@ds.study.iitm.ac.in`  
Secret string: `ruturaj-quiz-2025-xyz`

---

## 2. Architecture

### 2.1 Components

- **FastAPI app (`app/main.py`)**
  - Defines `POST /` endpoint.
  - Validates JSON payload: `{ email, secret, url }`.
  - Checks `secret` against an environment variable or default.
  - Starts a background task `solve_quiz_chain(...)`.

- **Quiz solver (`solve_quiz_chain` in `main.py`)**
  - Core loop that:
    1. Opens the current quiz URL in a headless browser.
    2. Reads visible text (`get_page_text`).
    3. Detects:
       - Submit URL (e.g. `POST this JSON to ...` or `/submit`).
       - Data file URLs (`.csv`, `.xlsx`, `.json`).
       - Special patterns like:
         - `"answer": "anything you want"`
         - Scraping a relative URL for a **secret code**.
         - Using a **cutoff** value for numeric data.
    4. Downloads and analyses data using **httpx + pandas**.
    5. Builds the JSON payload `{ email, secret, url, answer }`.
    6. POSTs to the submit URL.
    7. Checks response:
       - If `correct` and `url` present → follow the next URL.
       - If incorrect but new `url` given → optionally skip to next URL.
       - If no new URL → quiz ends.

- **Headless browser (`app/browser.py`)**
  - Uses Playwright (`async_playwright`) to:
    - `get_page_text(url)` – visible text from the page body.
    - `get_page_html(url)` – full HTML content.
  - This is required because the quiz pages are often JavaScript-rendered.

---

## 3. Endpoint Contract

### 3.1 Request

**URL:** `POST /`  
**Body:**

```json
{
  "email": "23f1001967@ds.study.iitm.ac.in",
  "secret": "ruturaj-quiz-2025-xyz",
  "url": "https://tds-llm-analysis.s-anand.net/demo"
}
