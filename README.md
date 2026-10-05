# Repo Explorer

A small web app that lists a GitHub user's public repositories and can
summarize a repo's README with AI.

## Features

- Search any GitHub username and see repos sorted by stars or name
- Handles pagination, unknown users, rate limits, and network failures
- In-memory caching so repeat searches don't spend API requests
- "Summarize" button that sends a README to a model on Groq
- Automated tests (pytest) that never call real services

## Tech stack

- Python, FastAPI, Jinja2, httpx
- GitHub REST API
- Groq API (OpenAI-compatible chat completions)
- pytest

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
```

Fill in `.env` with your own keys, then run:

```bash
uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000

## Configuration

| Variable | Purpose |
|---|---|
| `GITHUB_TOKEN` | Raises the GitHub rate limit from 60 to 5,000 requests per hour |
| `GROQ_API_KEY` | Enables AI summaries |
| `GROQ_BASE_URL` | Groq's OpenAI-compatible endpoint |
| `GROQ_MODEL` | Which model writes the summaries |

## Tests

```bash
python -m pytest -v
```

## Known limitations

- The cache lives in memory, so it resets on restart and is not shared between workers.
- The summary endpoint has no per-user limits, so it needs protection before public deployment.