EXTRACTION_PROMPT = """
You are a medical data extraction assistant specializing in clinical pathology.
Extract the patient name, age, gender, weight, height, and all medical tests from the following lab report.

For each test:
1. Extract the test name, numerical value, units, and reference range.
2. Compare the value to the reference range.
3. Assign an interpretation: 'normal', 'low', 'high', or 'critical'.

Return the result strictly as a JSON object with this structure:
{
  "patient_information": {
    "patient_name": "...",
    "age_years": 0,
    "gender": "...",
    "weight_kg": 0,
    "height_cm": 0
  },
  "tests_index": {
    "test_key": {
      "test_name": "...",
      "value": "...",
      "units": "...",
      "reference_range": "...",
      "interpretation": "..."
    }
  },
  "tests_by_category": {
    "category_name": ["test_key1", "test_key2"]
  },
  "abnormal_findings": [
    {
      "canonical_test_key": "test_key",
      "observed_value": "...",
      "expected_range": "...",
      "severity": "high/low/critical",
      "insight": "Short clinical reason why this is flagged."
    }
  ]
}

CRITICAL: If a value is outside the reference range, it MUST be included in 'abnormal_findings'.
Return ONLY valid JSON.
"""
