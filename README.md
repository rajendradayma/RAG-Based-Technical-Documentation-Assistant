# RAG-Based Technical Documentation Assistant

A self-corrective RAG pipeline built with **LangGraph**, served via **FastAPI** and **Streamlit**, using **Groq** (LLM), **FAISS** (vector store), and **sentence-transformers** (embeddings).

Live demo: [Streamlit app](https://rag-based-technical-documentation-assistant-cpjoafmat8ajbj3ptv.streamlit.app/)

## Overview

This system answers natural-language questions about a small corpus of technical documentation (FastAPI, Pydantic, LangGraph, and ChromaDB basics) using a LangGraph `StateGraph` with retrieval, LLM-based document grading, query rewriting on failure, and grounded answer generation with citations.

## Architecture

```
analyze_query → retrieve → grade_documents ─┬─► generate ─► END
                    ▲                        │
                    │                        ├─► transform_query ─► retrieve (loop, max 2 retries)
                    └────────────────────────┘
                                              └─► web_search (bonus, if Tavily key set) ─► generate
```

### Nodes

1. **analyze_query** — Classifies the question (`conceptual` / `how-to` / `troubleshooting` / `api-reference`) and rewrites it into a more retrieval-friendly search query (adds synonyms, expands abbreviations).
2. **retrieve** — Runs a similarity search against a local FAISS index (top-`k=4` chunks), using `all-MiniLM-L6-v2` sentence-transformer embeddings.
3. **grade_documents** — For each retrieved chunk, asks the LLM "is this relevant to the question? yes/no". Filters to `relevant_documents`.
4. **transform_query** — If *no* chunks were graded relevant and the retry budget (`MAX_RETRIES = 2`) isn't exhausted, the LLM rewrites the search query with different keywords and the graph loops back to `retrieve`.
5. **web_search** *(bonus)* — If retries are exhausted and a `TAVILY_API_KEY` is configured, falls back to a live web search before generation.
6. **generate** — Produces the final answer grounded in `relevant_documents`, including code examples from context where relevant, with a deduplicated `Sources:` line. If no relevant context exists, it honestly returns "I don't have enough information...".

### State Schema (`graph.py: GraphState`)

| Field | Type | Purpose |
|---|---|---|
| `question` | `str` | Original user question (immutable) |
| `search_query` | `str` | Current (possibly rewritten) query used for retrieval |
| `query_type` | `str` | Classification from query analysis |
| `documents` | `List[dict]` | All retrieved chunks with grading verdicts |
| `relevant_documents` | `List[dict]` | Chunks that passed grading |
| `retries` | `int` | Number of rewrite/re-retrieve cycles performed |
| `answer` | `str` | Final generated answer |
| `used_web_search` | `bool` | Whether the bonus web fallback fired |
| `sources` | `List[str]` | Source identifiers cited in the answer |

The `retries` counter is incremented inside `transform_query` and checked in the conditional edge `route_after_grading`, which is the self-corrective / cyclical core of the graph.

## Document Corpus & Chunking Strategy

The corpus (`corpus/*.md`) contains four short reference docs: FastAPI basics, Pydantic basics, LangGraph basics, and ChromaDB basics — written so the assistant has clear ground-truth answers and clear ground-truth gaps (asking about something unrelated triggers the retry / "I don't know" path).

**Chunking**: `RecursiveCharacterTextSplitter` with `chunk_size=800`, `chunk_overlap=120`, and a separator priority of `["\n## ", "\n### ", "\n\n", "\n```", "\n", " ", ""]`.

- 800 chars (~150–200 tokens) is large enough to contain a full explanation + one code example, but small enough that grading and generation stay focused and citations stay precise.
- Prioritizing markdown heading and paragraph breaks means chunks tend to align with conceptual sections rather than splitting mid-explanation.
- 120-char overlap helps preserve continuity when a code block or explanation straddles a chunk boundary.

**Embeddings**: `sentence-transformers/all-MiniLM-L6-v2` — free, runs locally/CPU, no API key required.

**Vector store**: local FAISS index (`IndexFlatIP` over normalized embeddings = cosine similarity), persisted to `faiss_index/`.

**LLM**: Groq (`llama-3.1-8b-instant`) — free tier, very fast, used for query analysis, grading, query rewriting, and generation.

## Project Structure

```
.
├── corpus/
│   ├── fastapi_basics.md
│   ├── pydantic_basics.md
│   ├── langgraph_basics.md
│   └── chromadb_basics.md
├── ingest.py          # FAISS ingestion pipeline
├── graph.py           # LangGraph workflow (nodes, routing, state)
├── main.py            # FastAPI app
├── streamlit_app.py   # Streamlit chat UI
├── requirements.txt
└── README.md
```

## Setup

```bash
git clone <your-repo-url>
cd <your-repo>
pip install -r requirements.txt
```

### Environment Variables

| Variable | Required | Purpose |
|---|---|---|
| `GROQ_API_KEY` | Yes | LLM calls (query analysis, grading, rewriting, generation). Free key: https://console.groq.com/keys |
| `TAVILY_API_KEY` | No | Bonus web-search fallback. Free key: https://tavily.com |

For local runs, create `.streamlit/secrets.toml`:
```toml
GROQ_API_KEY = "your-groq-key"
TAVILY_API_KEY = "your-tavily-key"
```

For FastAPI-only runs, export as shell env vars instead:
```bash
export GROQ_API_KEY="your-groq-key"
export TAVILY_API_KEY="your-tavily-key"
```

## Running Locally

### Streamlit (recommended — simplest, single process)

```bash
streamlit run streamlit_app.py
```

First load builds the FAISS index from `corpus/*.md` automatically (a few seconds).

### FastAPI

```bash
python ingest.py          # build the FAISS index (first time)
uvicorn main:app --reload
```

Visit `http://localhost:8000/docs` for Swagger UI.

## Deploying to Streamlit Community Cloud

1. Push this repo to GitHub.
2. Go to https://share.streamlit.io → "New app".
3. Select your repo, branch `main`, main file path `streamlit_app.py`.
4. Under **Advanced settings → Secrets**, paste:
```toml
   GROQ_API_KEY = "your-groq-key"
   TAVILY_API_KEY = "your-tavily-key"
```
5. Deploy. First load builds the FAISS index from `corpus/`.

> Note: Streamlit Cloud's filesystem is ephemeral — `faiss_index/` and `feedback_log.jsonl` reset on redeploy/restart. The index is rebuilt automatically on startup.

## API Reference (FastAPI)

### `POST /query`
```json
// Request
{ "question": "How do I define a request body model in FastAPI using Pydantic?" }

// Response
{
  "answer": "To define a request body... \n\nSources: fastapi_basics.md, pydantic_basics.md",
  "sources": ["fastapi_basics.md", "pydantic_basics.md"],
  "query_type": "how-to",
  "retries": 0,
  "used_web_search": false
}
```

### `POST /ingest`
Multipart file upload (`file`) OR form fields `source_name` + `text`.
```json
{ "source": "custom_note.md", "chunks_added": 1 }
```

### `GET /documents`
```json
{
  "total_chunks": 17,
  "sources": [
    {"source": "chromadb_basics.md", "chunks": 4},
    {"source": "fastapi_basics.md", "chunks": 4},
    {"source": "langgraph_basics.md", "chunks": 5},
    {"source": "pydantic_basics.md", "chunks": 4}
  ]
}
```

### `POST /feedback`
```json
{ "question": "...", "answer": "...", "rating": "up", "comment": "optional" }
```

## Example Queries to Try

- "How do I define a request body model in FastAPI using Pydantic?" → answers with code from `pydantic_basics.md` / `fastapi_basics.md`
- "How do I create a collection in ChromaDB and add documents to it?" → answers from `chromadb_basics.md`
- "What is LangGraph's conditional edge used for?" → answers from `langgraph_basics.md`
- "What is the capital of France?" → off-topic, demonstrates the retry / fallback path (`retries: 2`, "I don't have enough information...")

## Design Decisions & Tradeoffs

- **Groq + llama-3.1-8b-instant**: chosen for a generous free tier and very low latency, important since the graph makes multiple LLM calls per query (analysis, grading per-chunk, possibly rewrite, generation). Defensive JSON parsing in `analyze_query` handles occasional formatting inconsistencies from the smaller model.
- **Per-chunk grading**: grading each chunk individually (rather than one combined call) is more accurate and lets us filter precisely, at the cost of `top_k` extra LLM calls per query.
- **FAISS + MiniLM embeddings**: zero-cost, no API key, no external service, avoids dependency conflicts (chromadb's telemetry/grpc/protobuf chain caused deployment failures on newer Python). `IndexFlatIP` over normalized vectors gives exact cosine similarity, fine at this corpus scale.
- **MAX_RETRIES = 2**: keeps worst-case latency bounded (at most 3 retrieval rounds) while still allowing the self-correction loop to demonstrate value.
- **Web search bonus is optional/graceful**: if `TAVILY_API_KEY` isn't set, `web_search` is a no-op and the graph routes to `generate`, which returns the honest "I don't have enough information" message.
- **Sources/answer consistency**: `generate` strips any model-written `Sources:` line and appends a clean deduplicated one; if the model still returns the "I don't have enough information" fallback despite having context, `sources` is forced empty to avoid a contradictory footer.
- **In-memory/file feedback**: `/feedback` appends to a JSONL file rather than a database, appropriate for this scope.

## Assumptions

- A small (4-doc) markdown corpus is sufficient to demonstrate the architecture; the ingestion pipeline generalizes to any `.md` files dropped into `corpus/`.
- Free-tier CPU (Streamlit Cloud / local) is fine for MiniLM embeddings at this corpus scale.
- Conversation memory and a full hallucination-check node were treated as stretch goals beyond the core 2-day scope.

## What I'd Improve With More Time

- **Hallucination/groundedness check node** (Self-RAG style): after `generate`, run a second LLM pass that checks each claim against `relevant_documents`, looping back to `generate` or flagging unsupported claims.
- **Conversation memory**: thread a chat-history list through `GraphState` and prepend it in `analyze_query`/`generate` for follow-up questions.
- **Batch grading**: grade all `top_k` chunks in a single structured-JSON LLM call to cut latency/cost.
- **Persistent vector store** (e.g. a hosted FAISS/pgvector instance) so the index survives platform restarts without rebuilding from `corpus/`.
