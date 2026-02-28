"""Rule-based document type classifier for medical reports."""

import logging

logger = logging.getLogger(__name__)

DOC_TYPES = frozenset({
    "lab_report",
    "prescription",
    "discharge_summary",
    "diagnosis",
    "other",
})

_RX_KEYWORDS: list[str] = [
    "tablet", "capsule", "mg daily", "dosage", "prescribed",
    " rx ", "twice daily", "once daily", "before meals",
    "after meals", "medication", "drug", "syrup", "injection",
    "ointment", "inhaler",
]

_DISCHARGE_KEYWORDS: list[str] = [
    "discharge", "admitted", "hospital stay", "inpatient",
    "admission", "discharged on", "date of admission",
    "length of stay", "hospital course", "ward",
]

_DIAGNOSIS_KEYWORDS: list[str] = [
    "diagnosis", "icd-10", "icd-9", "condition",
    "diagnosed with", "clinical impression",
    "primary diagnosis", "secondary diagnosis",
    "differential diagnosis",
]


def _is_numeric(value) -> bool:
    """Check if a value can be interpreted as a number."""
    if isinstance(value, (int, float)):
        return True
    try:
        float(str(value))
        return True
    except (ValueError, TypeError):
        return False


def classify_document(extracted_data: dict, ocr_text: str) -> str:
    """Classify a document based on OCR text content."""
    scores: dict[str, int] = {t: 0 for t in DOC_TYPES}
    ocr_lower = ocr_text.lower()

    tests_index = extracted_data.get("tests_index", {})
    numeric_with_range = sum(
        1 for t in tests_index.values()
        if _is_numeric(t.get("value")) and t.get("reference_range")
    )
    scores["lab_report"] += min(numeric_with_range * 2, 10)

    if len(tests_index) >= 3:
        scores["lab_report"] += 3

    rx_hits = sum(1 for kw in _RX_KEYWORDS if kw in ocr_lower)
    scores["prescription"] += rx_hits * 2

    dc_hits = sum(1 for kw in _DISCHARGE_KEYWORDS if kw in ocr_lower)
    scores["discharge_summary"] += dc_hits * 2

    dx_hits = sum(1 for kw in _DIAGNOSIS_KEYWORDS if kw in ocr_lower)
    scores["diagnosis"] += dx_hits * 2

    best_type = max(scores, key=lambda k: scores[k])
    best_score = scores[best_type]

    if best_score < 2:
        best_type = "other"

    logger.info(
        "Document classified as '%s' (scores: %s)",
        best_type,
        {k: v for k, v in scores.items() if v > 0} or {"other": 0},
    )
    return best_type
