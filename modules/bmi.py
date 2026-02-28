"""BMI calculation from extracted lab data."""

import logging
import re

logger = logging.getLogger(__name__)

_BMI_CATEGORIES = [
    (18.5, "Underweight"),
    (25.0, "Normal"),
    (30.0, "Overweight"),
    (float("inf"), "Obese"),
]


def _classify(bmi: float) -> str:
    """Return the WHO BMI category string."""
    for threshold, label in _BMI_CATEGORIES:
        if bmi < threshold:
            return label
    return "Obese"


def _extract_numeric(value) -> float | None:
    """Pull the first decimal/integer number from a value (str, int, or float)."""
    if isinstance(value, (int, float)):
        return float(value)
    match = re.search(r"(\d+\.?\d*)", str(value))
    return float(match.group(1)) if match else None


def _find_in_tests_index(tests_index: dict, keywords: list[str]) -> tuple[float | None, str]:
    """Search the tests_index dict for a measurement matching any keyword."""
    for key, test in tests_index.items():
        name = (test.get("test_name") or key).lower()
        if any(kw in name for kw in keywords) or any(kw in key.lower() for kw in keywords):
            val = _extract_numeric(test.get("value"))
            unit = test.get("units") or test.get("unit") or ""
            if val is not None:
                return val, unit
    return None, ""


def _find_in_tests_list(tests: list[dict], keywords: list[str]) -> tuple[float | None, str]:
    """Fallback: search a flat tests[] list for a measurement."""
    for test in tests:
        name = test.get("test_name", "").lower()
        if any(kw in name for kw in keywords):
            val = _extract_numeric(test.get("value", ""))
            unit = test.get("units") or test.get("unit") or ""
            if val is not None:
                return val, unit
    return None, ""


def _normalise_height_to_meters(value: float, unit_hint: str = "") -> float:
    """Convert height to metres using unit hints and heuristics."""
    hint = unit_hint.lower()
    if "cm" in hint or value > 100:
        return value / 100.0
    if "in" in hint and "interp" not in hint:
        return value * 0.0254
    if "ft" in hint or "feet" in hint or (3 <= value <= 10):
        return value * 0.3048
    return value  # assume metres


def calculate_bmi(structured_data: dict) -> dict | None:
    """Calculate BMI from extracted report data."""
    height_keywords = ["height", "stature"]
    weight_keywords = ["weight", "body_weight"]

    tests_index = structured_data.get("tests_index", {})
    tests_list = structured_data.get("tests", [])

    weight_kg, _ = _find_in_tests_index(tests_index, weight_keywords)
    height_raw, height_unit = _find_in_tests_index(tests_index, height_keywords)

    if weight_kg is None:
        weight_kg, _ = _find_in_tests_list(tests_list, weight_keywords)
    if height_raw is None:
        height_raw, height_unit = _find_in_tests_list(tests_list, height_keywords)

    if weight_kg is None or height_raw is None:
        logger.info("Height and/or weight not found — skipping BMI calculation.")
        return None

    height_m = _normalise_height_to_meters(height_raw, height_unit)

    if height_m <= 0:
        logger.warning("Invalid height value after conversion: %s", height_m)
        return None

    bmi_value = round(weight_kg / (height_m ** 2), 2)
    category = _classify(bmi_value)

    logger.info("BMI calculated: %.2f (%s)  [weight=%.1f kg, height=%.2f m]",
                bmi_value, category, weight_kg, height_m)
    return {"bmi_value": bmi_value, "category": category}
