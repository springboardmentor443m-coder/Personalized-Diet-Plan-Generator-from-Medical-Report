"""RAG (Retrieval-Augmented Generation) module for evidence-based diet planning.

Uses FAISS for vector search and sentence-transformers for embeddings,
following the same proven pattern from talk_with_pdf.

The knowledge base consists of medical nutrition therapy guidelines that
ground the LLM's diet recommendations in clinical evidence.
"""

from __future__ import annotations

import logging
import os
import pickle
import re
from pathlib import Path
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
EMBEDDING_MODEL_ID = "sentence-transformers/all-MiniLM-L6-v2"
KNOWLEDGE_BASE_DIR = Path(__file__).resolve().parent.parent / "data" / "knowledge_base"
FAISS_INDEX_DIR = Path(__file__).resolve().parent.parent / "data" / "faiss_index"

# Chunking parameters
CHUNK_SIZE_WORDS = 300        # smaller chunks = more precise retrieval
CHUNK_OVERLAP_WORDS = 60      # overlap prevents cutting context
DEFAULT_TOP_K = 6             # number of chunks to retrieve
MAX_CONTEXT_CHARS = 4000      # hard cap on RAG context length in prompt

# ---------------------------------------------------------------------------
# Lazy-loaded singletons
# ---------------------------------------------------------------------------
_embedder = None
_index_pack: dict[str, Any] | None = None


def _get_embedder():
    """Lazy-load the sentence-transformer embedding model (singleton) with optimized caching."""
    global _embedder
    if _embedder is None:
        try:
            import os
            # Use locally cached model — skip HuggingFace online checks
            # This significantly speeds up model loading on subsequent requests
            os.environ.setdefault("HF_HUB_OFFLINE", "1")
            os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
            os.environ.setdefault("HF_HOME", os.path.expanduser("~/.cache/huggingface"))
            
            from sentence_transformers import SentenceTransformer
            logger.info("Loading embedding model: %s", EMBEDDING_MODEL_ID)
            # Force CPU to avoid GPU initialization overhead
            _embedder = SentenceTransformer(EMBEDDING_MODEL_ID, device="cpu")
            logger.info("Embedding model loaded successfully")
        except ImportError:
            logger.error(
                "sentence-transformers not installed. "
                "Run: pip install sentence-transformers"
            )
            raise
    return _embedder


# ---------------------------------------------------------------------------
# Chunking
# ---------------------------------------------------------------------------
def _chunk_by_sections(text: str, source_file: str) -> list[dict[str, str]]:
    """Chunk markdown text by sections (## headings) with word-level overlap.

    Each chunk carries metadata about its source file and section heading
    for better retrieval context.
    """
    # Split on markdown ## headings (keep the heading with its section)
    heading_pattern = r"(?=^## )"
    raw_sections = re.split(heading_pattern, text, flags=re.MULTILINE)

    chunks: list[dict[str, str]] = []

    # Extract top-level heading (# title) as context prefix
    doc_title = ""
    title_match = re.match(r"^#\s+(.+?)$", text, re.MULTILINE)
    if title_match:
        doc_title = title_match.group(1).strip()

    for section in raw_sections:
        section = section.strip()
        if not section:
            continue

        # Extract section heading
        section_heading = ""
        heading_match = re.match(r"^##\s+(.+?)$", section, re.MULTILINE)
        if heading_match:
            section_heading = heading_match.group(1).strip()

        # Word-level chunking within each section
        words = section.split()
        if len(words) <= CHUNK_SIZE_WORDS:
            # Section fits in one chunk
            metadata = _build_metadata(doc_title, section_heading, source_file)
            chunks.append({
                "text": f"{metadata}\n{section}",
                "source": source_file,
                "section": section_heading or doc_title,
            })
        else:
            # Split large section into overlapping chunks
            start = 0
            part = 1
            while start < len(words):
                end = min(len(words), start + CHUNK_SIZE_WORDS)
                chunk_text = " ".join(words[start:end])

                metadata = _build_metadata(
                    doc_title,
                    f"{section_heading} (part {part})" if section_heading else "",
                    source_file,
                )
                chunks.append({
                    "text": f"{metadata}\n{chunk_text}",
                    "source": source_file,
                    "section": section_heading or doc_title,
                })

                if end >= len(words):
                    break
                start = max(0, end - CHUNK_OVERLAP_WORDS)
                part += 1

    return chunks


def _build_metadata(doc_title: str, section: str, source: str) -> str:
    """Build a short metadata prefix for a chunk."""
    parts = []
    if doc_title:
        parts.append(f"[Source: {doc_title}]")
    if section:
        parts.append(f"[Section: {section}]")
    return " ".join(parts)


# ---------------------------------------------------------------------------
# Index Building
# ---------------------------------------------------------------------------
def _load_knowledge_base() -> list[dict[str, str]]:
    """Load and chunk all .md files from the knowledge base directory."""
    if not KNOWLEDGE_BASE_DIR.exists():
        logger.warning("Knowledge base directory not found: %s", KNOWLEDGE_BASE_DIR)
        return []

    all_chunks: list[dict[str, str]] = []

    for md_file in sorted(KNOWLEDGE_BASE_DIR.glob("*.md")):
        try:
            text = md_file.read_text(encoding="utf-8")
            file_chunks = _chunk_by_sections(text, md_file.name)
            all_chunks.extend(file_chunks)
            logger.info(
                "Loaded %d chunks from %s", len(file_chunks), md_file.name
            )
        except Exception as exc:
            logger.error("Failed to load %s: %s", md_file.name, exc)

    logger.info("Total knowledge base chunks: %d", len(all_chunks))
    return all_chunks


def build_index(force_rebuild: bool = False) -> dict[str, Any]:
    """Build (or load cached) FAISS index from the knowledge base.

    Returns a dict with keys: 'index', 'chunks', 'vectors'.
    The index is cached to disk for fast subsequent loads.
    """
    import faiss

    index_file = FAISS_INDEX_DIR / "index.faiss"
    meta_file = FAISS_INDEX_DIR / "metadata.pkl"

    # Try to load cached index
    if not force_rebuild and index_file.exists() and meta_file.exists():
        try:
            index = faiss.read_index(str(index_file))
            with open(meta_file, "rb") as f:
                metadata = pickle.load(f)
            logger.info(
                "Loaded cached FAISS index: %d vectors", index.ntotal
            )
            return {
                "index": index,
                "chunks": metadata["chunks"],
                "vectors": metadata.get("vectors"),
            }
        except Exception as exc:
            logger.warning("Failed to load cached index, rebuilding: %s", exc)

    # Build from scratch
    chunks = _load_knowledge_base()
    if not chunks:
        logger.warning("No knowledge base documents found — RAG disabled")
        return {"index": None, "chunks": [], "vectors": None}

    emb = _get_embedder()
    texts = [c["text"] for c in chunks]

    logger.info("Encoding %d chunks...", len(texts))
    vectors = emb.encode(texts, convert_to_numpy=True, show_progress_bar=False)

    # Normalize for cosine similarity via inner product
    norms = np.linalg.norm(vectors, axis=1, keepdims=True) + 1e-12
    vectors = vectors / norms

    # Build FAISS index (IndexFlatIP = inner product = cosine on normalised vecs)
    index = faiss.IndexFlatIP(vectors.shape[1])
    index.add(vectors.astype(np.float32))

    # Cache to disk
    FAISS_INDEX_DIR.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(index_file))
    with open(meta_file, "wb") as f:
        pickle.dump({"chunks": chunks, "vectors": vectors}, f)

    logger.info(
        "Built and cached FAISS index: %d vectors, dim=%d",
        index.ntotal, vectors.shape[1],
    )

    return {"index": index, "chunks": chunks, "vectors": vectors}


def _get_index() -> dict[str, Any]:
    """Get or build the FAISS index (singleton)."""
    global _index_pack
    if _index_pack is None:
        _index_pack = build_index()
    return _index_pack


# ---------------------------------------------------------------------------
# Retrieval
# ---------------------------------------------------------------------------
def _build_query_from_health_state(
    aggregated_state: dict,
    per_doc_results: list[dict] | None = None,
) -> str:
    """Build a natural-language RAG query from the patient's health state.

    Combines abnormal findings, conditions, medications, and BMI into
    a focused query that will match relevant knowledge base sections.
    """
    parts: list[str] = []

    # Abnormal findings (most important for dietary relevance)
    abnormals = aggregated_state.get("aggregated_abnormal_findings", [])
    if abnormals:
        finding_strs = []
        for f in abnormals[:10]:  # limit to top 10
            key = f.get("canonical_test_key", "")
            severity = f.get("severity", "")
            finding_strs.append(f"{key} ({severity})")
        parts.append("Abnormal lab findings: " + ", ".join(finding_strs))

    # Chronic conditions
    chronic = aggregated_state.get("chronic_flags", [])
    if chronic:
        chronic_strs = [
            f.get("test_name", f.get("test_key", "")) for f in chronic[:5]
        ]
        parts.append("Chronic conditions: " + ", ".join(chronic_strs))

    # BMI category
    bmi = aggregated_state.get("bmi")
    if bmi:
        cat = bmi.get("category", "")
        val = bmi.get("bmi_value", "")
        if cat:
            parts.append(f"BMI: {val} ({cat})")

    # Patient demographics
    patient = aggregated_state.get("patient_information", {})
    age = patient.get("age_years")
    if age is not None:
        if age >= 65:
            parts.append("Elderly patient (age ≥ 65)")
        elif age < 18:
            parts.append("Pediatric patient (age < 18)")

    # Medications from prescriptions
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

    # Specific test categories for targeted retrieval
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
) -> str:
    """Retrieve relevant medical nutrition guidelines for the patient.

    Parameters
    ----------
    aggregated_state : dict
        The merged health state from all processed documents.
    per_doc_results : list[dict] | None
        Per-document extraction results (for medication data).
    top_k : int
        Number of knowledge base chunks to retrieve.

    Returns
    -------
    str
        Concatenated relevant guideline excerpts, or empty string if
        RAG is unavailable.
    """
    try:
        pack = _get_index()
    except Exception as exc:
        logger.warning("RAG index unavailable: %s", exc)
        return ""

    index = pack.get("index")
    chunks = pack.get("chunks", [])

    if index is None or not chunks:
        logger.info("RAG disabled — no knowledge base index available")
        return ""

    import faiss

    # Build query from health state
    query = _build_query_from_health_state(aggregated_state, per_doc_results)
    logger.info("RAG query: %s", query[:200])

    # Encode query
    emb = _get_embedder()
    q_vec = emb.encode([query], convert_to_numpy=True)
    q_vec = q_vec / (np.linalg.norm(q_vec, axis=1, keepdims=True) + 1e-12)

    # Search
    distances, indices = index.search(q_vec.astype(np.float32), top_k)

    # Collect retrieved chunks with deduplication by section
    seen_sections: set[str] = set()
    retrieved: list[str] = []
    total_chars = 0

    for i, idx in enumerate(indices[0]):
        if idx < 0 or idx >= len(chunks):
            continue

        chunk = chunks[idx]
        section_key = f"{chunk['source']}::{chunk['section']}"
        score = float(distances[0][i])

        # Skip low-relevance chunks
        if score < 0.25:
            continue

        # Skip duplicate sections
        if section_key in seen_sections:
            continue
        seen_sections.add(section_key)

        text = chunk["text"]

        # Enforce character limit
        if total_chars + len(text) > MAX_CONTEXT_CHARS:
            remaining = MAX_CONTEXT_CHARS - total_chars
            if remaining > 100:
                text = text[:remaining] + "..."
                retrieved.append(text)
            break

        retrieved.append(text)
        total_chars += len(text)

    if not retrieved:
        logger.info("RAG retrieval returned no relevant chunks")
        return ""

    context = "\n\n---\n\n".join(retrieved)
    logger.info(
        "RAG retrieved %d chunks (%d chars) for diet prompt",
        len(retrieved), len(context),
    )
    return context


# ---------------------------------------------------------------------------
# Management utilities
# ---------------------------------------------------------------------------
def rebuild_index() -> int:
    """Force rebuild the FAISS index from knowledge base. Returns chunk count."""
    global _index_pack
    _index_pack = build_index(force_rebuild=True)
    return len(_index_pack.get("chunks", []))


def get_index_stats() -> dict[str, Any]:
    """Return stats about the current RAG index."""
    pack = _get_index()
    index = pack.get("index")
    chunks = pack.get("chunks", [])

    if index is None:
        return {"status": "disabled", "chunks": 0, "vectors": 0}

    sources = set()
    sections = set()
    for c in chunks:
        sources.add(c.get("source", "unknown"))
        sections.add(c.get("section", "unknown"))

    return {
        "status": "active",
        "total_chunks": len(chunks),
        "total_vectors": index.ntotal,
        "source_files": sorted(sources),
        "unique_sections": len(sections),
        "embedding_model": EMBEDDING_MODEL_ID,
        "index_path": str(FAISS_INDEX_DIR),
    }
