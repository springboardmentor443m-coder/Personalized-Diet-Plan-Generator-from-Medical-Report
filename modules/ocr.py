"""Vision-model OCR with parallel page processing and retry logic."""

import base64
import io
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from PIL import Image
from groq import Groq

from config.settings import (
    GROQ_API_KEY,
    OCR_VISION_MODEL,
    OCR_VISION_MODEL_FALLBACK,
    MAX_OCR_WORKERS,
    MAX_OCR_RETRIES,
    IMAGE_ENCODE_FORMAT,
    IMAGE_ENCODE_QUALITY,
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


OCR_PROMPT = (
    "Act as an expert OCR engine. "
    "Transcribe the provided medical report image into highly accurate Markdown.\n"
    "- Preserve all tables using Markdown table syntax.\n"
    "- Maintain the visual hierarchy (headings, sub-headings).\n"
    "- Do not summarize; transcribe every word, including small print and legal clauses.\n"
    "- Return ONLY the transcription."
)


def _encode_image(image: Image.Image) -> str:
    """Encode a PIL image to a base64 data-URI string."""
    buffer = io.BytesIO()

    if image.mode != "RGB":
        image = image.convert("RGB")

    fmt = IMAGE_ENCODE_FORMAT.upper()
    save_kwargs: dict = {"format": fmt}
    if fmt == "JPEG":
        save_kwargs["quality"] = IMAGE_ENCODE_QUALITY

    image.save(buffer, **save_kwargs)

    b64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
    mime = "image/jpeg" if fmt == "JPEG" else "image/png"
    return f"data:{mime};base64,{b64}"


def _ocr_single_page(
    client: Groq,
    image: Image.Image,
    page_num: int,
) -> str:
    """Run OCR on a single page image with retry + model fallback."""
    data_uri = _encode_image(image)
    models = [OCR_VISION_MODEL] * min(2, MAX_OCR_RETRIES) + [
        OCR_VISION_MODEL_FALLBACK
    ] * max(0, MAX_OCR_RETRIES - 1)
    # Ensure at least one attempt
    models = models[:MAX_OCR_RETRIES] if models else [OCR_VISION_MODEL]

    last_exc: Exception | None = None

    for attempt, model in enumerate(models, start=1):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": OCR_PROMPT},
                            {
                                "type": "image_url",
                                "image_url": {"url": data_uri},
                            },
                        ],
                    }
                ],
                temperature=0.0,
                max_completion_tokens=4096,
            )
            text = response.choices[0].message.content or ""
            logger.info(
                "OCR page %d OK (attempt %d, model=%s, %d chars)",
                page_num, attempt, model, len(text),
            )
            return text.strip()

        except Exception as exc:
            last_exc = exc
            if _is_rate_limit_error(exc):
                wait = RATE_LIMIT_RETRY_DELAY_SECONDS
                logger.warning(
                    "Rate-limit hit on page %d (attempt %d), waiting %.1fs",
                    page_num, attempt, wait,
                )
            else:
                wait = 0.5 * attempt
                logger.warning(
                    "OCR page %d failed (attempt %d, model=%s): %s",
                    page_num, attempt, model, exc,
                )
            time.sleep(wait)

    raise RuntimeError(
        f"OCR failed on page {page_num} after {MAX_OCR_RETRIES} attempts: {last_exc}"
    )


def run_ocr(images: list[Image.Image]) -> str:
    """Run OCR on a list of PIL images, returning concatenated Markdown."""
    if not GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY is not configured. Cannot perform OCR.")

    client = Groq(api_key=GROQ_API_KEY)
    n_pages = len(images)

    if n_pages == 1:
        text = _ocr_single_page(client, images[0], page_num=1)
        return f"\n--- PAGE 1 ---\n{text}"

    # Multi-page — parallel OCR
    workers = min(MAX_OCR_WORKERS, n_pages)
    logger.info("Starting parallel OCR: %d pages, %d workers", n_pages, workers)

    page_texts: dict[int, str] = {}

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(_ocr_single_page, client, img, idx): idx
            for idx, img in enumerate(images, start=1)
        }
        for future in as_completed(futures):
            page_idx = futures[future]
            page_texts[page_idx] = future.result()  # propagates exceptions

    chunks: list[str] = []
    for i in sorted(page_texts.keys()):
        chunks.append(f"\n--- PAGE {i} ---\n{page_texts[i]}")

    combined = "".join(chunks)
    logger.info("OCR complete: %d page(s), %d total chars", n_pages, len(combined))
    return combined
