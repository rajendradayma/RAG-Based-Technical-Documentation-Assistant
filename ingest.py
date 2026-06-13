"""
Document ingestion pipeline.
Loads markdown documents from the corpus directory, splits them into chunks,
generates embeddings, and stores them in a local FAISS index.
"""

import os
import glob
import pickle

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
from langchain_text_splitters import RecursiveCharacterTextSplitter

CORPUS_DIR = "corpus"
INDEX_DIR = "faiss_index"
INDEX_FILE = os.path.join(INDEX_DIR, "index.faiss")
META_FILE = os.path.join(INDEX_DIR, "meta.pkl")

EMBED_MODEL_NAME = "all-MiniLM-L6-v2"

# Chunking strategy:
# - chunk_size=800, chunk_overlap=120
# - Technical docs mix prose explanations with code blocks. We use
#   RecursiveCharacterTextSplitter with separators ordered so it prefers
#   splitting on markdown headings ("\n## "), then paragraph breaks,
#   then code fences, before falling back to sentence/word splits.
# - 800 chars (~150-200 tokens) keeps a chunk small enough to be focused
#   on one concept/code-example pair, while 120-char overlap preserves
#   continuity when a code block is split across chunks.
SPLITTER = RecursiveCharacterTextSplitter(
    chunk_size=800,
    chunk_overlap=120,
    separators=["\n## ", "\n### ", "\n\n", "\n```", "\n", " ", ""],
)

_embedder = None


def get_embedder():
    global _embedder
    if _embedder is None:
        _embedder = SentenceTransformer(EMBED_MODEL_NAME)
    return _embedder


def embed_texts(texts):
    embedder = get_embedder()
    vectors = embedder.encode(texts, convert_to_numpy=True, normalize_embeddings=True)
    return vectors.astype("float32")


def load_documents(corpus_dir: str = CORPUS_DIR):
    """Load all markdown files from the corpus directory."""
    docs = []
    for path in glob.glob(os.path.join(corpus_dir, "*.md")):
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
        docs.append({"source": os.path.basename(path), "text": text})
    return docs


def chunk_documents(docs):
    """Split each document into overlapping chunks, tagging with source + chunk index."""
    chunks = []
    metadatas = []
    for doc in docs:
        pieces = SPLITTER.split_text(doc["text"])
        for i, piece in enumerate(pieces):
            chunks.append(piece)
            metadatas.append({"source": doc["source"], "chunk_index": i})
    return chunks, metadatas


def _save_index(index, texts, metadatas):
    os.makedirs(INDEX_DIR, exist_ok=True)
    faiss.write_index(index, INDEX_FILE)
    with open(META_FILE, "wb") as f:
        pickle.dump({"texts": texts, "metadatas": metadatas}, f)


def _load_index():
    if not (os.path.exists(INDEX_FILE) and os.path.exists(META_FILE)):
        return None, [], []
    index = faiss.read_index(INDEX_FILE)
    with open(META_FILE, "rb") as f:
        data = pickle.load(f)
    return index, data["texts"], data["metadatas"]


def build_index(corpus_dir: str = CORPUS_DIR, reset: bool = True):
    """Run the full ingestion pipeline and persist the FAISS index + metadata."""
    if reset and os.path.exists(INDEX_DIR):
        for f in (INDEX_FILE, META_FILE):
            if os.path.exists(f):
                os.remove(f)

    docs = load_documents(corpus_dir)
    if not docs:
        print(f"No .md files found in {corpus_dir}")
        return

    chunks, metadatas = chunk_documents(docs)
    vectors = embed_texts(chunks)

    dim = vectors.shape[1]
    index = faiss.IndexFlatIP(dim)  # cosine similarity via normalized vectors + inner product
    index.add(vectors)

    _save_index(index, chunks, metadatas)
    print(f"Ingested {len(docs)} documents -> {len(chunks)} chunks into FAISS index")


def add_text_document(source_name: str, text: str):
    """Ingest a single new document (used by the /ingest API endpoint)."""
    index, texts, metadatas = _load_index()

    pieces = SPLITTER.split_text(text)
    if not pieces:
        return 0

    new_vectors = embed_texts(pieces)

    if index is None:
        dim = new_vectors.shape[1]
        index = faiss.IndexFlatIP(dim)

    index.add(new_vectors)

    for i, piece in enumerate(pieces):
        texts.append(piece)
        metadatas.append({"source": source_name, "chunk_index": i})

    _save_index(index, texts, metadatas)
    return len(pieces)


def query_index(query_text: str, top_k: int = 4):
    """Return top_k chunks as list of dicts: {text, source, chunk_index}."""
    index, texts, metadatas = _load_index()
    if index is None or index.ntotal == 0:
        return []

    query_vector = embed_texts([query_text])
    k = min(top_k, index.ntotal)
    scores, indices = index.search(query_vector, k)

    results = []
    for idx in indices[0]:
        if idx == -1:
            continue
        results.append({
            "text": texts[idx],
            "source": metadatas[idx]["source"],
            "chunk_index": metadatas[idx]["chunk_index"],
        })
    return results


def get_documents_summary():
    """Return a summary of indexed documents grouped by source, for GET /documents."""
    index, texts, metadatas = _load_index()
    if index is None or index.ntotal == 0:
        return {"total_chunks": 0, "sources": []}

    counts = {}
    for meta in metadatas:
        source = meta.get("source", "unknown")
        counts[source] = counts.get(source, 0) + 1

    sources = [{"source": s, "chunks": c} for s, c in sorted(counts.items())]
    return {"total_chunks": index.ntotal, "sources": sources}


def get_collection():
    """Compatibility shim so callers can check whether an index exists."""
    index, _, _ = _load_index()

    class _CollectionStub:
        def __init__(self, n):
            self._n = n

        def count(self):
            return self._n

    return _CollectionStub(index.ntotal if index is not None else 0)


if __name__ == "__main__":
    build_index()
