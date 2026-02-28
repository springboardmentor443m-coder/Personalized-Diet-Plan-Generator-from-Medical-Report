"""Convert PDF and image files to a list of RGB PIL images.

Supports both file-path and in-memory (bytes) inputs so that the
pipeline can operate without persisting uploads to disk.
"""

from __future__ import annotations

import io
import logging
from pathlib import Path

from PIL import Image
import pypdfium2 as pdfium

logger = logging.getLogger(__name__)

# Render PDFs at 300 DPI for high‑quality OCR
_PDF_RENDER_SCALE = 300 / 72  # scale factor: target_dpi / base_dpi


# ── public API ──────────────────────────────────────────────────────

def convert_to_images(file_path: str) -> list[Image.Image]:
    """Convert a file on disk (PDF or image) to a list of RGB PIL images."""
    path = Path(file_path)
    ext = path.suffix.lower()

    if ext == ".pdf":
        return _pdf_to_images_from_path(path)
    elif ext in {".jpg", ".jpeg", ".png"}:
        img = Image.open(path)
        if img.mode != "RGB":
            img = img.convert("RGB")
        logger.info("Loaded image: %s (%dx%d)", path.name, img.width, img.height)
        return [img]
    else:
        raise ValueError(f"Unsupported file type: {ext}")


def convert_bytes_to_images(content: bytes, ext: str) -> list[Image.Image]:
    """Convert raw file bytes to a list of RGB PIL images (no disk I/O).

    Parameters
    ----------
    content : bytes
        The raw file content.
    ext : str
        Lowercase file extension including the dot, e.g. ``".pdf"``.
    """
    if ext == ".pdf":
        return _pdf_to_images_from_bytes(content)
    elif ext in {".jpg", ".jpeg", ".png"}:
        img = Image.open(io.BytesIO(content))
        if img.mode != "RGB":
            img = img.convert("RGB")
        logger.info("Loaded image from bytes (%dx%d)", img.width, img.height)
        return [img]
    else:
        raise ValueError(f"Unsupported file type: {ext}")


# ── internal helpers ────────────────────────────────────────────────

def _pdf_to_images_from_path(pdf_path: Path) -> list[Image.Image]:
    """Render each page of a PDF file to an RGB PIL image at 300 DPI."""
    images: list[Image.Image] = []
    pdf = None

    try:
        pdf = pdfium.PdfDocument(str(pdf_path))
        n_pages = len(pdf)
        logger.info("PDF loaded: %s (%d page(s))", pdf_path.name, n_pages)

        for page_index in range(n_pages):
            page = pdf[page_index]
            bitmap = page.render(scale=_PDF_RENDER_SCALE, rotation=0)
            pil_image = bitmap.to_pil().convert("RGB")
            images.append(pil_image)
            page.close()

    except Exception as exc:
        raise RuntimeError(f"Failed to render PDF page(s): {exc}") from exc
    finally:
        if pdf is not None:
            pdf.close()

    if not images:
        raise RuntimeError("PDF contains no renderable pages.")

    return images


def _pdf_to_images_from_bytes(content: bytes) -> list[Image.Image]:
    """Render each page of an in-memory PDF to an RGB PIL image at 300 DPI."""
    images: list[Image.Image] = []
    pdf = None

    try:
        pdf = pdfium.PdfDocument(content)
        n_pages = len(pdf)
        logger.info("PDF loaded from bytes (%d page(s))", n_pages)

        for page_index in range(n_pages):
            page = pdf[page_index]
            bitmap = page.render(scale=_PDF_RENDER_SCALE, rotation=0)
            pil_image = bitmap.to_pil().convert("RGB")
            images.append(pil_image)
            page.close()

    except Exception as exc:
        raise RuntimeError(f"Failed to render PDF page(s): {exc}") from exc
    finally:
        if pdf is not None:
            pdf.close()

    if not images:
        raise RuntimeError("PDF contains no renderable pages.")

    return images
