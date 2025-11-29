# LLM Analysis Quiz – Endpoint Solver  
IIT Madras (BS Data Science) – TDS LLM Analysis Quiz Project  
Author: Ruturaj (email: 23f1001967@ds.study.iitm.ac.in)

This project implements the required API endpoint that receives quiz tasks,
fetches the quiz page, interprets the instructions, processes the data, and
submits the answer back to the specified submit URL.

The application uses:
- FastAPI for the HTTP endpoint  
- Playwright (headless Chromium) for JavaScript-rendered pages  
- Rule-based parsing for known quiz patterns  
- Optional GPT-5 (gpt-5.1-mini) fallback for unusual formats  
- Pandas for data/CSV handling  

## How it works (short summary)
1. The server exposes a POST `/` endpoint.  
2. It validates the secret and returns HTTP 200/403/400 as required.  
3. A background task runs the quiz solver.  
4. The solver:
   - Opens the quiz URL with Playwright  
   - Reads all visible text  
   - Detects instructions like submit URLs, CSV links, secret codes  
   - Handles multi-URL quiz chains within the 3-minute window  
   - Tries multiple candidate answers when uncertain  
   - Falls back to GPT-5 (gpt-5.1-mini) only when needed  
5. Answers are posted back exactly as the quiz page specifies.

## Running locally
Install dependencies:
