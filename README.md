# Personal AI Assistant

A responsive AI web app built with **Python, FastAPI, SQLite, and an LLM API**. Includes conversational AI, a coding-help mode, PDF summarization, and local chat history.

## Features
- AI chat with saved session history
- Coding assistant mode for explaining and debugging code
- PDF summarization for text-based PDFs
- SQLite database
- FastAPI REST API and interactive API docs
- Responsive dark web interface

## Setup (macOS/Linux)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` and add your own API key. Do not commit `.env` or share your key publicly. API usage may incur charges.

Start the app:

```bash
uvicorn app:app --reload
```

Open http://127.0.0.1:8000. API docs: http://127.0.0.1:8000/docs.

## Main routes

| Method | Route | Purpose |
|---|---|---|
| GET | `/api/health` | Check server and key configuration |
| POST | `/api/chat` | Chat and coding assistant |
| GET | `/api/history/{session_id}` | Read saved chat history |
| DELETE | `/api/history/{session_id}` | Clear chat history |
| POST | `/api/summarize-pdf` | Summarize a PDF upload |

## Project structure

```text
personal-ai-assistant/
├── app.py
├── static/
│   ├── index.html
│   ├── style.css
│   └── app.js
├── requirements.txt
├── .env.example
├── .gitignore
├── LICENSE
└── README.md
```

## Limitations and safety
- Scanned/image-only PDFs need OCR; this starter version extracts selectable text only.
- PDF uploads are limited to 12 MB and 80 pages; extracted text is capped to keep prompts manageable.
- Do not send confidential documents to an external AI provider unless you understand its data policies.
- Before public deployment, add authentication, rate limiting, secure session management, and production monitoring.

## Next improvements
Streaming responses, Markdown/code highlighting, document search with embeddings (RAG), user accounts, tests, and GitHub Actions.

## License
MIT
