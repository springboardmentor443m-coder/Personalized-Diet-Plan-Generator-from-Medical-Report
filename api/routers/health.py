"""
Health Router — liveness / readiness probe + Knowledge Store + Web retrieval status.
"""

from fastapi import APIRouter
from schemas.models import HealthCheckResponse

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthCheckResponse)
async def health():
    return HealthCheckResponse()


# ---------------------------------------------------------------------------
# Legacy RAG endpoints (FAISS-based — kept for backward compatibility)
# ---------------------------------------------------------------------------
@router.get("/rag/status")
async def rag_status():
    """Return RAG index statistics."""
    try:
        from modules.rag import get_index_stats
        return get_index_stats()
    except Exception as exc:
        return {"status": "error", "detail": str(exc)}


@router.post("/rag/rebuild")
async def rag_rebuild():
    """Force-rebuild the RAG index from the knowledge base."""
    try:
        from modules.rag import rebuild_index
        count = rebuild_index()
        return {"status": "rebuilt", "chunks_indexed": count}
    except Exception as exc:
        return {"status": "error", "detail": str(exc)}


# ---------------------------------------------------------------------------
# ChromaDB Knowledge Store endpoints
# ---------------------------------------------------------------------------
@router.get("/knowledge-store/status")
async def knowledge_store_status():
    """Return ChromaDB knowledge store statistics (all collections)."""
    try:
        from modules.knowledge_store import get_all_stats
        return get_all_stats()
    except Exception as exc:
        return {"status": "error", "detail": str(exc)}


@router.post("/knowledge-store/rebuild")
async def knowledge_store_rebuild():
    """Force-rebuild all ChromaDB knowledge indexes."""
    try:
        from modules.knowledge_store import rebuild_all
        counts = rebuild_all(force=True)
        return {"status": "rebuilt", "collections": counts}
    except Exception as exc:
        return {"status": "error", "detail": str(exc)}


@router.post("/knowledge-store/index-who-nih")
async def knowledge_store_index_who_nih():
    """Index WHO/NIH datasets into ChromaDB."""
    try:
        from modules.knowledge_store import index_who_nih_data
        count = index_who_nih_data(force_rebuild=True)
        return {"status": "indexed", "chunks": count}
    except Exception as exc:
        return {"status": "error", "detail": str(exc)}


# ---------------------------------------------------------------------------
# Web Retrieval endpoints
# ---------------------------------------------------------------------------
@router.get("/web-retrieval/cache-stats")
async def web_cache_stats():
    """Return web retrieval cache statistics."""
    try:
        from modules.web_retrieval import get_web_cache_stats
        return get_web_cache_stats()
    except Exception as exc:
        return {"status": "error", "detail": str(exc)}


@router.post("/web-retrieval/clear-cache")
async def web_clear_cache():
    """Clear all cached web retrieval results."""
    try:
        from modules.web_retrieval import clear_web_cache
        count = clear_web_cache()
        return {"status": "cleared", "files_removed": count}
    except Exception as exc:
        return {"status": "error", "detail": str(exc)}
