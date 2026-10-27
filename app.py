import os, sqlite3
from pathlib import Path
from datetime import datetime, timezone
from io import BytesIO
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from openai import OpenAI
from pypdf import PdfReader
from pydantic import BaseModel

load_dotenv()
ROOT=Path(__file__).resolve().parent
DB=ROOT/"assistant.db"
app=FastAPI(title="Personal AI Assistant")
app.mount("/static", StaticFiles(directory=ROOT/"static"), name="static")

def connect():
    c=sqlite3.connect(DB); c.row_factory=sqlite3.Row; return c

def init_db():
    with connect() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS messages(
        id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT NOT NULL,
        role TEXT NOT NULL, content TEXT NOT NULL, created_at TEXT NOT NULL)""")
        c.execute("CREATE INDEX IF NOT EXISTS idx_session ON messages(session_id,id)")

@app.on_event("startup")
def startup(): init_db()

def client():
    key=os.getenv("OPENAI_API_KEY","").strip()
    if not key: raise HTTPException(503,"Set OPENAI_API_KEY in your .env file first.")
    return OpenAI(api_key=key)

def ask(messages):
    try:
        r=client().chat.completions.create(model=os.getenv("OPENAI_MODEL","gpt-4.1-mini"),messages=messages,temperature=.4)
        return r.choices[0].message.content or "No response was generated."
    except HTTPException: raise
    except Exception as e: raise HTTPException(502,f"AI provider request failed: {type(e).__name__}") from e

def save(sid,role,content):
    with connect() as c:
        c.execute("INSERT INTO messages(session_id,role,content,created_at) VALUES(?,?,?,?)",
                  (sid,role,content,datetime.now(timezone.utc).isoformat()))

class Chat(BaseModel):
    session_id: str
    message: str
    mode: str="chat"

@app.get("/")
def home(): return FileResponse(ROOT/"static"/"index.html")

@app.get("/api/health")
def health(): return {"status":"ok","ai_configured":bool(os.getenv("OPENAI_API_KEY","").strip())}

@app.post("/api/chat")
def chat(q:Chat):
    sid=q.session_id.strip()[:100]; msg=q.message.strip()
    if not sid or not msg: raise HTTPException(400,"Session ID and message are required.")
    if len(msg)>12000: raise HTTPException(413,"Message is too long (max 12,000 characters).")
    with connect() as c:
        rows=c.execute("SELECT role,content FROM messages WHERE session_id=? ORDER BY id DESC LIMIT 16",(sid,)).fetchall()
    history=[{"role":r["role"],"content":r["content"]} for r in reversed(rows)]
    system="You are a helpful personal AI assistant. Be clear, accurate, and admit uncertainty."
    if q.mode=="coding": system+=" Act as a coding tutor: explain code, help debug, and provide readable examples."
    save(sid,"user",msg)
    answer=ask([{"role":"system","content":system}]+history+[{"role":"user","content":msg}])
    save(sid,"assistant",answer)
    return {"reply":answer,"session_id":sid}

@app.get("/api/history/{session_id}")
def history(session_id:str):
    with connect() as c:
        rows=c.execute("SELECT id,role,content,created_at FROM messages WHERE session_id=? ORDER BY id",(session_id[:100],)).fetchall()
    return {"messages":[dict(r) for r in rows]}

@app.delete("/api/history/{session_id}")
def clear(session_id:str):
    with connect() as c: c.execute("DELETE FROM messages WHERE session_id=?",(session_id[:100],))
    return {"status":"cleared"}

@app.post("/api/summarize-pdf")
async def summarize_pdf(file:UploadFile=File(...), session_id:str="pdf-summary"):
    if not (file.filename or "").lower().endswith(".pdf"):
        raise HTTPException(400,"Please upload a PDF file.")
    raw=await file.read()
    if not raw: raise HTTPException(400,"The PDF is empty.")
    if len(raw)>12*1024*1024: raise HTTPException(413,"Maximum PDF size is 12 MB.")
    try:
        reader=PdfReader(BytesIO(raw))
        if reader.is_encrypted: raise HTTPException(400,"Encrypted PDFs are not supported.")
        text="\n\n".join((p.extract_text() or "") for p in reader.pages[:80]).strip()[:45000]
    finally: await file.close()
    if not text: raise HTTPException(400,"No selectable text found. Scanned PDFs need OCR.")
    summary=ask([{"role":"system","content":"Summarize documents faithfully. Do not invent details."},
                 {"role":"user","content":"Summarize this PDF with Overview, Key Points, Important Details, and Questions to Consider:\n\n"+text}])
    sid=session_id.strip()[:100] or "pdf-summary"
    save(sid,"user",f"Summarize PDF: {file.filename}"); save(sid,"assistant",summary)
    return {"filename":file.filename,"summary":summary,"characters_processed":len(text)}
