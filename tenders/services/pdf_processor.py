# tenders/services/pdf_processor.py
"""
Extracts text from uploaded tender PDF files using pdfplumber.
Handles large PDFs, text cleaning, and chunking.
Works with both local file paths and Django FieldFile objects (cloud storage).
"""

import io
import logging
import re

import pdfplumber

logger = logging.getLogger(__name__)

# Maximum characters to send to OpenAI (~30k tokens)
MAX_TEXT_LENGTH = 60_000


def extract_text_from_file(file_source) -> str:
    """
    Extract and clean text from a PDF.

    Args:
        file_source: Either an absolute file path (str) or a Django FieldFile /
                     file-like object. Supports both local disk and cloud storage.

    Returns:
        Cleaned text string ready for AI summarization.

    Raises:
        ValueError: If no text could be extracted.
        RuntimeError: If the PDF cannot be parsed.
    """
    text_parts = []

    try:
        pdf_input = _resolve_pdf_input(file_source)
        with pdfplumber.open(pdf_input) as pdf:
            total_pages = len(pdf.pages)
            logger.info("PDF has %d pages", total_pages)

            for i, page in enumerate(pdf.pages):
                try:
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)
                except Exception as e:
                    logger.warning("Failed to extract text from page %d: %s", i + 1, e)
                    continue

    except (ValueError, RuntimeError):
        raise
    except Exception as e:
        raise RuntimeError(f"Failed to parse PDF: {e}")

    if not text_parts:
        raise ValueError("No text could be extracted from the PDF")

    full_text = '\n\n'.join(text_parts)
    cleaned = _clean_text(full_text)

    # Truncate if too long for the AI model
    if len(cleaned) > MAX_TEXT_LENGTH:
        logger.info(
            "Text truncated from %d to %d chars", len(cleaned), MAX_TEXT_LENGTH
        )
        cleaned = (
            cleaned[:MAX_TEXT_LENGTH]
            + "\n\n[... document truncated due to length ...]"
        )

    logger.info("Extracted %d characters of text", len(cleaned))
    return cleaned


def _resolve_pdf_input(file_source):
    """
    Convert various file source types into something pdfplumber.open() accepts.

    - str → treat as file path (local dev)
    - Django FieldFile / file-like → read bytes into BytesIO
    """
    # If it's already a plain path string, return as-is
    if isinstance(file_source, str):
        return file_source

    # Django FieldFile or any file-like object
    try:
        file_source.seek(0)
        data = file_source.read()
        return io.BytesIO(data)
    except Exception as e:
        raise RuntimeError(
            f"Cannot read PDF from file source ({type(file_source).__name__}): {e}"
        )


def _clean_text(text: str) -> str:
    """
    Clean extracted PDF text: fix encoding issues, normalize whitespace,
    remove excessive blank lines.
    """
    # Replace common encoding artifacts
    text = text.replace('\x00', '')
    text = text.replace('\ufeff', '')

    # Normalize whitespace within lines
    text = re.sub(r'[ \t]+', ' ', text)

    # Collapse excessive newlines (more than 2 consecutive)
    text = re.sub(r'\n{3,}', '\n\n', text)

    # Strip leading/trailing whitespace per line
    lines = [line.strip() for line in text.split('\n')]
    text = '\n'.join(lines)

    return text.strip()
