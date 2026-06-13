"""
LangGraph self-corrective RAG workflow.

Nodes:
  1. analyze_query   - classify + rewrite the user's question
  2. retrieve        - vector similarity search
  3. grade_documents - LLM grades each chunk as relevant/irrelevant
  4. transform_query - rewrite query for re-retrieval (on grading failure)
  5. generate        - produce final answer with citations
  6. web_search      - bonus fallback if vector store has nothing relevant

Conditional edges:
  - after grade_documents: if any relevant docs -> generate
                            elif retries < MAX_RETRIES -> transform_query -> retrieve (loop)
                            else -> web_search (bonus) -> generate, or "no answer" generate
"""

import os
import json
from typing import TypedDict, List

from langgraph.graph import StateGraph, END
from langchain_groq import ChatGroq


MAX_RETRIES = 2
TOP_K = 4


# ---------------------------------------------------------------------------
# State schema
# ---------------------------------------------------------------------------

class GraphState(TypedDict):
    question: str               # original user question (never mutated)
    search_query: str           # current query used for retrieval (may be rewritten)
    query_type: str             # conceptual | how-to | troubleshooting | api-reference
    documents: List[dict]       # list of {"text":..., "source":..., "chunk_index":..., "relevant": bool}
    relevant_documents: List[dict]
    retries: int                # number of rewrite/re-retrieve cycles done
    answer: str                 # final generated answer
    used_web_search: bool       # whether bonus web-search fallback was used
    sources: List[str]          # list of source identifiers cited in the final answer


# ---------------------------------------------------------------------------
# LLM setup
# ---------------------------------------------------------------------------

def get_llm():
    """Groq's free tier hosts fast Llama models - used for all LLM calls."""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY environment variable is not set.")
    return ChatGroq(model="llama-3.1-8b-instant", temperature=0, api_key=api_key)


# ---------------------------------------------------------------------------
# Node 1: Query Analysis
# ---------------------------------------------------------------------------

QUERY_ANALYSIS_PROMPT = """You are a query analysis assistant for a technical documentation search system.

Given the user's question, do two things:
1. Classify it into exactly one of: "conceptual", "how-to", "troubleshooting", "api-reference"
2. Rewrite/expand the question into a search-friendly query that adds relevant synonyms or
   clarifies ambiguous terms, to improve retrieval from a vector store of technical docs
   (FastAPI, Pydantic, LangGraph, ChromaDB).

Respond ONLY with valid JSON in this exact format, no extra text:
{{"query_type": "<type>", "search_query": "<rewritten query>"}}

User question: {question}
"""
def retrieve(state: GraphState) -> dict:
    from ingest import query_index

    results = query_index(state["search_query"], top_k=TOP_K)

    documents = []
    for r in results:
        documents.append({
            "text": r["text"],
            "source": r["source"],
            "chunk_index": r["chunk_index"],
            "relevant": None,
        })

    return {"documents": documents}

def analyze_query(state: GraphState) -> dict:
    llm = get_llm()
    prompt = QUERY_ANALYSIS_PROMPT.format(question=state["question"])
    response = llm.invoke(prompt)
    content = response.content.strip()

    # Defensive parsing - strip markdown fences if the model adds them
    if content.startswith("```"):
        content = content.strip("`")
        if content.startswith("json"):
            content = content[4:]
        content = content.strip()

    try:
        parsed = json.loads(content)
        query_type = parsed.get("query_type", "conceptual")
        search_query = parsed.get("search_query", state["question"])
    except (json.JSONDecodeError, AttributeError):
        query_type = "conceptual"
        search_query = state["question"]

    return {
        "search_query": search_query,
        "query_type": query_type,
        "retries": 0,
    }


# ---------------------------------------------------------------------------
# Node 2: Retrieval
# ---------------------------------------------------------------------------

def retrieve(state: GraphState) -> dict:
    collection = get_collection()
    results = collection.query(
        query_texts=[state["search_query"]],
        n_results=TOP_K,
    )

    documents = []
    docs_list = results.get("documents", [[]])[0]
    metas_list = results.get("metadatas", [[]])[0]

    for text, meta in zip(docs_list, metas_list):
        documents.append({
            "text": text,
            "source": meta.get("source", "unknown"),
            "chunk_index": meta.get("chunk_index", -1),
            "relevant": None,
        })

    return {"documents": documents}


# ---------------------------------------------------------------------------
# Node 3: Document Grading (self-corrective core)
# ---------------------------------------------------------------------------

GRADING_PROMPT = """You are grading whether a retrieved document chunk is relevant to a user question.

User question: {question}

Document chunk:
---
{chunk}
---

Is this chunk relevant to answering the question? Respond with exactly one word: "yes" or "no".
"""


def grade_documents(state: GraphState) -> dict:
    llm = get_llm()
    graded_docs = []
    relevant_docs = []

    for doc in state["documents"]:
        prompt = GRADING_PROMPT.format(question=state["question"], chunk=doc["text"][:1500])
        response = llm.invoke(prompt)
        verdict = response.content.strip().lower()
        is_relevant = verdict.startswith("yes")

        doc_copy = dict(doc)
        doc_copy["relevant"] = is_relevant
        graded_docs.append(doc_copy)

        if is_relevant:
            relevant_docs.append(doc_copy)

    return {
        "documents": graded_docs,
        "relevant_documents": relevant_docs,
    }


# ---------------------------------------------------------------------------
# Node 3b: Transform Query (fallback on irrelevant docs)
# ---------------------------------------------------------------------------

TRANSFORM_PROMPT = """The following search query did not return relevant results from a technical
documentation vector store covering FastAPI, Pydantic, LangGraph, and ChromaDB.

Original question: {question}
Previous search query: {search_query}

Rewrite the search query using different keywords, more general or more specific terms,
to improve retrieval. Respond with ONLY the new search query text, nothing else.
"""


def transform_query(state: GraphState) -> dict:
    llm = get_llm()
    prompt = TRANSFORM_PROMPT.format(
        question=state["question"],
        search_query=state["search_query"],
    )
    response = llm.invoke(prompt)
    new_query = response.content.strip().strip('"')

    return {
        "search_query": new_query,
        "retries": state["retries"] + 1,
    }


# ---------------------------------------------------------------------------
# Node 5 (bonus): Web search fallback
# ---------------------------------------------------------------------------

def web_search(state: GraphState) -> dict:
    """If Tavily key is configured, search the web; otherwise no-op."""
    api_key = os.environ.get("TAVILY_API_KEY")
    if not api_key:
        return {"used_web_search": False}

    try:
        from tavily import TavilyClient
        client = TavilyClient(api_key=api_key)
        results = client.search(query=state["question"], max_results=3)

        web_docs = []
        for r in results.get("results", []):
            web_docs.append({
                "text": r.get("content", ""),
                "source": r.get("url", "web"),
                "chunk_index": -1,
                "relevant": True,
            })

        return {
            "relevant_documents": web_docs,
            "used_web_search": True,
        }
    except Exception:
        return {"used_web_search": False}


# ---------------------------------------------------------------------------
# Node 4: Generation
# ---------------------------------------------------------------------------

GENERATION_PROMPT = """You are a technical documentation assistant. Answer the user's question using
ONLY the information in the provided context. Be clear and accurate.

Do NOT include a "Sources:" line yourself - that will be added separately.

If the context does not contain enough information to answer the question, say so honestly
and respond with exactly: "I don't have enough information in the documentation to answer this question."

Question: {question}

Context:
{context}
"""


def generate(state: GraphState) -> dict:
    relevant_docs = state.get("relevant_documents", [])

    if not relevant_docs:
        return {
            "answer": "I don't have enough information in the documentation to answer this question.",
            "sources": [],
        }

    context_parts = []
    sources = []
    for doc in relevant_docs:
        context_parts.append(f"[Source: {doc['source']}]\n{doc['text']}")
        if doc["source"] not in sources:
            sources.append(doc["source"])

    context = "\n\n---\n\n".join(context_parts)

    llm = get_llm()
    prompt = GENERATION_PROMPT.format(question=state["question"], context=context)
    response = llm.invoke(prompt)

    # Strip any "Sources:" line the model adds anyway, then append a clean,
    # deduplicated one based on the actual relevant_documents sources.
    raw_answer = response.content.strip()
    lines = raw_answer.split("\n")
    answer_lines = [l for l in lines if not l.strip().lower().startswith("sources:")]
    answer_text = "\n".join(answer_lines).strip()

    final_answer = f"{answer_text}\n\nSources: {', '.join(sources)}"

    return {
        "answer": final_answer,
        "sources": sources,
    }


# ---------------------------------------------------------------------------
# Conditional routing
# ---------------------------------------------------------------------------

def route_after_grading(state: GraphState) -> str:
    if state["relevant_documents"]:
        return "generate"
    if state["retries"] < MAX_RETRIES:
        return "transform_query"
    # Out of retries - try web search fallback if configured, else give up
    if os.environ.get("TAVILY_API_KEY"):
        return "web_search"
    return "generate"


# ---------------------------------------------------------------------------
# Build the graph
# ---------------------------------------------------------------------------

def build_graph():
    workflow = StateGraph(GraphState)

    workflow.add_node("analyze_query", analyze_query)
    workflow.add_node("retrieve", retrieve)
    workflow.add_node("grade_documents", grade_documents)
    workflow.add_node("transform_query", transform_query)
    workflow.add_node("web_search", web_search)
    workflow.add_node("generate", generate)

    workflow.set_entry_point("analyze_query")
    workflow.add_edge("analyze_query", "retrieve")
    workflow.add_edge("retrieve", "grade_documents")

    workflow.add_conditional_edges(
        "grade_documents",
        route_after_grading,
        {
            "generate": "generate",
            "transform_query": "transform_query",
            "web_search": "web_search",
        },
    )

    workflow.add_edge("transform_query", "retrieve")
    workflow.add_edge("web_search", "generate")
    workflow.add_edge("generate", END)

    return workflow.compile()


_graph = None


def get_graph():
    global _graph
    if _graph is None:
        _graph = build_graph()
    return _graph


def run_query(question: str) -> dict:
    graph = get_graph()
    initial_state: GraphState = {
        "question": question,
        "search_query": question,
        "query_type": "",
        "documents": [],
        "relevant_documents": [],
        "retries": 0,
        "answer": "",
        "used_web_search": False,
        "sources": [],
    }
    result = graph.invoke(initial_state)
    return result
