"""
Streamlit frontend for the RAG Technical Documentation Assistant.

This app runs the LangGraph pipeline directly in-process (no separate
FastAPI server needed) - simplest setup for Streamlit Community Cloud.

Required secrets (Settings -> Secrets on Streamlit Cloud, or .streamlit/secrets.toml locally):
    GROQ_API_KEY = "your-groq-key"
    TAVILY_API_KEY = "your-tavily-key"   # optional, bonus web-search fallback
"""

import os
import json
import time
import os
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"

import streamlit as st
import streamlit as st

# --- Load secrets into environment BEFORE importing graph/ingest modules ----
# (graph.py reads os.environ at call-time, so this must happen first)
if "GROQ_API_KEY" in st.secrets:
    os.environ["GROQ_API_KEY"] = st.secrets["GROQ_API_KEY"]
if "TAVILY_API_KEY" in st.secrets:
    os.environ["TAVILY_API_KEY"] = st.secrets["TAVILY_API_KEY"]

from ingest import build_index, add_text_document, get_documents_summary, get_collection
from graph import run_query


FEEDBACK_FILE = "feedback_log.jsonl"

st.set_page_config(
    page_title="RAG Technical Docs Assistant",
    page_icon="📚",
    layout="wide",
)


# ---------------------------------------------------------------------------
# Index initialization (runs once per deployment, cached)
# ---------------------------------------------------------------------------

@st.cache_resource(show_spinner=False)
def init_index():
    """Build the vector index from corpus/ on first run if the collection is empty."""
    try:
        collection = get_collection()
        if collection.count() == 0:
            build_index(reset=False)
        return True
    except Exception as e:
        return str(e)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def save_feedback(question: str, answer: str, rating: str, comment: str = ""):
    entry = {
        "timestamp": time.time(),
        "question": question,
        "answer": answer,
        "rating": rating,
        "comment": comment,
    }
    with open(FEEDBACK_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

with st.sidebar:
    st.title("📚 RAG Docs Assistant")
    st.caption("Self-corrective LangGraph RAG pipeline")

    if not os.environ.get("GROQ_API_KEY"):
        st.error("GROQ_API_KEY not set. Add it in Settings -> Secrets.")
        st.stop()

    init_result = init_index()
    if init_result is not True:
        st.error(f"Index init failed: {init_result}")
        st.stop()

    st.success("Vector index ready ✅")

    tavily_configured = bool(os.environ.get("TAVILY_API_KEY"))
    st.caption(
        f"Web search fallback: {'enabled' if tavily_configured else 'disabled'}"
    )

    st.divider()
    st.subheader("📄 Indexed Documents")
    try:
        summary = get_documents_summary()
        st.write(f"**Total chunks:** {summary['total_chunks']}")
        for s in summary["sources"]:
            st.write(f"- `{s['source']}` — {s['chunks']} chunks")
    except Exception as e:
        st.warning(f"Could not load document summary: {e}")

    st.divider()
    st.subheader("➕ Add a Document")
    with st.form("ingest_form", clear_on_submit=True):
        new_source_name = st.text_input("Source name (e.g. my_notes.md)")
        new_text = st.text_area("Document text (Markdown)", height=120)
        submitted = st.form_submit_button("Ingest")
        if submitted:
            if not new_source_name.strip() or not new_text.strip():
                st.warning("Provide both a source name and document text.")
            else:
                try:
                    chunks_added = add_text_document(new_source_name.strip(), new_text)
                    st.success(f"Added {chunks_added} chunk(s) from '{new_source_name}'.")
                    st.cache_resource.clear()
                except Exception as e:
                    st.error(f"Ingest failed: {e}")


# ---------------------------------------------------------------------------
# Main area - chat-style Q&A
# ---------------------------------------------------------------------------

st.title("Ask the Technical Documentation Assistant")
st.caption(
    "Corpus covers: FastAPI, Pydantic, LangGraph, and ChromaDB basics. "
    "Try a question — or ask something off-topic to see the self-correction / fallback path."
)

if "history" not in st.session_state:
    st.session_state.history = []  # list of dicts: question, result

# Render previous Q&A
for i, item in enumerate(st.session_state.history):
    with st.chat_message("user"):
        st.write(item["question"])
    with st.chat_message("assistant"):
        st.write(item["result"]["answer"])

        meta_cols = st.columns(4)
        meta_cols[0].caption(f"Query type: `{item['result']['query_type']}`")
        meta_cols[1].caption(f"Retries: `{item['result']['retries']}`")
        meta_cols[2].caption(f"Web search: `{item['result']['used_web_search']}`")
        meta_cols[3].caption(f"Sources: `{', '.join(item['result']['sources']) or 'none'}`")

        fb_col1, fb_col2, fb_col3 = st.columns([1, 1, 6])
        if fb_col1.button("👍", key=f"up_{i}"):
            save_feedback(item["question"], item["result"]["answer"], "up")
            st.toast("Thanks for the feedback!")
        if fb_col2.button("👎", key=f"down_{i}"):
            save_feedback(item["question"], item["result"]["answer"], "down")
            st.toast("Thanks for the feedback!")

# Chat input
question = st.chat_input("Ask a question about FastAPI, Pydantic, LangGraph, or ChromaDB...")

if question:
    with st.chat_message("user"):
        st.write(question)

    with st.chat_message("assistant"):
        with st.spinner("Running retrieval -> grading -> generation..."):
            try:
                result = run_query(question)
            except Exception as e:
                result = {
                    "answer": f"Error running the workflow: {e}",
                    "sources": [],
                    "query_type": "error",
                    "retries": 0,
                    "used_web_search": False,
                }

        st.write(result["answer"])

        meta_cols = st.columns(4)
        meta_cols[0].caption(f"Query type: `{result['query_type']}`")
        meta_cols[1].caption(f"Retries: `{result['retries']}`")
        meta_cols[2].caption(f"Web search: `{result['used_web_search']}`")
        meta_cols[3].caption(f"Sources: `{', '.join(result['sources']) or 'none'}`")

    st.session_state.history.append({"question": question, "result": result})
    st.rerun()
