"""
core/ocr.py
Steps 1-3: File loading → OCR (Llama 4 Scout Vision) → JSON Extraction (Kimi K2)
All logic ported from your experiment notebook.
"""

import os
import io
import json
import base64
from pathlib import Path
from typing import List, Dict
from concurrent.futures import ThreadPoolExecutor

from PIL import Image
from groq import Groq
import pypdfium2 as pdfium

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# ── OCR Prompt ────────────────────────────────────────────────────────────────
OCR_PROMPT = """Act as an expert OCR engine. Transcribe the provided image into highly accurate Markdown.
- Preserve all tables using Markdown table syntax.
- Maintain the visual hierarchy (headings, sub-headings).
- Do not summarize; transcribe every word, including small print and legal clauses.
- Return ONLY the transcription."""

# ── Extraction Prompt ─────────────────────────────────────────────────────────
EXTRACTION_PROMPT = """You are a medical document information extraction system.
You are given the FULL OCR text of a diagnostic lab report.
Extract structured information and return ONLY valid JSON in the exact schema below.

====================
REQUIRED OUTPUT SCHEMA
====================
{
  "patient_information": {
    "patient_name": "string | null",
    "age_years": "number | null",
    "gender": "string | null",
    "lab_number": "string | null",
    "report_status": "string | null",
    "collection_datetime": "string | null",
    "report_datetime": "string | null",
    "laboratory_name": "string | null"
  },
  "tests_index": {
    "<canonical_test_key>": {
      "test_name": "string",
      "value": "number | string | null",
      "units": "string | null",
      "reference_range": "string | null",
      "interpretation": "low | normal | high | borderline | null",
      "category": "string"
    }
  },
  "tests_by_category": {
    "complete_blood_count": [],
    "liver_function": [],
    "kidney_function": [],
    "lipid_profile": [],
    "thyroid_profile": [],
    "diabetes_related": [],
    "vitamins_and_minerals": [],
    "electrolytes": [],
    "other_tests": []
  },
  "abnormal_findings": [
    {
      "canonical_test_key": "string",
      "observed_value": "number | string",
      "expected_range": "string",
      "severity": "low | high | critical"
    }
  ],
  "clinical_notes": {
    "interpretations": [],
    "comments": [],
    "notes": [],
    "recommendations": [],
    "disclaimers": []
  },
  "metadata": {
    "total_pages": "number",
    "page_numbers_detected": [],
    "report_end_marker_present": "boolean"
  }
}

====================
CANONICAL TEST KEY RULES
====================
- Each test MUST appear exactly ONCE in tests_index
- Use a normalized snake_case key (e.g. "Hemoglobin (Photometry)" → "hemoglobin")
- The same canonical key MUST be used everywhere

====================
INTERPRETATION RULES
====================
- value < lower bound → "low"
- value > upper bound → "high"
- borderline per report text → "borderline"
- otherwise → "normal"

====================
STRICT RULES
====================
- Return ONLY valid JSON
- No explanations, no markdown, no comments
- No duplicated tests
- If information is missing, use null
- Units should be taken from reference range if mentioned"""


def load_document(file_path: str) -> List[Image.Image]:
    """Load PDF or image file and return list of PIL images."""
    ext = Path(file_path).suffix.lower()

    if ext == ".pdf":
        pdf    = pdfium.PdfDocument(file_path)
        images = []
        for i in range(len(pdf)):
            page        = pdf[i]
            page_bitmap = page.render(scale=300 / 72, rotation=0)
            images.append(page_bitmap.to_pil())
            page.close()
        return images

    if ext in [".jpg", ".jpeg", ".png"]:
        return [Image.open(file_path)]

    raise ValueError(f"Unsupported file type: {ext}")


def encode_pil_image(image: Image.Image) -> str:
    """Convert PIL image to base64 JPEG string."""
    buffer = io.BytesIO()
    if image.mode != "RGB":
        image = image.convert("RGB")
    image.save(buffer, format="JPEG", quality=95)
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


def get_markdown_from_page(image: Image.Image) -> str:
    """Run OCR on a single page image using Llama 4 Scout Vision."""
    b64 = encode_pil_image(image)
    response = client.chat.completions.create(
        model="meta-llama/llama-4-scout-17b-16e-instruct",
        messages=[{
            "role": "user",
            "content": [
                {"type": "text",      "text": OCR_PROMPT},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
            ],
        }],
    )
    return response.choices[0].message.content


def extract_fields_from_full_text(markdown: str) -> Dict:
    """Extract structured JSON from combined OCR markdown using Kimi K2."""
    response = client.chat.completions.create(
        model="moonshotai/kimi-k2-instruct",
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": "You are a medical report analyser. Return valid JSON only."},
            {"role": "user",   "content": f"{EXTRACTION_PROMPT}\n\nReport Text:\n{markdown}"},
        ],
    )
    content = response.choices[0].message.content
    content = content.replace("```json", "").replace("```", "").strip()
    return json.loads(content)


def process_document(file_path: str) -> Dict:
    """
    Full pipeline: file → images → parallel OCR → extraction → structured JSON.
    Mirrors process_document_with_llm_ocr_v2 from your notebook.
    """
    images  = load_document(file_path)
    workers = min(8, len(images))

    # Parallel OCR
    with ThreadPoolExecutor(max_workers=workers) as executor:
        page_texts = list(executor.map(get_markdown_from_page, images))

    # Combine pages
    chunks = [f"\n--- PAGE {i+1} ---\n{text}" for i, text in enumerate(page_texts)]
    full_markdown = "".join(chunks)

    # Extract JSON
    return extract_fields_from_full_text(full_markdown)
