import json
from groq import Groq
from backend.config import settings

# Initialize Groq client
client = Groq(api_key=settings.GROQ_API_KEY)

# --- EXTRACTION PROMPT ---
# This is the "brain" of the extraction process.
# We are forcing the LLM to act as a database converter.
# It takes the messy OCR text and reorganizes it into a strict JSON format.
# This schema is critical because the Frontend expects data in exactly this shape.
EXTRACTION_PROMPT = """You are a medical document information extraction system.

You are given the FULL OCR text of a diagnostic lab report.
Extract structured information and return ONLY valid JSON in the exact schema below.

====================
REQUIRED OUTPUT SCHEMA
====================
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
    "complete_blood_count": [ "<canonical_test_key>", ... ],
    "liver_function": [ "<canonical_test_key>", ... ],
    "kidney_function": [ "<canonical_test_key>", ... ],
    "lipid_profile": [ "<canonical_test_key>", ... ],
    "thyroid_profile": [ "<canonical_test_key>", ... ],
    "diabetes_related": [ "<canonical_test_key>", ... ],
    "vitamins_and_minerals": [ "<canonical_test_key>", ... ],
    "electrolytes": [ "<canonical_test_key>", ... ],
    "other_tests": [ "<canonical_test_key>", ... ]
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
    "total_pages": number,
    "page_numbers_detected": [ number ],
    "report_end_marker_present": boolean
  }
}

====================
CANONICAL TEST KEY RULES
====================
- Each test MUST appear exactly ONCE in `tests_index`
- Use a normalized snake_case key derived from the test name
- Remove units, methods, symbols, and punctuation
- Examples:
  - "Hemoglobin (Photometry)" → "hemoglobin"
  - "Calcium, Total (Arsenazo III)" → "calcium_total"
  - "HbA1c" → "hba1c"
  - "Vitamin D, 25 - Hydroxy, Serum" → "vitamin_d_25_hydroxy"
- The same canonical key MUST be used everywhere

====================
INTERPRETATION RULES
====================
- Determine interpretation using reference ranges when available
- If value < lower bound → "low"
- If value > upper bound → "high"
- If borderline per report text → "borderline"
- Otherwise → "normal"

====================
STRICT RULES
====================
- Return ONLY valid JSON
- No explanations
- No markdown
- No comments
- No duplicated tests
- If information is missing, use null
- units need to be taken from reference range if mentioned or else search for it 
"""


def extract_structured_data(markdown_text: str) -> dict:
    """
    Extract structured data from OCR markdown text.
    
    1. We send the raw Markdown (from OCR) to the Llama 3 (70B) model.
    2. We use 'response_format={"type": "json_object"}' to ensure the AI 
       doesn't write sentences like "Here is your JSON...", but gives purely machine-readable code.
    3. We convert that text response into a Python Dictionary.
    """
    response = client.chat.completions.create(
        model=settings.EXTRACTION_MODEL, # Using a smart model (Llama-3-70b) for logic
        response_format={"type": "json_object"}, # Forces Valid JSON output
        messages=[
            {
                "role": "system",
                "content": "You extract structured medical data from lab reports."
            },
            {
                "role": "user",
                "content": f"{EXTRACTION_PROMPT}\n\nLAB REPORT TEXT:\n{markdown_text}"
            }
        ],
        temperature=0.1 # Low temperature = factual, consistent answers (no creativity)
    )
    
    # --- Parse the Response ---
    try:
        # The AI returns a string, so we must parse it into a real Python dictionary
        structured_output = json.loads(response.choices[0].message.content)
        return structured_output
    except json.JSONDecodeError as e:
        # If the AI hallucinates and returns bad JSON, we catch the error here
        raise ValueError(f"Failed to parse structured data: {e}")