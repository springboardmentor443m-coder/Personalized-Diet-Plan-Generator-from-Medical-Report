from pathlib import Path
from typing import List
from PIL import Image
import pypdfium2 as pdfium
import io
import base64
from groq import Groq
from backend.config import settings

# Initialize the Groq client with the API key
client = Groq(api_key=settings.GROQ_API_KEY)

# --- OCR PROMPT ---
# This instruction tells the AI vision model exactly how to behave.
# We want it to act like a scanner that outputs Markdown text instead of just summarizing.
OCR_PROMPT = """
Act as an expert OCR engine. Transcribe the provided image into highly accurate Markdown.
- Preserve all tables using Markdown table syntax.
- Maintain the visual hierarchy (headings, sub-headings).
- Do not summarize; transcribe every word, including small print and legal clauses.
- Return ONLY the transcription.
"""

def load_document(file_path: str) -> List[Image.Image]:
    """
    Load document and convert to a list of PIL images.
    - If it's a PDF, we convert each page into a high-quality image.
    - If it's already an image (JPG/PNG), we just open it.
    """
    ext = Path(file_path).suffix.lower()

    # --- Case 1: Handle PDF Files ---
    if ext == ".pdf":
        pdf = pdfium.PdfDocument(file_path)
        images = []
        
        # Loop through every page in the PDF
        for i in range(len(pdf)):
            page = pdf[i]
            # Render the page to a bitmap (picture) at 300 DPI for clarity
            page_bitmap = page.render(scale=300/72, rotation=0)
            pil_image = page_bitmap.to_pil()
            images.append(pil_image)
            page.close()
        
        return images

    # --- Case 2: Handle Image Files ---
    if ext in [".jpg", ".jpeg", ".png"]:
        return [Image.open(file_path)]

    # If it's not a PDF or Image, stop here.
    raise ValueError(f"Unsupported file type: {ext}")


def encode_pil_image(image: Image.Image) -> str:
    """
    Encode a PIL image to a base64 string.
    LLMs (like Llama Vision) cannot 'see' a file on your hard drive.
    They need the image converted into a long text string (base64).
    """
    buffer = io.BytesIO()
    
    # Convert to RGB (remove transparency) because JPEG doesn't support transparency
    if image.mode != 'RGB':
        image = image.convert('RGB')
    
    # Save image to memory buffer as a high-quality JPEG
    image.save(buffer, format="JPEG", quality=95)
    
    # Convert binary data -> Base64 String -> UTF-8 String
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


def get_markdown_from_page(image: Image.Image) -> str:
    """
    Send a single page image to Groq's Vision Model (Llama 3.2 Vision)
    and get back the text transcription.
    """
    # 1. Convert image to string format
    base64_image = encode_pil_image(image)
    
    # 2. Call the AI API
    response = client.chat.completions.create(
        model=settings.OCR_MODEL, # e.g., "llama-3.2-11b-vision-preview"
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": OCR_PROMPT}, # The instructions
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"} # The image data
                    }
                ]
            }
        ],
    )
    # 3. Return only the text content
    return response.choices[0].message.content


def process_document(file_path: str) -> str:
    """
    Main function to process the entire document.
    1. Loads the file (converts PDF -> Images if needed).
    2. Loops through every page.
    3. Sends each page to the AI to be read.
    4. Stitches all the text together into one big string.
    """
    images = load_document(file_path)
    markdown_pages = []
    
    for i, image in enumerate(images):
        print(f"Processing page {i+1}/{len(images)}...")
        
        # Perform OCR on this specific page
        markdown_text = get_markdown_from_page(image)
        
        # Add a clear separator between pages
        markdown_pages.append(f"--- Page {i+1} ---\n{markdown_text}")
    
    # Join all pages with double newlines
    return "\n\n".join(markdown_pages)