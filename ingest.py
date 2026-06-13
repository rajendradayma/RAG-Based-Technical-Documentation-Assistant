"""
Document ingestion pipeline.
Loads markdown documents from the corpus directory, splits them into chunks,
generates embeddings, and stores them in a persistent ChromaDB collection.
"""

import os
import glob
import chromadb
from chromadb.utils import embedding_functions
from langchain_text_splitters import RecursiveCharacterTextSplitter

CORPUS_DIR = "corpus"
CHROMA_PATH = "chroma_db"
COLLECTION_NAME = "tech_docs"

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
    ids = []
    for doc in docs:
        pieces = SPLITTER.split_text(doc["text"])
        for i, piece in enumerate(pieces):
            chunks.append(piece)
            metadatas.append({"source": doc["source"], "chunk_index": i})
            ids.append(f"{doc['source']}::chunk_{i}")
    return chunks, metadatas, ids


def get_embedding_fn():
    return embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="all-MiniLM-L6-v2"
    )


def get_collection(chroma_path: str = CHROMA_PATH):
    client = chromadb.PersistentClient(path=chroma_path)
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=get_embedding_fn(),
    )


def build_index(corpus_dir: str = CORPUS_DIR, chroma_path: str = CHROMA_PATH, reset: bool = True):
    """Run the full ingestion pipeline and return the Chroma collection."""
    client = chromadb.PersistentClient(path=chroma_path)

    if reset:
        try:
            client.delete_collection(COLLECTION_NAME)
        except Exception:
            pass

    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=get_embedding_fn(),
    )

    docs = load_documents(corpus_dir)
    if not docs:
        print(f"No .md files found in {corpus_dir}")
        return collection

    chunks, metadatas, ids = chunk_documents(docs)

    # Chroma add() has a practical batch limit; batch in groups of 100.
    batch_size = 100
    for i in range(0, len(chunks), batch_size):
        collection.add(
            documents=chunks[i:i + batch_size],
            metadatas=metadatas[i:i + batch_size],
            ids=ids[i:i + batch_size],
        )

    print(f"Ingested {len(docs)} documents -> {len(chunks)} chunks into '{COLLECTION_NAME}'")
    return collection


def add_text_document(source_name: str, text: str, chroma_path: str = CHROMA_PATH):
    """Ingest a single new document (used by the /ingest API endpoint)."""
    client = chromadb.PersistentClient(path=chroma_path)
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=get_embedding_fn(),
    )

    pieces = SPLITTER.split_text(text)
    chunks, metadatas, ids = [], [], []
    for i, piece in enumerate(pieces):
        chunks.append(piece)
        metadatas.append({"source": source_name, "chunk_index": i})
        ids.append(f"{source_name}::chunk_{i}")

    if chunks:
        collection.add(documents=chunks, metadatas=metadatas, ids=ids)

    return len(chunks)


def get_documents_summary(chroma_path: str = CHROMA_PATH):
    """Return a summary of indexed documents grouped by source, for GET /documents."""
    client = chromadb.PersistentClient(path=chroma_path)
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=get_embedding_fn(),
    )

    total = collection.count()
    if total == 0:
        return {"total_chunks": 0, "sources": []}

    all_data = collection.get(include=["metadatas"])
    counts = {}
    for meta in all_data.get("metadatas", []):
        source = meta.get("source", "unknown")
        counts[source] = counts.get(source, 0) + 1

    sources = [{"source": s, "chunks": c} for s, c in sorted(counts.items())]
    return {"total_chunks": total, "sources": sources}


if __name__ == "__main__":
    build_index()
