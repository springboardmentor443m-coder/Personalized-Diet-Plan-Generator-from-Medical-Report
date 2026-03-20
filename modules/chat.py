"""AI Chat Assistant — RAG-powered conversational interface for patient queries.

Retrieves patient-specific context from ChromaDB (session-scoped),
combines with chat history, and generates responses via Groq LLM.
"""

from __future__ import annotations

import json
import logging
import re
import time
from typing import Any

from groq import Groq

from config.settings import (
    GROQ_API_KEY,
    CHAT_MODEL,
    CHAT_MAX_HISTORY_TURNS,
    CHAT_MAX_CONTEXT_CHUNKS,
)
from modules.knowledge_store import retrieve_for_patient, retrieve_guidelines
from services import database as db

logger = logging.getLogger(__name__)

_NO_ACCESS_MARKERS = (
    "don't have access",
    "do not have access",
    "can't access",
    "cannot access",
    "unable to access",
    "no information in your medical reports",
    "i don't have your",
)

_PATIENT_DATA_TYPES = {
    "ocr_text",
    "structured_json",
    "diet_plan",
    "patient_profile",
    "session_aggregate",
    "diet_meta",
    "safety_json",
}

CHAT_SYSTEM_PROMPT = """\
You are a helpful, empathetic AI health assistant for a personalised diet planning application.
You have access to the patient's medical reports, lab results, health profile, and generated diet plan.

IMPORTANT:
Answer ONLY using the retrieved patient context provided below.
Never invent lab values, diagnoses, medications, or dietary advice.

RULES:
1. Answer questions ONLY using the retrieved patient context below. Do NOT fabricate or assume any medical information.
2. If the retrieved context does not contain the answer, respond exactly with:
   **"The available report information does not contain this detail."**
   Do not guess, infer, or supplement with general medical knowledge.
3. Do NOT diagnose diseases or medical conditions. Only explain what the report data indicates.
4. When mentioning lab results:
   - Include the exact value from the report.
   - State whether it is normal, high, or low if that information is available.
5. When explaining diet recommendations:
   - Reference the patient's specific lab findings or conditions from the report.
   - Provide practical, food-based guidance (e.g. specific foods to include or avoid) when possible.
6. Keep answers concise, clear, actionable, and understandable for a patient without medical training.
7. Maintain a calm, empathetic tone when explaining results or recommendations.

RETRIEVED PATIENT CONTEXT:
{context}
"""

# Improved system prompt that balances guidelines with general health knowledge
CHAT_SYSTEM_PROMPT_ENHANCED = """\
You are a friendly, knowledgeable health assistant for a personalized diet planning application.

PRIMARY DIRECTIVE:
Answer questions using the patient's medical reports, lab results, and diet plan (provided in context below).

SECONDARY DIRECTIVE (when patient data is not available):
If the patient's retrieved data doesn't answer their question, you may provide general health guidance
based on established medical knowledge, but ALWAYS:
- Clearly indicate you're giving general guidance ("Based on general health guidelines...")
- Suggest they discuss specifics with their doctor
- NEVER diagnose conditions or prescribe medications
- NEVER invent lab values, test results, or medical history

CORE RULES:
1. Patient data is your PRIMARY source - use it whenever available and relevant
2. Give specific, actionable advice tied to THEIR labs/diet, not generic platitudes
3. When explaining lab results: state exact values, reference normal ranges if available
4. When recommending foods: explain WHY based on their conditions (e.g., "High potassium, so limit bananas")
5. NEVER diagnose. Say "Your report shows elevated blood sugar" not "You have diabetes"
6. For questions your patient context can't answer:
     - Offer general guidance with a disclaimer
     - Suggest they ask their doctor for specifics
7. Keep responses concise, clear, and jargon-free
8. For any health emergency symptoms, recommend immediate medical attention
9. Maintain a warm, empathetic, encouraging tone
10. Formatting style:
    - Use clean plain text with short paragraphs or simple bullet points
    - Do not use markdown styling like **bold**, ## headings, or numbered bold section headers

RETRIEVED PATIENT CONTEXT:
{context}
"""


def _looks_like_no_access(text: str) -> bool:
    lower = (text or "").lower()
    return any(marker in lower for marker in _NO_ACCESS_MARKERS)


def _trim_text(text: str, max_chars: int = 6000) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rstrip() + " ..."


def _safe_json_load(raw: Any) -> Any:
    if not raw:
        return None
    if isinstance(raw, (dict, list)):
        return raw
    if not isinstance(raw, str):
        return None
    try:
        return json.loads(raw)
    except Exception:
        return None


def _cleanup_response_text(text: str) -> str:
    """Normalize model output so UI shows clean readable text."""
    cleaned = (text or "").strip()
    if not cleaned:
        return ""

    # Convert common markdown section patterns to plain text.
    cleaned = re.sub(r"(?m)^\s*(\d+)\.\s*\*\*([^*]+)\*\*\s*:?[ \t]*", r"\1. \2: ", cleaned)
    cleaned = re.sub(r"\*\*(.*?)\*\*", r"\1", cleaned)
    cleaned = re.sub(r"__(.*?)__", r"\1", cleaned)
    cleaned = re.sub(r"`([^`]+)`", r"\1", cleaned)
    cleaned = re.sub(r"(?m)^\s{0,3}#{1,6}\s*", "", cleaned)
    cleaned = re.sub(r"(?m)^\s*[-*]\s+", "• ", cleaned)

    # Clean excess whitespace introduced by normalization.
    cleaned = re.sub(r"[ \t]+\n", "\n", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def _tokenize(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9]+", (text or "").lower()) if len(t) > 2}


def _score_chunk_for_query(query: str, chunk: dict[str, Any]) -> float:
    meta = chunk.get("metadata", {}) or {}
    data_type = str(meta.get("data_type", "")).lower()

    base_similarity = float(chunk.get("similarity", 0.0) or 0.0)
    quality_score = float(meta.get("quality_score", 0.5) or 0.5)

    data_type_bonus = {
        "structured_json": 0.18,
        "session_aggregate": 0.16,
        "diet_plan": 0.14,
        "patient_profile": 0.12,
        "ocr_text": 0.10,
        "diet_meta": 0.07,
        "safety_json": 0.05,
    }.get(data_type, 0.0)

    query_tokens = _tokenize(query)
    if not query_tokens:
        return round(min(1.0, base_similarity + data_type_bonus), 4)

    text_tokens = _tokenize(str(chunk.get("text", ""))[:2500])
    overlap = len(query_tokens & text_tokens)
    coverage = overlap / max(1, len(query_tokens))

    score = (
        0.50 * min(max(base_similarity, 0.0), 1.0)
        + 0.30 * coverage
        + 0.08 * quality_score
        + data_type_bonus
    )
    return round(min(1.0, score), 4)


def _select_top_chunks(
    query: str,
    chunks: list[dict[str, Any]],
    top_k: int,
) -> list[dict[str, Any]]:
    ranked: list[dict[str, Any]] = []
    for chunk in chunks:
        candidate = dict(chunk)
        candidate["query_score"] = _score_chunk_for_query(query, candidate)
        ranked.append(candidate)

    ranked.sort(
        key=lambda c: (c.get("query_score", 0.0), c.get("similarity", 0.0)),
        reverse=True,
    )
    return ranked[: max(1, top_k)]


def _build_sqlite_fallback_chunks(session_id: str) -> list[dict[str, Any]]:
    chunks: list[dict[str, Any]] = []

    try:
        session = db.get_session(session_id)
        documents = db.get_documents_for_session(session_id)
    except Exception as exc:
        logger.warning("SQLite fallback load failed for session %s: %s", session_id, exc)
        return []

    if not session and not documents:
        return []

    session_result = _safe_json_load((session or {}).get("result_json"))
    diet_plan = _safe_json_load((session or {}).get("diet_plan_json"))
    safety_json = _safe_json_load((session or {}).get("safety_json"))
    diet_meta = _safe_json_load((session or {}).get("diet_meta_json"))

    if isinstance(session_result, dict):
        summary_lines: list[str] = []
        patient_info = session_result.get("patient_information") or {}
        aggregated_tests = session_result.get("aggregated_tests") or {}
        abnormal = session_result.get("aggregated_abnormal_findings") or []
        chronic_flags = session_result.get("chronic_flags") or []
        bmi = session_result.get("bmi")

        if isinstance(patient_info, dict):
            if patient_info.get("patient_name"):
                summary_lines.append(f"Patient: {patient_info.get('patient_name')}")
            if patient_info.get("age_years") is not None:
                summary_lines.append(f"Age: {patient_info.get('age_years')} years")
            if patient_info.get("gender"):
                summary_lines.append(f"Gender: {patient_info.get('gender')}")

        if isinstance(bmi, dict) and bmi.get("bmi_value") is not None:
            summary_lines.append(
                "BMI: "
                f"{bmi.get('bmi_value')}"
                f" ({bmi.get('category', 'unknown category')})"
            )

        if isinstance(aggregated_tests, dict) and aggregated_tests:
            test_lines: list[str] = []
            for test_name, payload in list(aggregated_tests.items())[:40]:
                if isinstance(payload, dict):
                    value = payload.get("value", "")
                    status = payload.get("status") or payload.get("interpretation") or ""
                    if value != "":
                        if status:
                            test_lines.append(f"{test_name}: {value} ({status})")
                        else:
                            test_lines.append(f"{test_name}: {value}")
                else:
                    test_lines.append(f"{test_name}: {payload}")
            if test_lines:
                summary_lines.append("Aggregated tests: " + "; ".join(test_lines))

        if abnormal:
            abnormal_lines: list[str] = []
            for item in abnormal[:20]:
                if isinstance(item, dict):
                    label = (
                        item.get("test_name")
                        or item.get("name")
                        or item.get("parameter")
                        or "finding"
                    )
                    value = item.get("value")
                    status = item.get("status") or item.get("interpretation") or "abnormal"
                    if value not in (None, ""):
                        abnormal_lines.append(f"{label}: {value} ({status})")
                    else:
                        abnormal_lines.append(f"{label}: {status}")
                else:
                    abnormal_lines.append(str(item))
            if abnormal_lines:
                summary_lines.append("Abnormal findings: " + "; ".join(abnormal_lines))

        if chronic_flags:
            summary_lines.append("Chronic flags: " + "; ".join(str(x) for x in chronic_flags[:12]))

        if summary_lines:
            chunks.append({
                "text": _trim_text("\n".join(summary_lines), 3000),
                "metadata": {
                    "data_type": "session_aggregate",
                    "source": "sqlite.sessions",
                    "session_id": session_id,
                    "quality_score": 0.75,
                },
                "similarity": 0.80,
                "doc_id": f"{session_id}::sqlite::aggregate",
            })

    if diet_plan is not None:
        chunks.append({
            "text": _trim_text(f"Generated diet plan:\n{json.dumps(diet_plan, default=str)}", 3500),
            "metadata": {
                "data_type": "diet_plan",
                "source": "sqlite.sessions",
                "session_id": session_id,
                "quality_score": 0.70,
            },
            "similarity": 0.74,
            "doc_id": f"{session_id}::sqlite::diet_plan",
        })

    if safety_json is not None:
        chunks.append({
            "text": _trim_text(f"Diet safety checks:\n{json.dumps(safety_json, default=str)}", 2200),
            "metadata": {
                "data_type": "safety_json",
                "source": "sqlite.sessions",
                "session_id": session_id,
                "quality_score": 0.65,
            },
            "similarity": 0.62,
            "doc_id": f"{session_id}::sqlite::safety",
        })

    if diet_meta is not None:
        chunks.append({
            "text": _trim_text(f"Diet metadata:\n{json.dumps(diet_meta, default=str)}", 1800),
            "metadata": {
                "data_type": "diet_meta",
                "source": "sqlite.sessions",
                "session_id": session_id,
                "quality_score": 0.60,
            },
            "similarity": 0.58,
            "doc_id": f"{session_id}::sqlite::diet_meta",
        })

    for doc in documents:
        parsed = _safe_json_load(doc.get("result_json"))
        if not isinstance(parsed, dict):
            continue

        filename = doc.get("original_filename") or ""
        doc_id = doc.get("id") or ""
        doc_type = doc.get("doc_type") or parsed.get("doc_type") or ""

        ocr_text = parsed.get("raw_ocr_text")
        if isinstance(ocr_text, str) and ocr_text.strip():
            chunks.append({
                "text": _trim_text(ocr_text, 2600),
                "metadata": {
                    "data_type": "ocr_text",
                    "filename": filename,
                    "doc_type": doc_type,
                    "source": "sqlite.documents",
                    "session_id": session_id,
                    "quality_score": 0.55,
                },
                "similarity": 0.66,
                "doc_id": doc_id or f"{session_id}::sqlite::ocr::{len(chunks)}",
            })

        structured_json = parsed.get("structured_json")
        if structured_json is not None:
            chunks.append({
                "text": _trim_text(json.dumps(structured_json, default=str), 2400),
                "metadata": {
                    "data_type": "structured_json",
                    "filename": filename,
                    "doc_type": doc_type,
                    "source": "sqlite.documents",
                    "session_id": session_id,
                    "quality_score": 0.62,
                },
                "similarity": 0.72,
                "doc_id": doc_id or f"{session_id}::sqlite::structured::{len(chunks)}",
            })

    return chunks


def _has_patient_specific_chunks(chunks: list[dict[str, Any]]) -> bool:
    for chunk in chunks:
        data_type = str((chunk.get("metadata") or {}).get("data_type", "")).lower()
        if data_type in _PATIENT_DATA_TYPES:
            return True
    return False


def _build_context(session_id: str, query: str) -> tuple[str, list[dict[str, Any]]]:
    """Build chat context using tiered retrieval with robust fallback."""
    retrieval_tier = "none"
    chunks: list[dict[str, Any]] = []

    try:
        chroma_chunks = retrieve_for_patient(
            query=query,
            session_id=session_id,
            top_k=max(CHAT_MAX_CONTEXT_CHUNKS * 2, 4),
        )
    except Exception as exc:
        logger.warning("Chat context retrieval failed for session %s: %s", session_id, exc)
        chroma_chunks = []

    if chroma_chunks:
        chunks = _select_top_chunks(query, chroma_chunks, CHAT_MAX_CONTEXT_CHUNKS)
        retrieval_tier = "chromadb_patient"
    else:
        sqlite_chunks = _build_sqlite_fallback_chunks(session_id)
        if sqlite_chunks:
            chunks = _select_top_chunks(query, sqlite_chunks, CHAT_MAX_CONTEXT_CHUNKS)
            retrieval_tier = "sqlite_fallback"

    if not chunks:
        try:
            guideline_chunks = retrieve_guidelines(
                query=query,
                top_k=max(CHAT_MAX_CONTEXT_CHUNKS, 2),
            )
        except Exception as exc:
            logger.warning("Guideline fallback retrieval failed for session %s: %s", session_id, exc)
            guideline_chunks = []

        if guideline_chunks:
            chunks = _select_top_chunks(query, guideline_chunks, CHAT_MAX_CONTEXT_CHUNKS)
            retrieval_tier = "guideline_fallback"

    if not chunks:
        return "No patient data found for this session.", []

    label_map = {
        "ocr_text": "Medical Report (OCR)",
        "structured_json": "Extracted Lab Data",
        "diet_plan": "Generated Diet Plan",
        "patient_profile": "Patient Profile",
        "session_aggregate": "Session Summary",
        "diet_meta": "Diet Metadata",
        "safety_json": "Diet Safety Checks",
    }

    parts: list[str] = []
    for i, chunk in enumerate(chunks, 1):
        meta = chunk.get("metadata", {}) or {}
        data_type = str(meta.get("data_type", "unknown"))
        source_name = meta.get("filename") or meta.get("source_file") or meta.get("source") or ""
        relevance = float(chunk.get("query_score", chunk.get("similarity", 0.0)) or 0.0)
        label = label_map.get(data_type, data_type.replace("_", " ").title())

        source_piece = f" | Source: {source_name}" if source_name else ""
        parts.append(
            f"[Source {i}: {label}{source_piece} | Relevance: {relevance:.2f}]\n"
            f"{_trim_text(str(chunk.get('text', '')), 1800)}"
        )

    context_str = _trim_text("\n\n---\n\n".join(parts), max_chars=9000)
    logger.info(
        "Chat RAG: %d chunks (%s) for session %s (query: %s)",
        len(chunks), retrieval_tier, session_id, query[:80],
    )
    return context_str, chunks


def _trim_history(
    chat_history: list[dict[str, str]],
) -> list[dict[str, str]]:
    """Keep only the last N turns to respect token limits."""
    max_messages = CHAT_MAX_HISTORY_TURNS * 2  # each turn = user + assistant
    if len(chat_history) > max_messages:
        return chat_history[-max_messages:]
    return chat_history


def chat(
    session_id: str,
    user_message: str,
    chat_history: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    """Process a chat message with RAG context retrieval.

    Parameters
    ----------
    session_id : str
        Patient session ID for ChromaDB scoping.
    user_message : str
        The user's question.
    chat_history : list[dict] | None
        Previous messages as [{"role": "user"|"assistant", "content": "..."}].

    Returns
    -------
    dict with keys: response, context_chunks, model, response_time_seconds
    """
    if not session_id:
        return {
            "response": "No active session. Please upload and analyze your medical reports first.",
            "context_chunks": [],
            "model": CHAT_MODEL,
            "response_time_seconds": 0,
        }

    start = time.time()

    # 1. Retrieve patient context from ChromaDB
    context_str, chunks = _build_context(session_id, user_message)

    # 2. Build messages array
    system_msg = CHAT_SYSTEM_PROMPT_ENHANCED.format(context=context_str)
    messages: list[dict[str, str]] = [{"role": "system", "content": system_msg}]

    # 3. Add trimmed chat history
    if chat_history:
        messages.extend(_trim_history(chat_history))

    # 4. Add current user message
    messages.append({"role": "user", "content": user_message})

    # 5. Call Groq LLM
    try:
        client = Groq(api_key=GROQ_API_KEY)
        completion = client.chat.completions.create(
            model=CHAT_MODEL,
            messages=messages,
            temperature=0.3,
            max_completion_tokens=2048,
        )
        response_text = completion.choices[0].message.content or ""

        # If we have patient context but model still says it has no access,
        # do one guided retry with a stronger grounding reminder.
        if chunks and _has_patient_specific_chunks(chunks) and _looks_like_no_access(response_text):
            try:
                rescue_messages = [
                    *messages,
                    {
                        "role": "system",
                        "content": (
                            "Retrieved patient context is available above. "
                            "Do not claim lack of access to reports or diet plan. "
                            "Answer directly from the provided context and be specific."
                        ),
                    },
                ]
                rescue_completion = client.chat.completions.create(
                    model=CHAT_MODEL,
                    messages=rescue_messages,
                    temperature=0.2,
                    max_completion_tokens=2048,
                )
                rescue_text = rescue_completion.choices[0].message.content or ""
                if rescue_text and not _looks_like_no_access(rescue_text):
                    response_text = rescue_text
            except Exception as exc:
                logger.debug("Chat recovery pass failed: %s", exc)
    except Exception as exc:
        logger.error("Chat LLM call failed: %s", exc)
        response_text = (
            "I'm sorry, I encountered an error processing your question. "
            "Please try again in a moment."
        )

    elapsed = round(time.time() - start, 2)
    response_text = _cleanup_response_text(response_text)
    logger.info("Chat response generated in %.2fs (model: %s)", elapsed, CHAT_MODEL)

    return {
        "response": response_text,
        "context_chunks": [
            {
                "data_type": c.get("metadata", {}).get("data_type", ""),
                "similarity": c.get("similarity", 0),
                "query_score": c.get("query_score", c.get("similarity", 0)),
                "source": (
                    c.get("metadata", {}).get("filename")
                    or c.get("metadata", {}).get("source_file")
                    or c.get("metadata", {}).get("source", "")
                ),
            }
            for c in chunks
        ],
        "model": CHAT_MODEL,
        "response_time_seconds": elapsed,
    }
