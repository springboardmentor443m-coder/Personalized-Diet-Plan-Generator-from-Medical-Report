"""Aggregate multiple medical reports into a unified health state."""

from __future__ import annotations

import logging
import re
from datetime import datetime

from config.settings import (
    CONFLICT_THRESHOLD_PERCENT,
    CHRONIC_CONDITION_MIN_REPORTS,
    CHRONIC_CONDITION_MIN_DAYS,
)

logger = logging.getLogger(__name__)

_DATE_MIN = datetime.min


_DATE_FORMATS: list[str] = [
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d",
    "%d/%m/%Y %H:%M:%S",
    "%d/%m/%Y",
    "%d-%m-%Y",
    "%m/%d/%Y",
    "%d %b %Y",
    "%d %B %Y",
    "%b %d, %Y",
    "%B %d, %Y",
]


def _parse_datetime(dt_str: str | None) -> datetime | None:
    """Try multiple datetime formats; return None on failure."""
    if not dt_str or not isinstance(dt_str, str):
        return None
    cleaned = dt_str.strip()
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(cleaned, fmt)
        except ValueError:
            continue
    # Last resort — try ISO‑8601 with timezone suffix stripped
    try:
        cleaned = re.sub(r"[Zz]$", "", cleaned)
        cleaned = re.sub(r"[+-]\d{2}:\d{2}$", "", cleaned)
        return datetime.fromisoformat(cleaned)
    except (ValueError, TypeError):
        return None


def _resolve_document_date(
    doc_result: dict,
) -> tuple[datetime | None, str]:
    """Extract the best available date from a document result."""
    patient_info = doc_result.get("patient_information", {})

    # 1. report_datetime
    dt = _parse_datetime(patient_info.get("report_datetime"))
    if dt:
        return dt, "high"

    # 2. collection_datetime
    dt = _parse_datetime(patient_info.get("collection_datetime"))
    if dt:
        return dt, "medium"

    return None, "unknown"


def _resolve_conflict(
    v1: float,
    v2: float,
    u1: str | None,
    u2: str | None,
) -> dict:
    """Resolve conflicting values for the same test on the same date."""
    u1_norm = (u1 or "").strip().lower()
    u2_norm = (u2 or "").strip().lower()

    if u1_norm and u2_norm and u1_norm != u2_norm:
        return {"resolution": "conflict", "reason": "unit_mismatch"}

    max_abs = max(abs(v1), abs(v2))
    if max_abs == 0:
        return {"resolution": "averaged", "value": 0.0}

    pct_diff = abs(v1 - v2) / max_abs

    if pct_diff <= CONFLICT_THRESHOLD_PERCENT:
        return {"resolution": "averaged", "value": round((v1 + v2) / 2, 4)}

    return {
        "resolution": "conflict",
        "reason": f"percentage_diff={pct_diff:.4f}",
    }


def _compute_trend(
    current_interp: str | None,
    previous_interp: str | None,
) -> str | None:
    """
    Compare two consecutive interpretations to derive a trend.

    Returns one of: ``improving``, ``worsening``, ``stable``, ``changed``, or ``None``.
    """
    if not current_interp or not previous_interp:
        return None

    if current_interp == previous_interp:
        return "stable"

    # abnormal → normal = improving
    if previous_interp in ("low", "high") and current_interp == "normal":
        return "improving"

    # normal → abnormal = worsening
    if previous_interp == "normal" and current_interp in ("low", "high"):
        return "worsening"

    # one abnormal direction to another = worsening
    if previous_interp in ("low", "high") and current_interp in ("low", "high"):
        return "worsening"

    return "changed"


def _detect_chronic_conditions(
    all_test_entries: dict[str, list[dict]],
) -> list[dict]:
    """
    Flag a test as *chronic* when the same abnormal interpretation
    appears in ≥ ``CHRONIC_CONDITION_MIN_REPORTS`` reports that are
    separated by ≥ ``CHRONIC_CONDITION_MIN_DAYS`` calendar days.
    """
    chronic: list[dict] = []

    for key, entries in all_test_entries.items():
        abnormal = [
            e for e in entries
            if e.get("interpretation") in ("low", "high")
            and e.get("effective_date") is not None
        ]
        if len(abnormal) < CHRONIC_CONDITION_MIN_REPORTS:
            continue

        abnormal.sort(key=lambda e: e["effective_date"])
        first_dt = abnormal[0]["effective_date"]
        last_dt = abnormal[-1]["effective_date"]
        span = (last_dt - first_dt).days

        if span >= CHRONIC_CONDITION_MIN_DAYS:
            chronic.append({
                "test_key": key,
                "test_name": abnormal[0].get("test_name", key),
                "abnormality_type": abnormal[-1].get("interpretation"),
                "occurrences": len(abnormal),
                "first_seen": first_dt.isoformat(),
                "last_seen": last_dt.isoformat(),
                "span_days": span,
            })

    return chronic


def _merge_patient_info(dated_docs: list[dict]) -> dict:
    """Merge patient information — later-dated documents overwrite earlier ones."""
    merged: dict = {}
    for dd in dated_docs:
        pi = dd["doc"].get("patient_information", {})
        for k, v in pi.items():
            if v is not None:
                merged[k] = v
    return merged


def _aggregate_abnormal_findings(aggregated_tests: dict) -> list[dict]:
    """Build current abnormal findings from the aggregated (latest) test values."""
    abnormal: list[dict] = []
    for key, test in aggregated_tests.items():
        interp = test.get("current_interpretation")
        if interp in ("low", "high"):
            abnormal.append({
                "canonical_test_key": key,
                "observed_value": test.get("current_value"),
                "expected_range": test.get("reference_range", ""),
                "severity": interp,
                "source_doc_id": test.get("source_doc_id"),
                "trend": test.get("trend"),
            })

    severity_order = {"high": 0, "low": 1}
    abnormal.sort(key=lambda x: severity_order.get(x.get("severity", ""), 2))
    return abnormal


def aggregate_health_state(doc_results: list[dict]) -> dict:
    """Aggregate multiple document results into a unified health state."""
    dated_docs: list[dict] = []
    for doc in doc_results:
        dt, confidence = _resolve_document_date(doc)
        dated_docs.append({
            "doc": doc,
            "effective_date": dt,
            "date_confidence": confidence,
        })

    # Sort ascending (None dates go to the front via _DATE_MIN)
    dated_docs.sort(key=lambda d: d["effective_date"] or _DATE_MIN)

    all_test_entries: dict[str, list[dict]] = {}

    for dd in dated_docs:
        doc = dd["doc"]
        doc_id = doc.get("doc_id") or doc.get("session_id", "unknown")
        tests_index = doc.get("tests_index", {})

        for key, test in tests_index.items():
            entry = {
                "value": test.get("value"),
                "units": test.get("units"),
                "reference_range": test.get("reference_range"),
                "interpretation": test.get("interpretation"),
                "category": test.get("category"),
                "test_name": test.get("test_name"),
                "effective_date": dd["effective_date"],
                "date_confidence": dd["date_confidence"],
                "source_doc_id": doc_id,
            }
            all_test_entries.setdefault(key, []).append(entry)

    aggregated_tests: dict[str, dict] = {}
    conflicts: list[dict] = []

    for key, entries in all_test_entries.items():
        # Sort descending by date (latest first; None dates last)
        entries.sort(
            key=lambda e: e["effective_date"] or _DATE_MIN,
            reverse=True,
        )

        latest = entries[0]
        previous = entries[1] if len(entries) > 1 else None

        if (
            previous
            and latest["effective_date"]
            and previous["effective_date"]
            and latest["effective_date"].date() == previous["effective_date"].date()
        ):
            try:
                v1 = float(str(latest["value"]))
                v2 = float(str(previous["value"]))
                res = _resolve_conflict(v1, v2, latest["units"], previous["units"])

                if res["resolution"] == "conflict":
                    conflicts.append({
                        "test_key": key,
                        "date": latest["effective_date"].isoformat(),
                        "values": [
                            {"value": v1, "doc_id": latest["source_doc_id"]},
                            {"value": v2, "doc_id": previous["source_doc_id"]},
                        ],
                        "resolution": "unresolved",
                        "reason": res.get("reason", ""),
                    })
                elif res["resolution"] == "averaged":
                    # Mutate latest with averaged value
                    latest = dict(latest)
                    latest["value"] = res["value"]
                    # Shift previous to next entry
                    previous = entries[2] if len(entries) > 2 else None
            except (ValueError, TypeError):
                pass

        trend = None
        if previous:
            trend = _compute_trend(
                latest.get("interpretation"),
                previous.get("interpretation"),
            )

        aggregated_tests[key] = {
            "test_name": latest.get("test_name"),
            "current_value": latest.get("value"),
            "current_date": (
                latest["effective_date"].isoformat()
                if latest["effective_date"] else None
            ),
            "current_interpretation": latest.get("interpretation"),
            "units": latest.get("units"),
            "reference_range": latest.get("reference_range"),
            "reference_range_source_doc_id": latest.get("source_doc_id"),
            "category": latest.get("category"),
            "trend": trend,
            "source_doc_id": latest.get("source_doc_id"),
            "previous_value": previous.get("value") if previous else None,
            "previous_date": (
                previous["effective_date"].isoformat()
                if previous and previous.get("effective_date") else None
            ),
            "previous_interpretation": (
                previous.get("interpretation") if previous else None
            ),
            "history": [
                {
                    "value": e["value"],
                    "date": (
                        e["effective_date"].isoformat()
                        if e["effective_date"] else None
                    ),
                    "interpretation": e["interpretation"],
                    "doc_id": e["source_doc_id"],
                }
                for e in entries
            ],
        }

    chronic_flags = _detect_chronic_conditions(all_test_entries)

    patient_info = _merge_patient_info(dated_docs)

    aggregated_abnormal = _aggregate_abnormal_findings(aggregated_tests)

    has_failures = any(
        d["doc"].get("status") == "failed" for d in dated_docs
    )
    if has_failures:
        agg_status = "partial"
    elif conflicts:
        agg_status = "conflict_present"
    else:
        agg_status = "complete"

    bmi = None
    for dd in reversed(dated_docs):
        doc_bmi = dd["doc"].get("bmi")
        if doc_bmi:
            bmi = doc_bmi
            break

    logger.info(
        "Aggregation complete: %d tests, %d conflicts, %d chronic flags, status=%s",
        len(aggregated_tests), len(conflicts), len(chronic_flags), agg_status,
    )

    return {
        "aggregated_tests": aggregated_tests,
        "aggregated_abnormal_findings": aggregated_abnormal,
        "chronic_flags": chronic_flags,
        "conflicts": conflicts,
        "aggregation_status": agg_status,
        "patient_information": patient_info,
        "bmi": bmi,
    }
