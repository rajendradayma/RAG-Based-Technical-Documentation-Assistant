# ChromaDB Basics

Chroma is an open-source embedding database designed to make it easy to build LLM apps by making knowledge, facts, and skills pluggable.

## Creating a Client

```python
import chromadb

client = chromadb.PersistentClient(path="./chroma_db")
```

A `PersistentClient` stores data on disk so it persists across sessions. An `EphemeralClient` keeps data only in memory.

## Creating a Collection

```python
collection = client.get_or_create_collection(name="docs")
```

A collection is the basic unit of storage in Chroma. Each collection has a name and stores embeddings, documents, and metadata.

## Adding Documents

```python
collection.add(
    documents=["This is a document about FastAPI", "This is a document about Pydantic"],
    metadatas=[{"source": "fastapi.md"}, {"source": "pydantic.md"}],
    ids=["doc1", "doc2"]
)
```

If no embedding function is specified, Chroma uses a default sentence-transformers model to compute embeddings automatically. You can also provide your own embeddings or embedding function.

## Querying

```python
results = collection.query(
    query_texts=["How do I create a FastAPI app?"],
    n_results=3
)
```

The results contain the most similar documents, their metadata, distances, and ids. Lower distance generally indicates higher similarity for common distance metrics like cosine distance.

## Custom Embedding Functions

You can use custom embedding functions, including sentence-transformers models:

```python
from chromadb.utils import embedding_functions

sentence_transformer_ef = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="all-MiniLM-L6-v2"
)

collection = client.get_or_create_collection(
    name="docs",
    embedding_function=sentence_transformer_ef
)
```

## Filtering with Metadata

Queries can be filtered using the `where` parameter to restrict results to documents matching certain metadata:

```python
results = collection.query(
    query_texts=["error handling"],
    n_results=3,
    where={"source": "fastapi.md"}
)
```

## Updating and Deleting

```python
collection.update(ids=["doc1"], documents=["Updated content"])
collection.delete(ids=["doc1"])
```

## Persistence

When using a `PersistentClient`, all data is automatically saved to disk at the specified path, and will be available again the next time a client is created with that path.
