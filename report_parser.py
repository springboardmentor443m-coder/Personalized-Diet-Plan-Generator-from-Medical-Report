"""
report_parser.py - AI-NutriCare Medical Document Processor

Extracts structured patient data and lab results from medical reports
(PDF or image) using Groq vision + text models.
"""

import os
import io
import json
import base64
import re
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

from PIL import Image
import pypdfium2 as pdfium
from groq import Groq
from dotenv import load_dotenv

load_dotenv()
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))


# -----------------------------------------------------------------------------
# PROMPT TEMPLATES
# -----------------------------------------------------------------------------
VISION_OCR_PROMPT = """You are a medical OCR specialist. Extract ALL text visible in this laboratory report image.

Focus on:
- Patient demographics (name, age, gender, ID)
- Test names and their values
- Reference ranges and units
- Doctor's comments and interpretations
- Dates and laboratory information

Return the extracted text in clean markdown format, preserving the structure of the report.
Do not add any explanations or interpretations - just transcribe exactly what you see.
"""

STRUCTURED_EXTRACTION_PROMPT = """You are a medical data extraction system. Analyse the following lab report markdown and extract structured information according to the JSON schema below.

Return ONLY valid JSON without any additional text.

{
  "patient_data": {
    "full_name": string | null,
    "age_value": number | null,
    "gender": string | null,
    "patient_id": string | null,
    "report_date": string | null,
    "collection_date": string | null,
    "facility": string | null,
    "referring_doctor": string | null
  },
  "lab_results": {
    "<test_identifier>": {
      "test_name": string,
      "value": number | string | null,
      "unit": string | null,
      "reference_range": string | null,
      "flag": "low" | "normal" | "high" | "critical" | null,
      "category": string
    }
  },
  "test_categories": {
    "hematology": ["<test_identifier>"],
    "biochemistry": ["<test_identifier>"],
    "hormones": ["<test_identifier>"],
    "lipid_profile": ["<test_identifier>"],
    "diabetes_panel": ["<test_identifier>"],
    "renal_function": ["<test_identifier>"],
    "hepatic_function": ["<test_identifier>"],
    "electrolytes": ["<test_identifier>"],
    "other_tests": ["<test_identifier>"]
  },
  "abnormal_results": [
    {
      "test_key": string,
      "measured_value": number | string,
      "normal_interval": string,
      "severity": "mild" | "moderate" | "severe"
    }
  ],
  "clinical_notes": {
    "doctor_comments": [string],
    "interpretations": [string],
    "recommendations": [string],
    "disclaimers": [string]
  },
  "processing_info": {
    "total_pages": number,
    "processed_pages": [number],
    "extraction_timestamp": string,
    "document_type": string
  }
}

RULES:
1. Create snake_case identifiers for each test
2. Each test appears exactly once in lab_results
3. Compare values against reference ranges to determine flags
4. Include only abnormal findings in abnormal_results
5. Use null for missing values
6. Preserve numeric values as numbers, not strings
"""


# -----------------------------------------------------------------------------
# Utility: clean and parse a JSON string returned by an LLM
# Exported so app.py can import it if needed.
# -----------------------------------------------------------------------------
def clean_json(raw: str) -> dict:
    """
    Strip markdown code fences, locate the outermost JSON object,
    fix trailing commas, and return a parsed dict.
    Raises ValueError or json.JSONDecodeError on failure.
    """
    cleaned = re.sub(r"```json\s*|\s*```", "", raw).strip()
    start = cleaned.find("{")
    end   = cleaned.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("No JSON object found in LLM response")
    json_str = cleaned[start:end + 1]
    json_str = re.sub(r",\s*}", "}", json_str)
    json_str = re.sub(r",\s*]", "]", json_str)
    return json.loads(json_str)


# -----------------------------------------------------------------------------
# Medical Document Processor
# -----------------------------------------------------------------------------
class MedicalDocumentProcessor:
    """
    Extracts structured patient data and lab results from medical reports.
    Supports PDF and common image formats.
    """

    SUPPORTED_FORMATS = {".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".bmp"}

    def __init__(self, max_workers: int = 3):
        self.max_workers = max_workers

    # ------------------------------------------------------------------
    # Document loading
    # ------------------------------------------------------------------
    def load_pdf_document(self, file_path: str) -> List[Image.Image]:
        images = []
        try:
            pdf = pdfium.PdfDocument(file_path)
            for i in range(len(pdf)):
                bitmap = pdf[i].render(scale=2.0)
                images.append(bitmap.to_pil())
            print(f"✅ Loaded {len(images)} pages from PDF")
        except Exception as e:
            print(f"❌ PDF loading error: {e}")
        return images

    def load_image_file(self, file_path: str) -> List[Image.Image]:
        try:
            return [Image.open(file_path)]
        except Exception as e:
            print(f"❌ Image loading error: {e}")
            return []

    # ------------------------------------------------------------------
    # Image encoding
    # ------------------------------------------------------------------
    def encode_image_to_base64(self, image: Image.Image) -> str:
        try:
            if image.mode != "RGB":
                image = image.convert("RGB")
            max_side = 2000
            if max(image.size) > max_side:
                ratio    = max_side / max(image.size)
                new_size = tuple(int(d * ratio) for d in image.size)
                image    = image.resize(new_size, Image.Resampling.LANCZOS)
            buf = io.BytesIO()
            image.save(buf, format="JPEG", quality=85)
            return base64.b64encode(buf.getvalue()).decode("utf-8")
        except Exception as e:
            print(f"❌ Image encoding error: {e}")
            return ""

    # ------------------------------------------------------------------
    # OCR via Groq vision
    # ------------------------------------------------------------------
    def extract_text_from_image(self, image: Image.Image) -> str:
        b64 = self.encode_image_to_base64(image)
        if not b64:
            return ""
        try:
            response = groq_client.chat.completions.create(
                model="meta-llama/llama-4-scout-17b-16e-instruct",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": VISION_OCR_PROMPT},
                            {"type": "image_url",
                             "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
                        ],
                    }
                ],
                temperature=0.1,
                max_tokens=2048,
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"❌ Vision API error: {e}")
            return ""

    def process_single_page(self, image: Image.Image, page_num: int) -> dict:
        print(f"📄 Processing page {page_num + 1}...")
        text = self.extract_text_from_image(image)
        return {
            "page_number":  page_num + 1,
            "text_content": text,
            "status":       "success" if text else "failed",
        }

    # ------------------------------------------------------------------
    # Structured extraction
    # ------------------------------------------------------------------
    def extract_structured_data(self, full_text: str) -> dict:
        try:
            prompt = STRUCTURED_EXTRACTION_PROMPT + "\n\nREPORT TEXT:\n" + full_text
            response = groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": "You output only valid JSON without any additional text."},
                    {"role": "user",   "content": prompt},
                ],
                temperature=0.0,
                max_tokens=8000,
            )
            return clean_json(response.choices[0].message.content)
        except (json.JSONDecodeError, ValueError) as e:
            return {"error": f"JSON parsing failed: {str(e)}"}
        except Exception as e:
            return {"error": f"LLM processing error: {str(e)}"}

    # ------------------------------------------------------------------
    # Main pipeline
    # ------------------------------------------------------------------
    def process_document(self, file_path: str) -> dict:
        print(f"\n🔍 Processing document: {file_path}")

        if not os.path.exists(file_path):
            return {"error": f"File not found: {file_path}"}

        ext = Path(file_path).suffix.lower()
        if ext not in self.SUPPORTED_FORMATS:
            return {"error": f"Unsupported format: {ext}. Supported: {self.SUPPORTED_FORMATS}"}

        pages = self.load_pdf_document(file_path) if ext == ".pdf" else self.load_image_file(file_path)
        if not pages:
            return {"error": "Failed to load document pages"}

        print(f"🚀 Processing {len(pages)} pages with {self.max_workers} workers...")
        page_results = []

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {executor.submit(self.process_single_page, pg, i): i
                       for i, pg in enumerate(pages)}
            for future in as_completed(futures):
                idx = futures[future]
                try:
                    page_results.append(future.result())
                    print(f"✅ Page {idx + 1} complete")
                except Exception as e:
                    print(f"❌ Page {idx + 1} failed: {e}")
                    page_results.append({
                        "page_number":  idx + 1,
                        "text_content": "",
                        "status":       "failed",
                        "error":        str(e),
                    })

        page_results.sort(key=lambda x: x["page_number"])

        full_text = "\n\n--- PAGE BREAK ---\n\n".join(
            f"Page {r['page_number']}:\n{r['text_content']}"
            for r in page_results if r.get("text_content")
        )

        if not full_text.strip():
            return {"error": "No text could be extracted from document"}

        print(f"📝 Extracted {len(full_text)} characters total")
        print("🧠 Extracting structured data with LLM...")

        structured = self.extract_structured_data(full_text)

        structured["_metadata"] = {
            "source_file":          os.path.basename(file_path),
            "total_pages":          len(pages),
            "processed_pages":      len([r for r in page_results if r.get("status") == "success"]),
            "extraction_timestamp": datetime.now().isoformat(),
            "processor_version":    "AI-NutriCare v1.0",
        }
        return structured

    def save_to_json(self, data: dict, filename: Optional[str] = None) -> str:
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)

        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename  = f"extracted_report_{timestamp}.json"

        output_path = output_dir / filename
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        print(f"💾 Data saved to {output_path}")
        return str(output_path)


# -----------------------------------------------------------------------------
# CLI
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="AI-NutriCare Medical Document Processor")
    parser.add_argument("file",       help="Path to medical report (PDF or image)")
    parser.add_argument("--workers",  "-w", type=int, default=3)
    parser.add_argument("--output",   "-o", help="Output JSON filename")
    parser.add_argument("--verbose",  "-v", action="store_true")
    args = parser.parse_args()

    processor = MedicalDocumentProcessor(max_workers=args.workers)
    result    = processor.process_document(args.file)

    if "error" in result:
        print(f"❌ Error: {result['error']}")
        if args.verbose and "raw_output" in result:
            print("\nRaw output:", result["raw_output"])
    else:
        saved = processor.save_to_json(result, args.output)
        print("\n" + "=" * 50)
        print("✅ EXTRACTION COMPLETE")
        print("=" * 50)
        patient = result.get("patient_data", {})
        print(f"Patient : {patient.get('full_name', 'Unknown')}")
        print(f"Age     : {patient.get('age_value', 'Unknown')}")
        print(f"Gender  : {patient.get('gender', 'Unknown')}")
        print(f"Tests   : {len(result.get('lab_results', {}))}")
        print(f"Abnormal: {len(result.get('abnormal_results', []))}")
        print(f"Saved to: {saved}")