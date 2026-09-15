"""
tools/chroma_store.py
──────────────────────
ChromaDB wrapper for all agents.
Provides a simple interface for upserting and retrieving context embeddings.
All agents share one ChromaDB instance stored locally at settings.chroma_path.
"""

import logging
import chromadb
from chromadb.config import Settings as ChromaSettings
from config.settings import settings
from modules.common.logger import platform_logger
logger = platform_logger

# ── Singleton client ───────────────────────────────────────────────────────────
_client: chromadb.ClientAPI | None = None


def _get_client() -> chromadb.ClientAPI:
    global _client
    if _client is None:
        if settings.chroma_api_key:
            db_name = settings.chroma_database or "LIST ASSISTANT"
            _client = chromadb.CloudClient(
                api_key=settings.chroma_api_key,
                tenant=settings.chroma_tenant or None,
                database=db_name,
                settings=ChromaSettings(anonymized_telemetry=False),
            )
            logger.info(f"ChromaDB initialised with Chroma Cloud Client (Database: '{db_name}')")
        else:
            path = str(settings.chroma_path)
            settings.chroma_path.mkdir(parents=True, exist_ok=True)
            _client = chromadb.PersistentClient(
                path=path,
                settings=ChromaSettings(anonymized_telemetry=False),
            )
            logger.info(f"ChromaDB initialised at local path: {path}")
    return _client


def _get_collection(name: str) -> chromadb.Collection:
    """
    Returns (or creates) a named collection.
    Each pipeline run uses a collection named after the project/app.
    """
    client = _get_client()
    return client.get_or_create_collection(
        name=name,
        metadata={"hnsw:space": "cosine"},
    )


# ── Public API ─────────────────────────────────────────────────────────────────

def upsert_context(collection_name: str, key: str, text: str, metadata: dict | None = None) -> None:
    """
    Store a piece of text context in ChromaDB.

    Args:
        collection_name: Project-scoped collection name (e.g. "my_todo_app").
        key: Unique document ID (e.g. "structured_spec", "api_contracts").
        text: The text content to embed and store.
        metadata: Optional dict of extra metadata tags.
    """
    collection = _get_collection(collection_name)
    collection.upsert(
        ids=[key],
        documents=[text],
        metadatas=[metadata or {"key": key}],
    )
    logger.vector_db(f"Embedding Stored | Upserted '{key}' into collection '{collection_name}'", details=f"key={key}, collection={collection_name}")


def retrieve_context(collection_name: str, query: str, k: int = 5) -> list[dict]:
    """
    Retrieve the top-k most relevant context chunks for a query.

    Args:
        collection_name: Project-scoped collection name.
        query: The query string to embed and search against.
        k: Number of results to return.

    Returns:
        List of dicts with keys: 'id', 'document', 'metadata', 'distance'
    """
    try:
        collection = _get_collection(collection_name)
        results = collection.query(query_texts=[query], n_results=min(k, collection.count()))
        logger.vector_db(f"Similarity Search | Queried '{query[:40]}...' in '{collection_name}'", details=f"collection={collection_name}, count={len(results.get('ids', [[]])[0]) if results else 0}")
        items = []
        if results and results.get("ids"):
            for i, doc_id in enumerate(results["ids"][0]):
                items.append({
                    "id": doc_id,
                    "document": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i],
                    "distance": results["distances"][0][i] if results.get("distances") else None,
                })
        return items
    except Exception as exc:
        logger.warning(f"[ChromaDB] Retrieval failed for query '{query[:60]}...': {exc}")
        return []


def delete_collection(collection_name: str) -> None:
    """Remove a project's entire collection (e.g. on pipeline reset)."""
    try:
        _get_client().delete_collection(collection_name)
        logger.vector_db(f"Deleted collection '{collection_name}'", details=f"collection={collection_name}")
    except Exception as exc:
        logger.warning(f"Could not delete collection '{collection_name}': {exc}")
