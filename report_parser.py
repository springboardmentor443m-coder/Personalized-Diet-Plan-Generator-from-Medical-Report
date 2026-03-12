#report_parser.py
import os
import io
import json
import base64
from pathlib import Path
from typing import Dict, List, Optional
from PIL import Image
import pypdfium2 as pdfium
from concurrent.futures import ThreadPoolExecutor, as_completed
from groq import Groq
from dotenv import load_dotenv
import re
from datetime import datetime

# Load environment configuration
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

STRUCTURED_EXTRACTION_PROMPT = """You are a medical data extraction system. Analyze the following lab report markdown and extract structured information according to the JSON schema below.

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

class MedicalDocumentProcessor:
    """
    AI-NutriCare Medical Document Processor
    Extracts structured patient data and lab results from medical reports
    """
    
    def __init__(self, max_workers: int = 3):
        self.max_workers = max_workers
        self.supported_formats = ['.pdf', '.png', '.jpg', '.jpeg', '.tiff', '.bmp']
        
    def load_pdf_document(self, file_path: str) -> List[Image.Image]:
        """
        Convert PDF pages to PIL Images using pypdfium2
        """
        images = []
        try:
            pdf_document = pdfium.PdfDocument(file_path)
            for page_number in range(len(pdf_document)):
                page = pdf_document[page_number]
                
                # Render page to bitmap
                bitmap = page.render(scale=2.0)  # Higher scale for better OCR
                
                # Convert to PIL Image
                pil_image = bitmap.to_pil()
                images.append(pil_image)
                
            print(f"✅ Loaded {len(images)} pages from PDF")
        except Exception as e:
            print(f"❌ PDF loading error: {e}")
            
        return images
    
    def load_image_file(self, file_path: str) -> List[Image.Image]:
        """
        Load single image file
        """
        try:
            image = Image.open(file_path)
            return [image]
        except Exception as e:
            print(f"❌ Image loading error: {e}")
            return []
    
    def encode_image_to_base64(self, image: Image.Image) -> str:
        """
        Convert PIL Image to base64 string for API transmission
        """
        try:
            # Convert to RGB if necessary
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Resize if too large (API limits)
            max_size = 2000
            if max(image.size) > max_size:
                ratio = max_size / max(image.size)
                new_size = tuple(int(dim * ratio) for dim in image.size)
                image = image.resize(new_size, Image.Resampling.LANCZOS)
            
            # Save to bytes
            buffer = io.BytesIO()
            image.save(buffer, format='JPEG', quality=85)
            buffer.seek(0)
            
            # Encode to base64
            encoded = base64.b64encode(buffer.getvalue()).decode('utf-8')
            return encoded
            
        except Exception as e:
            print(f"❌ Image encoding error: {e}")
            return ""
    
    def extract_text_from_image(self, image: Image.Image) -> str:
        """
        Use Groq Llama Vision API to extract text from image
        """
        try:
            # Encode image
            base64_image = self.encode_image_to_base64(image)
            
            if not base64_image:
                return ""
            
            # Call Groq Vision API
            response = groq_client.chat.completions.create(
                model="llama-3.2-11b-vision-preview",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": VISION_OCR_PROMPT},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                temperature=0.1,
                max_tokens=2048
            )
            
            extracted_text = response.choices[0].message.content
            return extracted_text
            
        except Exception as e:
            print(f"❌ Vision API error: {e}")
            return ""
    
    def process_single_page(self, image: Image.Image, page_num: int) -> Dict:
        """
        Process a single page and return extracted text
        """
        print(f"📄 Processing page {page_num + 1}...")
        extracted_text = self.extract_text_from_image(image)
        
        return {
            "page_number": page_num + 1,
            "text_content": extracted_text,
            "status": "success" if extracted_text else "failed"
        }
    
    def extract_structured_data(self, full_text: str) -> Dict:
        """
        Send extracted text to LLM for structured JSON extraction
        """
        try:
            complete_prompt = STRUCTURED_EXTRACTION_PROMPT + "\n\nREPORT TEXT:\n" + full_text
            
            response = groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": "You output only valid JSON without any additional text."},
                    {"role": "user", "content": complete_prompt}
                ],
                temperature=0.0,
                max_tokens=8000
            )
            
            json_response = response.choices[0].message.content
            
            # Clean and parse JSON
            cleaned = re.sub(r"```json\s*|\s*```", "", json_response).strip()
            start = cleaned.find("{")
            end = cleaned.rfind("}")
            
            if start != -1 and end != -1:
                json_str = cleaned[start:end+1]
                # Fix trailing commas
                json_str = re.sub(r",\s*}", "}", json_str)
                json_str = re.sub(r",\s*]", "]", json_str)
                
                return json.loads(json_str)
            else:
                return {"error": "No valid JSON found", "raw_output": json_response}
                
        except json.JSONDecodeError as e:
            return {"error": f"JSON parsing failed: {str(e)}", "raw_output": json_response}
        except Exception as e:
            return {"error": f"LLM processing error: {str(e)}"}
    
    def process_document(self, file_path: str) -> Dict:
        """
        Main pipeline: Load document, extract text, structure data
        """
        print(f"\n🔍 Processing document: {file_path}")
        
        # Step 1: Check file exists
        if not os.path.exists(file_path):
            return {"error": f"File not found: {file_path}"}
        
        # Step 2: Load document based on extension
        file_ext = Path(file_path).suffix.lower()
        
        if file_ext not in self.supported_formats:
            return {"error": f"Unsupported format: {file_ext}. Supported: {self.supported_formats}"}
        
        # Load pages
        if file_ext == '.pdf':
            pages = self.load_pdf_document(file_path)
        else:
            pages = self.load_image_file(file_path)
        
        if not pages:
            return {"error": "Failed to load document pages"}
        
        # Step 3: Process pages in parallel
        print(f"🚀 Processing {len(pages)} pages with {self.max_workers} workers...")
        page_results = []
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            future_to_page = {
                executor.submit(self.process_single_page, page, i): i 
                for i, page in enumerate(pages)
            }
            
            # Collect results
            for future in as_completed(future_to_page):
                page_num = future_to_page[future]
                try:
                    result = future.result()
                    page_results.append(result)
                    print(f"✅ Page {page_num + 1} complete")
                except Exception as e:
                    print(f"❌ Page {page_num + 1} failed: {e}")
                    page_results.append({
                        "page_number": page_num + 1,
                        "text_content": "",
                        "status": "failed",
                        "error": str(e)
                    })
        
        # Sort by page number
        page_results.sort(key=lambda x: x["page_number"])
        
        # Step 4: Combine all text
        full_document_text = "\n\n--- PAGE BREAK ---\n\n".join([
            f"Page {r['page_number']}:\n{r['text_content']}" 
            for r in page_results if r.get('text_content')
        ])
        
        if not full_document_text.strip():
            return {"error": "No text could be extracted from document"}
        
        print(f"📝 Extracted {len(full_document_text)} characters total")
        
        # Step 5: Extract structured data
        print("🧠 Extracting structured data with LLM...")
        structured_data = self.extract_structured_data(full_document_text)
        
        # Step 6: Add metadata
        structured_data["_metadata"] = {
            "source_file": os.path.basename(file_path),
            "total_pages": len(pages),
            "processed_pages": len([r for r in page_results if r.get("status") == "success"]),
            "extraction_timestamp": datetime.now().isoformat(),
            "processor_version": "AI-NutriCare v1.0"
        }
        
        return structured_data
    
    def save_to_json(self, data: Dict, filename: Optional[str] = None) -> str:
        """
        Save extracted data to JSON file
        """
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)
        
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"extracted_report_{timestamp}.json"
        
        output_path = output_dir / filename
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Data saved to {output_path}")
        return str(output_path)


# -----------------------------------------------------------------------------
# CLI Entry Point
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="AI-NutriCare Medical Document Processor")
    parser.add_argument("file", help="Path to medical report (PDF or image)")
    parser.add_argument("--workers", "-w", type=int, default=3, help="Number of parallel workers")
    parser.add_argument("--output", "-o", help="Output JSON filename")
    parser.add_argument("--verbose", "-v", action="store_true", help="Print verbose output")
    
    args = parser.parse_args()
    
    # Initialize processor
    processor = MedicalDocumentProcessor(max_workers=args.workers)
    
    # Process document
    result = processor.process_document(args.file)
    
    if "error" in result:
        print(f"❌ Error: {result['error']}")
        if args.verbose and "raw_output" in result:
            print("\nRaw output:", result["raw_output"])
    else:
        # Save results
        output_file = args.output if args.output else None
        saved_path = processor.save_to_json(result, output_file)
        
        # Print summary
        print("\n" + "="*50)
        print("✅ EXTRACTION COMPLETE")
        print("="*50)
        
        if "patient_data" in result:
            patient = result["patient_data"]
            print(f"Patient: {patient.get('full_name', 'Unknown')}")
            print(f"Age: {patient.get('age_value', 'Unknown')}")
            print(f"Gender: {patient.get('gender', 'Unknown')}")
        
        if "lab_results" in result:
            print(f"Tests extracted: {len(result['lab_results'])}")
        
        if "abnormal_results" in result:
            print(f"Abnormal findings: {len(result['abnormal_results'])}")
        
        print(f"\n📁 Saved to: {saved_path}")