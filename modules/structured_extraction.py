"""LLM-based structured data extraction with schema validation."""

import json
import logging
import re
import time
from groq import Groq

from config.settings import (
    GROQ_API_KEY,
    EXTRACTION_MODEL,
    EXTRACTION_MODEL_FALLBACK,
    MAX_EXTRACTION_RETRIES,
    RATE_LIMIT_RETRY_DELAY_SECONDS,
)

logger = logging.getLogger(__name__)


def _is_rate_limit_error(exc: Exception) -> bool:
    """Detect 429 / rate-limit errors without hard-coding SDK class names."""
    if "RateLimit" in type(exc).__name__:
        return True
    if hasattr(exc, "status_code") and getattr(exc, "status_code", None) == 429:
        return True
    return False


_REQUIRED_KEYS = {
    "patient_information",
    "tests_index",
    "tests_by_category",
    "abnormal_findings",
    "clinical_notes",
    "metadata",
}

EXTRACTION_PROMPT = """\
You are a deterministic medical report JSON extraction engine.

Convert FULL OCR text of a diagnostic lab report into STRICT VALID JSON.
Return ONLY JSON. No explanations. No markdown. No extra text.

========================
OUTPUT SCHEMA (MANDATORY)
========================
{
  "patient_information": {
    "patient_name": string | null,
    "age_years": number | null,
    "gender": string | null,
    "lab_number": string | null,
    "report_status": string | null,
    "collection_datetime": string | null,
    "report_datetime": string | null,
    "laboratory_name": string | null
  },

  "tests_index": {
    "<canonical_test_key>": {
      "test_name": string,
      "value": number | string | null,
      "units": string | null,
      "reference_range": string | null,
      "interpretation": "low" | "normal" | "high" | "borderline" | null,
      "category": string
    }
  },

  "tests_by_category": {
    "complete_blood_count": [ "<canonical_test_key>" ],
    "liver_function": [ "<canonical_test_key>" ],
    "kidney_function": [ "<canonical_test_key>" ],
    "lipid_profile": [ "<canonical_test_key>" ],
    "thyroid_profile": [ "<canonical_test_key>" ],
    "diabetes_related": [ "<canonical_test_key>" ],
    "vitamins_and_minerals": [ "<canonical_test_key>" ],
    "electrolytes": [ "<canonical_test_key>" ],
    "other_tests": [ "<canonical_test_key>" ]
  },

  "abnormal_findings": [
    {
      "canonical_test_key": string,
      "observed_value": number | string,
      "expected_range": string,
      "severity": "low" | "high" | "critical"
    }
  ],

  "clinical_notes": {
    "interpretations": [ string ],
    "comments": [ string ],
    "notes": [ string ],
    "recommendations": [ string ],
    "disclaimers": [ string ]
  },

  "metadata": {
    "total_pages": number | null,
    "page_numbers_detected": [ number ],
    "report_end_marker_present": boolean | null
  }
}

========================
CANONICAL KEY RULES
========================
- Each test appears EXACTLY ONCE in tests_index
- Use normalized snake_case
- Remove units, assay methods, punctuation, brackets
- Normalize common variants:
    Hb → hemoglobin
    HbA1c → hba1c
    SGPT → alt
    SGOT → ast
    Total Cholesterol → cholesterol_total
- Same key must be used everywhere

========================
VALUE CLEANING RULES
========================
- Extract numeric value only (strip %, mg/dL, etc.)
- Units must go into "units"
- If value is textual (e.g., "Reactive") keep as string
- If range format is "x - y", preserve full string in reference_range
- Do not merge units into value

========================
INTERPRETATION RULES
========================
If numeric value and numeric range exist:
    value < lower → "low"
    value > upper → "high"
    else → "normal"
If explicitly mentioned borderline → "borderline"
If no range → null

========================
RELATIONAL INTEGRITY RULES
========================
- tests_by_category must contain ONLY canonical_test_keys
- Do NOT duplicate full test objects inside category arrays
- Every key in tests_by_category must exist in tests_index

========================
STRICT OUTPUT RULES
========================
- Valid JSON only
- No duplicate keys
- No trailing commas
- Use null if missing
- If no tests found, return empty structures
"""


def _clean_json_response(text: str) -> str:
    """Strip markdown code fences and leading/trailing whitespace (fallback path)."""
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _validate_schema(data: dict) -> None:
    """
    Post-parse validation enforcing schema and relational integrity.
    Raises ValueError if critical checks fail.
    """
    missing = _REQUIRED_KEYS - set(data.keys())
    if missing:
        raise ValueError(f"Extracted JSON is missing required keys: {missing}")

    ti = data.get("tests_index")
    if ti is not None and not isinstance(ti, dict):
        raise ValueError(f"tests_index must be a dict, got {type(ti).__name__}")

    tbc = data.get("tests_by_category", {})
    if isinstance(tbc, dict) and isinstance(ti, dict):
        index_keys = set(ti.keys())
        for category, keys in tbc.items():
            if not isinstance(keys, list):
                continue
            orphans = set(keys) - index_keys
            if orphans:
                logger.warning(
                    "Category '%s' references keys not in tests_index: %s — removing",
                    category, orphans,
                )
                data["tests_by_category"][category] = [
                    k for k in keys if k in index_keys
                ]


def _parse_range(ref: str | None) -> tuple[float | None, float | None]:
    """
    Parse a reference range string like '4.0 - 11.0' or '< 200' into (low, high).
    Returns (None, None) on failure.
    """
    if not ref:
        return None, None

    ref = ref.strip()

    # Pattern: "4.0 - 11.0" or "4.0-11.0"
    m = re.match(r"(\d+\.?\d*)\s*[-–—to]+\s*(\d+\.?\d*)", ref)
    if m:
        return float(m.group(1)), float(m.group(2))

    # Pattern: "< 200" or "<= 200"
    m = re.match(r"[<≤]\s*=?\s*(\d+\.?\d*)", ref)
    if m:
        return None, float(m.group(1))

    # Pattern: "> 40" or ">= 40"
    m = re.match(r"[>≥]\s*=?\s*(\d+\.?\d*)", ref)
    if m:
        return float(m.group(1)), None

    return None, None


def _verify_interpretations(data: dict) -> dict:
    """Cross-check LLM interpretations against deterministic rules."""
    tests_index = data.get("tests_index", {})
    corrected = 0

    for key, test in tests_index.items():
        value_raw = test.get("value")
        ref_range = test.get("reference_range")

        if value_raw is None or ref_range is None:
            continue

        try:
            value = float(str(value_raw))
        except (ValueError, TypeError):
            continue

        low, high = _parse_range(ref_range)
        if low is None and high is None:
            continue

        if low is not None and value < low:
            computed = "low"
        elif high is not None and value > high:
            computed = "high"
        else:
            computed = "normal"

        llm_interp = test.get("interpretation")
        if llm_interp and llm_interp != computed:
            logger.warning(
                "Interpretation corrected for '%s': LLM said '%s', "
                "backend computed '%s' (value=%s, range=%s)",
                key, llm_interp, computed, value, ref_range,
            )
            test["interpretation"] = computed
            corrected += 1

    if corrected:
        logger.info("Corrected %d interpretation(s) via backend validation", corrected)

    # Also rebuild abnormal_findings from verified data
    abnormal: list[dict] = []
    for key, test in tests_index.items():
        interp = test.get("interpretation")
        if interp in ("low", "high"):
            abnormal.append({
                "canonical_test_key": key,
                "observed_value": test.get("value"),
                "expected_range": test.get("reference_range", ""),
                "severity": interp,
            })
    data["abnormal_findings"] = abnormal

    return data


def _call_llm(client: Groq, ocr_text: str, model: str) -> str:
    """Send the extraction request to Groq and return raw text response."""
    response = client.chat.completions.create(
        model=model,
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a medical report analyser. "
                    "Analyze the report and return valid JSON."
                ),
            },
            {
                "role": "user",
                "content": f"{EXTRACTION_PROMPT}\n\nReport Text:\n{ocr_text}",
            },
        ],
        temperature=0.0,
        max_completion_tokens=8192,
    )
    return response.choices[0].message.content or ""


def extract_structured_data(ocr_text: str) -> dict:
    """Extract structured medical data from OCR text using an LLM."""
    if not GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY is not configured.")

    client = Groq(api_key=GROQ_API_KEY)
    last_error: Exception | None = None

    for attempt in range(1, MAX_EXTRACTION_RETRIES + 1):
        model = EXTRACTION_MODEL if attempt <= 2 else EXTRACTION_MODEL_FALLBACK

        try:
            raw = _call_llm(client, ocr_text, model)
            cleaned = _clean_json_response(raw)
            data = json.loads(cleaned)

            _validate_schema(data)

            data = _verify_interpretations(data)

            logger.info(
                "Structured extraction succeeded (attempt %d, model=%s)",
                attempt, model,
            )
            return data

        except (json.JSONDecodeError, ValueError) as exc:
            last_error = exc
            logger.warning(
                "Extraction attempt %d parse error (model=%s): %s",
                attempt, model, exc,
            )
            time.sleep(0.5 * attempt)

        except Exception as exc:
            last_error = exc
            if _is_rate_limit_error(exc):
                wait = RATE_LIMIT_RETRY_DELAY_SECONDS
                logger.warning(
                    "Rate-limit hit (attempt %d), waiting %.1fs",
                    attempt, wait,
                )
            else:
                wait = 1.0 * attempt
                logger.warning(
                    "Extraction API error (attempt %d, model=%s): %s",
                    attempt, model, exc,
                )
            time.sleep(wait)

    raise RuntimeError(
        f"Structured extraction failed after {MAX_EXTRACTION_RETRIES} attempts. "
        f"Last error: {last_error}"
    )
