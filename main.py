"""
FastAPI application exposing the RAG assistant.

Endpoints:
  POST /query      - submit a question, returns answer + sources + workflow trace
  POST /ingest     - ingest a new text document (file upload or raw text)
  GET  /documents  - list indexed documents (grouped by source)
  POST /feedback   - submit thumbs up/down + optional comment
  GET  /health     - basic health check
"""

import json
import time
from contextlib import asynccontextmanager
from typing import Optional, List

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from ingest import build_index, add_text_document, get_documents_summary, get_collection
from graph import run_query


FEEDBACK_FILE = "feedback_log.jsonl"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Build the vector index from the corpus directory on first run if it's empty."""
    try:
        collection = get_collection()
        if collection.count() == 0:
            build_index(reset=False)
    except Exception as e:
        print(f"Startup ingestion check failed: {e}")
    yield


app = FastAPI(
    title="RAG Technical Documentation Assistant",
    description="Self-corrective LangGraph RAG pipeline over technical docs (FastAPI, Pydantic, LangGraph, ChromaDB).",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class QueryRequest(BaseModel):
    question: str


class QueryResponse(BaseModel):
    answer: str
    sources: List[str]
    query_type: str
    retries: int
    used_web_search: bool


class IngestResponse(BaseModel):
    source: str
    chunks_added: int


class FeedbackRequest(BaseModel):
    question: str
    answer: str
    rating: str  # "up" or "down"
    comment: Optional[str] = None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/query", response_model=QueryResponse)
def query(req: QueryRequest):
    if not req.question or not req.question.strip():
        raise HTTPException(status_code=400, detail="Question must not be empty.")

    try:
        result = run_query(req.question)
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Workflow error: {e}")

    return QueryResponse(
        answer=result.get("answer", ""),
        sources=result.get("sources", []),
        query_type=result.get("query_type", ""),
        retries=result.get("retries", 0),
        used_web_search=result.get("used_web_search", False),
    )


@app.post("/ingest", response_model=IngestResponse)
async def ingest(
    file: Optional[UploadFile] = File(None),
    source_name: Optional[str] = Form(None),
    text: Optional[str] = Form(None),
):
    """
    Accepts EITHER:
      - a file upload (.md / .txt), or
      - form fields `source_name` + `text` for raw text ingestion.
    """
    if file is not None:
        content = (await file.read()).decode("utf-8", errors="ignore")
        name = file.filename or "uploaded_doc.md"
        chunks_added = add_text_document(name, content)
        return IngestResponse(source=name, chunks_added=chunks_added)

    if text is not None and source_name is not None:
        chunks_added = add_text_document(source_name, text)
        return IngestResponse(source=source_name, chunks_added=chunks_added)

    raise HTTPException(
        status_code=400,
        detail="Provide either a file upload, or both 'source_name' and 'text' form fields.",
    )


@app.get("/documents")
def documents():
    try:
        return get_documents_summary()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/feedback")
def feedback(req: FeedbackRequest):
    if req.rating not in ("up", "down"):
        raise HTTPException(status_code=400, detail="rating must be 'up' or 'down'.")

    entry = {
        "timestamp": time.time(),
        "question": req.question,
        "answer": req.answer,
        "rating": req.rating,
        "comment": req.comment,
    }
    with open(FEEDBACK_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")

    return {"status": "received"}
