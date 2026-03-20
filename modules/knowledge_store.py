"""ChromaDB-backed Knowledge Store — unified vector database for all knowledge sources.

Replaces the FAISS-based RAG module with ChromaDB, providing:
- Persistent vector storage with metadata filtering
- Multiple collections: medical_guidelines, who_nih_datasets, pubmed_cache, patient_sessions
- Source-quality tagging for citation verification
- Cross-reference capability across collections
- Future chatbot support via session-scoped patient data collection

Architecture:
    ┌─────────────────────────────────────────────────────────┐
    │                    ChromaDB (Persistent)                │
    │                                                         │
    │  ┌──────────────────┐  ┌──────────────────┐            │
    │  │ medical_guidelines│  │  who_nih_data    │            │
    │  │ (23 MD files)     │  │ (official data)  │            │
    │  │ quality: curated  │  │ quality: official │            │
    │  └──────────────────┘  └──────────────────┘            │
    │                                                         │
    │  ┌──────────────────┐  ┌──────────────────┐            │
    │  │ pubmed_articles  │  │ patient_sessions │            │
    │  │ (live fetched)    │  │ (per-session)    │            │
    │  │ quality: reviewed │  │ quality: user    │            │
    │  └──────────────────┘  └──────────────────┘            │
    └─────────────────────────────────────────────────────────┘
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
CHROMADB_DIR = Path(__file__).resolve().parent.parent / "data" / "chromadb"
KNOWLEDGE_BASE_DIR = Path(__file__).resolve().parent.parent / "data" / "knowledge_base"
WHO_NIH_DIR = Path(__file__).resolve().parent.parent / "data" / "who_nih_datasets"
EMBEDDING_MODEL_ID = "sentence-transformers/all-MiniLM-L6-v2"

# Chunking parameters
CHUNK_SIZE_WORDS = 250          # Smaller chunks → more precise retrieval per query
CHUNK_OVERLAP_WORDS = 75         # Larger overlap → fewer boundary-split issues

# Retrieval parameters
DEFAULT_TOP_K = 8               # More candidates → better cross-reference & citation coverage
MAX_CONTEXT_CHARS = 6000         # Wider context window → fewer truncation-induced hallucinations

# Collection names
COLLECTION_GUIDELINES = "medical_guidelines"
COLLECTION_WHO_NIH = "who_nih_data"
COLLECTION_PUBMED = "pubmed_articles"
COLLECTION_PATIENT = "patient_sessions"

# Source quality tiers (for citation confidence scoring)
SOURCE_QUALITY = {
    "official": 1.0,     # WHO, NIH, government health agencies
    "peer_reviewed": 0.9, # PubMed articles (peer-reviewed journals)
    "curated": 0.7,      # Our knowledge base (AI-summarized guidelines)
    "user_data": 0.5,    # Patient-uploaded documents
}

# ---------------------------------------------------------------------------
# Lazy-loaded singletons
# ---------------------------------------------------------------------------
_chroma_client = None
_embedding_function = None


def _get_embedding_function():
    """Lazy-load ChromaDB-compatible embedding function with optimized caching."""
    global _embedding_function
    if _embedding_function is None:
        try:
            import os
            # Use locally cached model — skip HuggingFace online checks
            # This significantly speeds up model loading on subsequent requests
            os.environ.setdefault("HF_HUB_OFFLINE", "1")
            os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
            os.environ.setdefault("HF_HOME", os.path.expanduser("~/.cache/huggingface"))
            
            from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
            _embedding_function = SentenceTransformerEmbeddingFunction(
                model_name=EMBEDDING_MODEL_ID,
                device="cpu",  # Force CPU to avoid GPU initialization overhead
            )
            logger.info("ChromaDB embedding function loaded: %s", EMBEDDING_MODEL_ID)
        except ImportError:
            logger.error(
                "chromadb or sentence-transformers not installed. "
                "Run: pip install chromadb sentence-transformers"
            )
            raise
    return _embedding_function


def _get_client():
    """Lazy-load persistent ChromaDB client."""
    global _chroma_client
    if _chroma_client is None:
        import chromadb
        CHROMADB_DIR.mkdir(parents=True, exist_ok=True)
        _chroma_client = chromadb.PersistentClient(path=str(CHROMADB_DIR))
        logger.info("ChromaDB persistent client initialized at: %s", CHROMADB_DIR)
    return _chroma_client


def _get_collection(name: str):
    """Get or create a ChromaDB collection."""
    client = _get_client()
    ef = _get_embedding_function()
    return client.get_or_create_collection(
        name=name,
        embedding_function=ef,
        metadata={"hnsw:space": "cosine"},
    )


# ---------------------------------------------------------------------------
# Chunking (reused from FAISS module, adapted for ChromaDB)
# ---------------------------------------------------------------------------
def _chunk_by_sections(
    text: str,
    source_file: str,
    source_quality: str = "curated",
    source_org: str = "",
) -> list[dict[str, Any]]:
    """Chunk markdown text by ## headings. Returns dicts with text + metadata."""

    heading_pattern = r"(?=^## )"
    raw_sections = re.split(heading_pattern, text, flags=re.MULTILINE)

    doc_title = ""
    title_match = re.match(r"^#\s+(.+?)$", text, re.MULTILINE)
    if title_match:
        doc_title = title_match.group(1).strip()

    # Extract source reference section for citation metadata
    source_ref = ""
    ref_match = re.search(
        r"## Source Reference\s*\n(.*?)(?=\n## |\Z)", text, re.DOTALL
    )
    if ref_match:
        source_ref = ref_match.group(1).strip()[:500]

    chunks: list[dict[str, Any]] = []
    chunk_idx = 0

    for section in raw_sections:
        section = section.strip()
        if not section:
            continue

        section_heading = ""
        heading_match = re.match(r"^##\s+(.+?)$", section, re.MULTILINE)
        if heading_match:
            section_heading = heading_match.group(1).strip()

        words = section.split()
        if len(words) <= CHUNK_SIZE_WORDS:
            prefix = _build_metadata_prefix(doc_title, section_heading)
            chunks.append({
                "id": f"{source_file}::{chunk_idx}",
                "text": f"{prefix}\n{section}",
                "metadata": {
                    "source_file": source_file,
                    "source_quality": source_quality,
                    "source_org": source_org or doc_title,
                    "source_reference": source_ref,
                    "doc_title": doc_title,
                    "section": section_heading or doc_title,
                    "quality_score": SOURCE_QUALITY.get(source_quality, 0.5),
                },
            })
            chunk_idx += 1
        else:
            start = 0
            part = 1
            while start < len(words):
                end = min(len(words), start + CHUNK_SIZE_WORDS)
                chunk_text = " ".join(words[start:end])
                prefix = _build_metadata_prefix(
                    doc_title,
                    f"{section_heading} (part {part})" if section_heading else "",
                )
                chunks.append({
                    "id": f"{source_file}::{chunk_idx}",
                    "text": f"{prefix}\n{chunk_text}",
                    "metadata": {
                        "source_file": source_file,
                        "source_quality": source_quality,
                        "source_org": source_org or doc_title,
                        "source_reference": source_ref,
                        "doc_title": doc_title,
                        "section": (
                            f"{section_heading} (part {part})"
                            if section_heading
                            else doc_title
                        ),
                        "quality_score": SOURCE_QUALITY.get(source_quality, 0.5),
                    },
                })
                chunk_idx += 1
                if end >= len(words):
                    break
                start = max(0, end - CHUNK_OVERLAP_WORDS)
                part += 1

    return chunks


def _build_metadata_prefix(doc_title: str, section: str) -> str:
    parts = []
    if doc_title:
        parts.append(f"[Source: {doc_title}]")
    if section:
        parts.append(f"[Section: {section}]")
    return " ".join(parts)


# ---------------------------------------------------------------------------
# Index Building
# ---------------------------------------------------------------------------
def index_knowledge_base(force_rebuild: bool = False) -> int:
    """Index all .md files from data/knowledge_base/ into ChromaDB.

    Returns the total number of chunks indexed.
    """
    collection = _get_collection(COLLECTION_GUIDELINES)

    # Check if already populated
    if not force_rebuild and collection.count() > 0:
        logger.info(
            "Knowledge base collection already has %d chunks (use force_rebuild=True to re-index)",
            collection.count(),
        )
        return collection.count()

    # Clear existing data on rebuild
    if force_rebuild and collection.count() > 0:
        client = _get_client()
        client.delete_collection(COLLECTION_GUIDELINES)
        collection = _get_collection(COLLECTION_GUIDELINES)

    if not KNOWLEDGE_BASE_DIR.exists():
        logger.warning("Knowledge base directory not found: %s", KNOWLEDGE_BASE_DIR)
        return 0

    total = 0
    for md_file in sorted(KNOWLEDGE_BASE_DIR.glob("*.md")):
        try:
            text = md_file.read_text(encoding="utf-8")

            # Determine source quality based on filename
            quality = "curated"
            if any(
                kw in md_file.stem
                for kw in ["ada_", "kdigo_", "acc_aha_", "who_", "icmr"]
            ):
                quality = "curated"  # Still AI-summarized, but of authoritative sources

            chunks = _chunk_by_sections(text, md_file.name, source_quality=quality)
            if not chunks:
                continue

            # Batch add to ChromaDB
            collection.add(
                ids=[c["id"] for c in chunks],
                documents=[c["text"] for c in chunks],
                metadatas=[c["metadata"] for c in chunks],
            )
            total += len(chunks)
            logger.info("Indexed %d chunks from %s", len(chunks), md_file.name)

        except Exception as exc:
            logger.error("Failed to index %s: %s", md_file.name, exc)

    logger.info("Total knowledge base chunks indexed: %d", total)
    return total


def index_who_nih_data(force_rebuild: bool = False) -> int:
    """Index WHO/NIH datasets from data/who_nih_datasets/ into ChromaDB.

    These are official health datasets with higher source quality score.
    Returns the total number of chunks indexed.
    """
    collection = _get_collection(COLLECTION_WHO_NIH)

    if not force_rebuild and collection.count() > 0:
        logger.info(
            "WHO/NIH collection already has %d chunks", collection.count()
        )
        return collection.count()

    if force_rebuild and collection.count() > 0:
        client = _get_client()
        client.delete_collection(COLLECTION_WHO_NIH)
        collection = _get_collection(COLLECTION_WHO_NIH)

    if not WHO_NIH_DIR.exists():
        logger.warning("WHO/NIH directory not found: %s", WHO_NIH_DIR)
        return 0

    total = 0
    for md_file in sorted(WHO_NIH_DIR.glob("*.md")):
        try:
            text = md_file.read_text(encoding="utf-8")
            chunks = _chunk_by_sections(
                text,
                md_file.name,
                source_quality="official",
                source_org="WHO/NIH",
            )
            if not chunks:
                continue

            collection.add(
                ids=[c["id"] for c in chunks],
                documents=[c["text"] for c in chunks],
                metadatas=[c["metadata"] for c in chunks],
            )
            total += len(chunks)
            logger.info("Indexed %d WHO/NIH chunks from %s", len(chunks), md_file.name)

        except Exception as exc:
            logger.error("Failed to index WHO/NIH file %s: %s", md_file.name, exc)

    logger.info("Total WHO/NIH chunks indexed: %d", total)
    return total


def index_pubmed_article(
    pmid: str,
    title: str,
    abstract: str,
    journal: str = "",
    year: str = "",
) -> bool:
    """Index a single PubMed article abstract into ChromaDB.

    Called by web_retrieval module when fetching new articles.
    """
    collection = _get_collection(COLLECTION_PUBMED)

    doc_id = f"pubmed_{pmid}"

    # Check if already indexed
    try:
        existing = collection.get(ids=[doc_id])
        if existing and existing["ids"]:
            return False  # already exists
    except Exception:
        pass

    doc_text = f"[PubMed {year} — {journal}]\nTitle: {title}\n{abstract}"

    try:
        collection.add(
            ids=[doc_id],
            documents=[doc_text],
            metadatas=[{
                "source_file": f"pubmed_{pmid}",
                "source_quality": "peer_reviewed",
                "source_org": journal or "PubMed",
                "source_reference": f"PMID: {pmid}",
                "doc_title": title,
                "section": "abstract",
                "quality_score": SOURCE_QUALITY["peer_reviewed"],
                "pmid": pmid,
                "year": year,
            }],
        )
        return True
    except Exception as exc:
        logger.warning("Failed to index PubMed article %s: %s", pmid, exc)
        return False


def index_patient_session(
    session_id: str,
    data_type: str,
    content: str,
    metadata: dict[str, Any] | None = None,
) -> str:
    """Index patient session data for future chatbot retrieval.

    Parameters
    ----------
    session_id : str
        Patient session ID for isolation.
    data_type : str
        Type of data: "ocr_text", "structured_json", "diet_plan", "patient_profile"
    content : str
        The text content to index.
    metadata : dict | None
        Additional metadata.

    Returns
    -------
    str
        The document ID of the indexed chunk.
    """
    collection = _get_collection(COLLECTION_PATIENT)

    # Chunk large content
    words = content.split()
    chunks_to_add = []

    if len(words) <= 1000:
        doc_id = f"{session_id}::{data_type}::0"
        chunks_to_add.append({
            "id": doc_id,
            "text": content,
            "metadata": {
                "session_id": session_id,
                "data_type": data_type,
                "source_quality": "user_data",
                "quality_score": SOURCE_QUALITY["user_data"],
                **(metadata or {}),
            },
        })
    else:
        # Chunk into ~1000 char pieces
        start = 0
        idx = 0
        while start < len(words):
            end = min(len(words), start + 250)  # ~1000 chars
            chunk_text = " ".join(words[start:end])
            doc_id = f"{session_id}::{data_type}::{idx}"
            chunks_to_add.append({
                "id": doc_id,
                "text": chunk_text,
                "metadata": {
                    "session_id": session_id,
                    "data_type": data_type,
                    "source_quality": "user_data",
                    "quality_score": SOURCE_QUALITY["user_data"],
                    "chunk_index": idx,
                    **(metadata or {}),
                },
            })
            start = end
            idx += 1

    try:
        collection.add(
            ids=[c["id"] for c in chunks_to_add],
            documents=[c["text"] for c in chunks_to_add],
            metadatas=[c["metadata"] for c in chunks_to_add],
        )
        return chunks_to_add[0]["id"]
    except Exception as exc:
        logger.error("Failed to index patient data: %s", exc)
        return ""


# ---------------------------------------------------------------------------
# Retrieval
# ---------------------------------------------------------------------------
def retrieve_guidelines(
    query: str,
    top_k: int = DEFAULT_TOP_K,
    min_score: float = 0.25,
    collections: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Retrieve relevant chunks from one or more collections.

    Returns list of dicts with keys: text, metadata, score, collection.
    Results are sorted by quality-weighted score.
    """
    if collections is None:
        collections = [COLLECTION_GUIDELINES, COLLECTION_WHO_NIH, COLLECTION_PUBMED]

    all_results: list[dict[str, Any]] = []

    for coll_name in collections:
        try:
            collection = _get_collection(coll_name)
            if collection.count() == 0:
                continue

            results = collection.query(
                query_texts=[query],
                n_results=min(top_k, collection.count()),
                include=["documents", "metadatas", "distances"],
            )

            if not results or not results["ids"] or not results["ids"][0]:
                continue

            for i, doc_id in enumerate(results["ids"][0]):
                # ChromaDB returns distances (lower = closer for cosine)
                distance = results["distances"][0][i] if results["distances"] else 1.0
                # Convert distance to similarity score (cosine distance → similarity)
                similarity = 1.0 - distance

                if similarity < min_score:
                    continue

                meta = results["metadatas"][0][i] if results["metadatas"] else {}
                quality_score = meta.get("quality_score", 0.5)

                # Weighted score: similarity * quality_weight
                weighted_score = similarity * (0.7 + 0.3 * quality_score)

                all_results.append({
                    "text": results["documents"][0][i],
                    "metadata": meta,
                    "similarity": round(similarity, 4),
                    "quality_score": quality_score,
                    "weighted_score": round(weighted_score, 4),
                    "collection": coll_name,
                    "doc_id": doc_id,
                })

        except Exception as exc:
            logger.warning("Retrieval from %s failed: %s", coll_name, exc)

    # Sort by weighted score (highest first)
    all_results.sort(key=lambda x: x["weighted_score"], reverse=True)

    return all_results[:top_k]


def retrieve_for_patient(
    query: str,
    session_id: str,
    top_k: int = 5,
) -> list[dict[str, Any]]:
    """Retrieve from patient session data — scoped to a single session.

    For future chatbot use.
    """
    try:
        collection = _get_collection(COLLECTION_PATIENT)
    except ModuleNotFoundError as exc:
        logger.warning(
            "ChromaDB dependency unavailable during patient retrieval: %s", exc,
        )
        return []
    except Exception as exc:
        logger.warning("Patient collection initialization failed: %s", exc)
        return []

    if collection.count() == 0:
        return []

    try:
        results = collection.query(
            query_texts=[query],
            n_results=min(top_k, collection.count()),
            where={"session_id": session_id},
            include=["documents", "metadatas", "distances"],
        )

        if not results or not results["ids"] or not results["ids"][0]:
            return []

        items = []
        for i, doc_id in enumerate(results["ids"][0]):
            distance = results["distances"][0][i] if results["distances"] else 1.0
            similarity = 1.0 - distance
            items.append({
                "text": results["documents"][0][i],
                "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                "similarity": round(similarity, 4),
                "doc_id": doc_id,
            })

        return items

    except Exception as exc:
        logger.warning("Patient session retrieval failed: %s", exc)
        return []


    def retrieve_for_patient_with_fallback(
        query: str,
        session_id: str,
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        """Retrieve from patient session data with fallback to general guidelines.

        Strategy:
        1. Try to retrieve from patient-scoped collection (session_id filter)
        2. If empty or fails, retrieve from all patient sessions (unfiltered)
        3. If still empty, fallback to general medical guidelines

        This ensures the chatbot always has SOME context to work with.
        """
        collection = _get_collection(COLLECTION_PATIENT)

        # Attempt 1: Session-scoped retrieval with where filter
        if collection.count() > 0:
            try:
                results = collection.query(
                    query_texts=[query],
                    n_results=min(top_k, collection.count()),
                    where={"session_id": session_id},
                    include=["documents", "metadatas", "distances"],
                )

                if results and results["ids"] and results["ids"][0]:
                    items = []
                    for i, doc_id in enumerate(results["ids"][0]):
                        distance = results["distances"][0][i] if results["distances"] else 1.0
                        similarity = 1.0 - distance
                        items.append({
                            "text": results["documents"][0][i],
                            "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                            "similarity": round(similarity, 4),
                            "doc_id": doc_id,
                        })
                    logger.info(
                        "Patient retrieval (session-scoped): %d chunks found for %s",
                        len(items), session_id[:8],
                    )
                    return items

            except Exception as exc:
                logger.debug("Session-scoped where filter failed: %s (trying unfiltered)", exc)

            # Attempt 2: Retrieve from all patient sessions (unfiltered)
            try:
                results = collection.query(
                    query_texts=[query],
                    n_results=min(top_k * 2, collection.count()),
                    include=["documents", "metadatas", "distances"],
                )

                if results and results["ids"] and results["ids"][0]:
                    items = []
                    for i, doc_id in enumerate(results["ids"][0]):
                        distance = results["distances"][0][i] if results["distances"] else 1.0
                        similarity = 1.0 - distance
                        # Prioritize this session's data
                        metadata = results["metadatas"][0][i] if results["metadatas"] else {}
                        if metadata.get("session_id") == session_id:
                            similarity = min(1.0, similarity + 0.1)  # Slight boost for matching session
                        items.append({
                            "text": results["documents"][0][i],
                            "metadata": metadata,
                            "similarity": round(similarity, 4),
                            "doc_id": doc_id,
                        })
                    items.sort(key=lambda x: x["similarity"], reverse=True)
                    items = items[:top_k]
                    logger.info(
                        "Patient retrieval (unfiltered): %d chunks found for %s",
                        len(items), session_id[:8],
                    )
                    return items

            except Exception as exc:
                logger.debug("Unfiltered patient retrieval failed: %s", exc)

        # Attempt 3: Fallback to general medical guidelines
        logger.info("No patient data found for %s, falling back to medical guidelines", session_id[:8])
        return retrieve_guidelines(
            query=query,
            top_k=top_k,
            collections=[COLLECTION_GUIDELINES, COLLECTION_WHO_NIH],
        )


# ---------------------------------------------------------------------------
# Pre-generation chunk validation (runs BEFORE context reaches LLM)
# ---------------------------------------------------------------------------

# Minimum thresholds for chunk inclusion
_MIN_WEIGHTED_SCORE = 0.35       # Drop chunks below this relevance
_MIN_QUALITY_SCORE = 0.4         # Drop chunks below this quality tier
_CROSS_REF_BONUS = 0.10          # Score boost for cross-verified claims

# Known authoritative sources — chunks citing these get priority
_KNOWN_ORGS = {
    "who", "nih", "ada", "aha", "acc", "kdigo", "aasld", "nice",
    "icmr", "fssai", "dash", "usda", "niddk", "rda", "dri",
    "espen", "aace", "esc",
}


def _validate_and_filter_chunks(
    chunks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Validate and filter retrieved chunks before they reach the LLM.

    This is the pre-generation quality gate:
    1. Drops chunks below minimum relevance/quality thresholds
    2. Cross-references overlapping claims — boosts score when 2+ sources agree
    3. Tags each chunk with verified source orgs for the LLM to cite accurately
    4. Re-sorts by validated score

    Returns filtered, re-scored chunks (only high-confidence ones).
    """
    if not chunks:
        return []

    # Step 1: Filter by minimum thresholds
    filtered: list[dict[str, Any]] = []
    for chunk in chunks:
        ws = chunk.get("weighted_score", 0)
        qs = chunk.get("quality_score", 0)
        if ws >= _MIN_WEIGHTED_SCORE and qs >= _MIN_QUALITY_SCORE:
            filtered.append(chunk)
        else:
            meta = chunk.get("metadata", {})
            logger.debug(
                "Chunk filtered out (score=%.3f, quality=%.2f): %s",
                ws, qs, meta.get("section", "unknown"),
            )

    if not filtered:
        # Fall back to top chunks if all got filtered (rare but possible)
        logger.warning("All chunks filtered — falling back to top %d by score", min(3, len(chunks)))
        filtered = sorted(chunks, key=lambda c: c.get("weighted_score", 0), reverse=True)[:3]

    # Step 2: Cross-reference — find overlapping topics across different sources
    # Group chunks by broad topic (section heading) to detect agreement
    topic_sources: dict[str, list[int]] = {}
    for i, chunk in enumerate(filtered):
        meta = chunk.get("metadata", {})
        section = meta.get("section", "").lower()
        # Normalise section names to detect cross-source agreement
        for keyword in ["sodium", "protein", "fiber", "potassium", "sugar",
                         "calori", "fat", "cholesterol", "iron", "vitamin",
                         "calcium", "carbohydrate"]:
            if keyword in section or keyword in chunk.get("text", "").lower()[:200]:
                topic_key = keyword
                topic_sources.setdefault(topic_key, []).append(i)

    # Boost chunks that are corroborated by another source
    cross_verified_indices: set[int] = set()
    for topic, indices in topic_sources.items():
        if len(indices) < 2:
            continue
        # Check they come from different source files
        sources = {filtered[i].get("metadata", {}).get("source_file", "") for i in indices}
        if len(sources) >= 2:
            cross_verified_indices.update(indices)
            logger.debug("Cross-verified topic '%s' from %d sources", topic, len(sources))

    for i in cross_verified_indices:
        old = filtered[i].get("weighted_score", 0)
        filtered[i]["weighted_score"] = round(old + _CROSS_REF_BONUS, 4)
        filtered[i].setdefault("cross_verified", True)

    # Step 3: Tag source orgs so LLM knows which guidelines it can cite
    for chunk in filtered:
        meta = chunk.get("metadata", {})
        text_lower = chunk.get("text", "").lower()
        org_tag = meta.get("source_org", "").lower()

        verified_orgs: list[str] = []
        for org in _KNOWN_ORGS:
            if org in org_tag or org in text_lower:
                verified_orgs.append(org.upper())
        if verified_orgs:
            chunk["verified_source_orgs"] = verified_orgs

    # Step 4: Re-sort by validated score
    filtered.sort(key=lambda c: c.get("weighted_score", 0), reverse=True)

    logger.info(
        "Chunk validation: %d/%d passed, %d cross-verified",
        len(filtered), len(chunks), len(cross_verified_indices),
    )

    return filtered


# ---------------------------------------------------------------------------
# Build structured RAG context (replaces old rag.py retrieve_context)
# ---------------------------------------------------------------------------
def _build_query_from_health_state(
    aggregated_state: dict,
    per_doc_results: list[dict] | None = None,
) -> str:
    """Build a semantic query from the patient's health state."""
    parts: list[str] = []

    abnormals = aggregated_state.get("aggregated_abnormal_findings", [])
    if abnormals:
        finding_strs = []
        for f in abnormals[:10]:
            key = f.get("canonical_test_key", "")
            severity = f.get("severity", "")
            finding_strs.append(f"{key} ({severity})")
        parts.append("Abnormal lab findings: " + ", ".join(finding_strs))

    chronic = aggregated_state.get("chronic_flags", [])
    if chronic:
        chronic_strs = [
            f.get("test_name", f.get("test_key", "")) for f in chronic[:5]
        ]
        parts.append("Chronic conditions: " + ", ".join(chronic_strs))

    bmi = aggregated_state.get("bmi")
    if bmi:
        cat = bmi.get("category", "")
        val = bmi.get("bmi_value", "")
        if cat:
            parts.append(f"BMI: {val} ({cat})")

    patient = aggregated_state.get("patient_information", {})
    age = patient.get("age_years")
    if age is not None:
        if age >= 65:
            parts.append("Elderly patient (age ≥ 65)")
        elif age < 18:
            parts.append("Pediatric patient (age < 18)")

    if per_doc_results:
        meds: list[str] = []
        for doc in per_doc_results:
            if doc.get("doc_type") != "prescription":
                continue
            notes = doc.get("clinical_notes", {})
            for section in ["recommendations", "comments", "notes"]:
                entries = notes.get(section, [])
                meds.extend(entries[:5])
        if meds:
            parts.append("Medications: " + ", ".join(meds[:8]))

    tests = aggregated_state.get("aggregated_tests", {})
    categories_seen: set[str] = set()
    for _key, test in tests.items():
        cat = test.get("category", "")
        interp = test.get("current_interpretation", "")
        if interp and interp.lower() not in ("normal", "within_range", ""):
            categories_seen.add(cat)

    if categories_seen:
        cat_map = {
            "glucose_metabolism": "diabetes blood glucose HbA1c",
            "lipid_panel": "cholesterol triglycerides LDL HDL cardiovascular",
            "renal_function": "kidney creatinine BUN eGFR CKD",
            "liver_function": "liver ALT AST bilirubin NAFLD",
            "thyroid_panel": "thyroid TSH T3 T4 hypothyroidism",
            "hematology": "anemia hemoglobin iron B12 CBC",
            "electrolytes": "sodium potassium calcium magnesium electrolyte",
            "iron_studies": "iron ferritin anemia iron deficiency",
            "vitamins": "vitamin D B12 folate deficiency",
        }
        expanded = []
        for cat in categories_seen:
            expanded.append(cat_map.get(cat, cat))
        parts.append("Relevant categories: " + ", ".join(expanded))

    if not parts:
        return "general balanced diet nutrition guidelines"

    return " | ".join(parts)


def retrieve_context(
    aggregated_state: dict,
    per_doc_results: list[dict] | None = None,
    top_k: int = DEFAULT_TOP_K,
) -> tuple[str, list[dict[str, Any]]]:
    """Retrieve relevant medical nutrition guidelines for the patient.

    Returns
    -------
    tuple[str, list[dict]]
        (formatted_context_string, raw_retrieved_chunks_with_metadata)
        The raw chunks are needed for citation verification and cross-referencing.
    """
    # Ensure collections are populated
    try:
        guidelines_coll = _get_collection(COLLECTION_GUIDELINES)
        if guidelines_coll.count() == 0:
            logger.info("Knowledge base not indexed yet, building...")
            index_knowledge_base()
    except Exception as exc:
        logger.warning("Failed to check/build index: %s", exc)

    query = _build_query_from_health_state(aggregated_state, per_doc_results)
    logger.info("ChromaDB RAG query: %s", query[:200])

    results = retrieve_guidelines(query, top_k=top_k)

    if not results:
        logger.info("ChromaDB retrieval returned no relevant chunks")
        return "", []

    # Pre-generation validation: filter, cross-reference, and tag chunks
    results = _validate_and_filter_chunks(results)

    # Format context string
    seen_sections: set[str] = set()
    formatted_parts: list[str] = []
    total_chars = 0

    for r in results:
        meta = r["metadata"]
        section_key = f"{meta.get('source_file', '')}::{meta.get('section', '')}"

        if section_key in seen_sections:
            continue
        seen_sections.add(section_key)

        text = r["text"]
        quality = meta.get("source_quality", "unknown")
        quality_label = {
            "official": "⬛ OFFICIAL",
            "peer_reviewed": "🔬 PEER-REVIEWED",
            "curated": "📋 CURATED",
        }.get(quality, "📄 REFERENCE")

        # Add cross-verification and source org tags for LLM awareness
        tags = []
        if r.get("cross_verified"):
            tags.append("✅ CROSS-VERIFIED")
        verified_orgs = r.get("verified_source_orgs", [])
        if verified_orgs:
            tags.append(f"Source: {', '.join(verified_orgs)}")
        tag_str = f" | {' | '.join(tags)}" if tags else ""

        entry = f"[{quality_label} | Score: {r['weighted_score']}{tag_str}]\n{text}"

        if total_chars + len(entry) > MAX_CONTEXT_CHARS:
            remaining = MAX_CONTEXT_CHARS - total_chars
            if remaining > 100:
                entry = entry[:remaining] + "..."
                formatted_parts.append(entry)
            break

        formatted_parts.append(entry)
        total_chars += len(entry)

    context = "\n\n---\n\n".join(formatted_parts)
    logger.info(
        "ChromaDB retrieved %d chunks (%d chars) for diet prompt",
        len(formatted_parts),
        len(context),
    )

    return context, results


# ---------------------------------------------------------------------------
# Management utilities
# ---------------------------------------------------------------------------
def rebuild_all(force: bool = True) -> dict[str, int]:
    """Rebuild all knowledge indexes."""
    counts = {}
    counts["medical_guidelines"] = index_knowledge_base(force_rebuild=force)
    counts["who_nih"] = index_who_nih_data(force_rebuild=force)
    return counts


def get_all_stats() -> dict[str, Any]:
    """Return stats about all ChromaDB collections."""
    stats = {}
    for coll_name in [
        COLLECTION_GUIDELINES,
        COLLECTION_WHO_NIH,
        COLLECTION_PUBMED,
        COLLECTION_PATIENT,
    ]:
        try:
            coll = _get_collection(coll_name)
            count = coll.count()

            # Get source files if any
            sources = set()
            if count > 0:
                sample = coll.peek(min(count, 50))
                for meta in (sample.get("metadatas") or []):
                    if meta:
                        sources.add(meta.get("source_file", "unknown"))

            stats[coll_name] = {
                "chunks": count,
                "source_files": sorted(sources),
            }
        except Exception:
            stats[coll_name] = {"chunks": 0, "source_files": []}

    stats["embedding_model"] = EMBEDDING_MODEL_ID
    stats["storage_path"] = str(CHROMADB_DIR)

    return stats
