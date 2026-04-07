# tenders/services/pdf_processor.py
"""
Extracts text from uploaded tender PDF files using pdfplumber.
Handles large PDFs, text cleaning, and chunking.
"""

import logging
import re

import pdfplumber

logger = logging.getLogger(__name__)

# Maximum characters to send to OpenAI (~30k tokens)
MAX_TEXT_LENGTH = 60_000


def extract_text_from_file(file_path: str) -> str:
    """
    Extract and clean text from a local PDF file.

    Args:
        file_path: Absolute path to the PDF file on disk.

    Returns:
        Cleaned text string ready for AI summarization.

    Raises:
        ValueError: If no text could be extracted.
        RuntimeError: If the PDF cannot be parsed.
    """
    text_parts = []

    try:
        with pdfplumber.open(file_path) as pdf:
            total_pages = len(pdf.pages)
            logger.info("PDF has %d pages: %s", total_pages, file_path)

            for i, page in enumerate(pdf.pages):
                try:
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)
                except Exception as e:
                    logger.warning("Failed to extract text from page %d: %s", i + 1, e)
                    continue

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
