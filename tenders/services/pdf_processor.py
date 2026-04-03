# tenders/services/pdf_processor.py
"""
Downloads tender PDF documents and extracts text using PyPDF2.
Handles HTML tender pages (extracts PDF links), retries, User-Agent rotation,
large document chunking, and text cleaning.
"""

import io
import logging
import random
import re
import time
from urllib.parse import urljoin

import PyPDF2
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger('scrapers')

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15',
]

# Maximum characters to send to OpenAI (roughly ~30k tokens)
MAX_TEXT_LENGTH = 60000


def _get_headers():
    """Return request headers with a random User-Agent."""
    return {
        'User-Agent': random.choice(USER_AGENTS),
        'Accept': 'application/pdf,text/html,*/*',
    }


def _fetch_url(url, timeout=60, max_retries=3):
    """
    Fetch a URL with retry logic and random User-Agent.
    Returns (response_bytes, content_type).
    """
    last_error = None
    for attempt in range(1, max_retries + 1):
        try:
            headers = _get_headers()
            logger.info("Download attempt %d/%d: %s", attempt, max_retries, url[:120])
            response = requests.get(url, headers=headers, timeout=timeout)
            response.raise_for_status()

            content_type = response.headers.get('Content-Type', '').lower()
            return response.content, content_type

        except Exception as e:
            last_error = e
            logger.warning("Download attempt %d failed: %s", attempt, e)
            if attempt < max_retries:
                wait = 2 ** attempt + random.uniform(0, 1)
                time.sleep(wait)

    raise RuntimeError(
        "Failed to download after %d attempts: %s" % (max_retries, last_error)
    )


def _is_pdf_content(content_type, raw_bytes):
    """Check if the response is actually a PDF."""
    if 'pdf' in content_type or 'octet-stream' in content_type:
        return True
    # Check PDF magic bytes
    if raw_bytes[:5] == b'%PDF-':
        return True
    return False


def _extract_pdf_links_from_html(html_bytes, base_url):
    """
    Parse an HTML tender detail page and extract PDF download links.
    Returns a list of absolute PDF URLs.
    """
    try:
        soup = BeautifulSoup(html_bytes, 'lxml')
    except Exception:
        soup = BeautifulSoup(html_bytes, 'html.parser')

    pdf_links = []

    # Find all links that point to PDF files
    for a_tag in soup.find_all('a', href=True):
        href = a_tag['href'].strip()
        if href.lower().endswith('.pdf') or '/TenderDocs/' in href or '/tenderdocs/' in href.lower():
            absolute_url = urljoin(base_url, href)
            if absolute_url not in pdf_links:
                pdf_links.append(absolute_url)

    # Also check for iframes or embed tags with PDF sources
    for tag in soup.find_all(['iframe', 'embed', 'object']):
        src = tag.get('src', '') or tag.get('data', '')
        if src and ('.pdf' in src.lower() or '/TenderDocs/' in src):
            absolute_url = urljoin(base_url, src)
            if absolute_url not in pdf_links:
                pdf_links.append(absolute_url)

    logger.info("Found %d PDF link(s) on page: %s", len(pdf_links), pdf_links[:3])
    return pdf_links


def download_pdf(url, max_retries=3, timeout=60):
    """
    Download a PDF from the given URL. If the URL points to an HTML page,
    scrape it for PDF links and download the first one found.
    Returns the raw PDF bytes.
    """
    raw_bytes, content_type = _fetch_url(url, timeout=timeout, max_retries=max_retries)

    # If it's already a PDF, return directly
    if _is_pdf_content(content_type, raw_bytes):
        if len(raw_bytes) < 100:
            raise ValueError(
                "Downloaded file too small (%d bytes), likely not a valid PDF" % len(raw_bytes)
            )
        logger.info("Direct PDF downloaded: %d bytes", len(raw_bytes))
        return raw_bytes

    # It's an HTML page — extract PDF links from it
    if 'html' in content_type or raw_bytes[:15].lower().startswith((b'<!doctype', b'<html')):
        logger.info("Tender link is an HTML page, searching for PDF links...")
        pdf_links = _extract_pdf_links_from_html(raw_bytes, url)

        if not pdf_links:
            raise ValueError(
                "No PDF documents found on the tender detail page. "
                "The tender may not have an attached document."
            )

        # Download the first PDF found
        for pdf_url in pdf_links:
            try:
                logger.info("Downloading PDF from extracted link: %s", pdf_url[:120])
                pdf_bytes, pdf_ct = _fetch_url(pdf_url, timeout=timeout, max_retries=2)

                if _is_pdf_content(pdf_ct, pdf_bytes) and len(pdf_bytes) >= 100:
                    logger.info("PDF downloaded successfully: %d bytes", len(pdf_bytes))
                    return pdf_bytes
                else:
                    logger.warning("Link did not return a valid PDF: %s", pdf_url[:120])
            except Exception as e:
                logger.warning("Failed to download PDF from %s: %s", pdf_url[:80], e)
                continue

        raise RuntimeError(
            "Found %d PDF link(s) but none could be downloaded successfully" % len(pdf_links)
        )

    raise ValueError(
        "Unexpected response type '%s' — not a PDF or HTML page" % content_type
    )


def extract_text_from_pdf(pdf_bytes):
    """
    Extract text from PDF bytes using PyPDF2.
    Handles multi-page PDFs and cleans extracted text.
    """
    text_parts = []

    try:
        reader = PyPDF2.PdfReader(io.BytesIO(pdf_bytes))
        total_pages = len(reader.pages)
        logger.info("PDF has %d pages", total_pages)

        for i, page in enumerate(reader.pages):
            try:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
            except Exception as e:
                logger.warning("Failed to extract text from page %d: %s", i + 1, e)
                continue

    except Exception as e:
        raise RuntimeError("Failed to parse PDF: %s" % e)

    if not text_parts:
        raise ValueError("No text could be extracted from the PDF")

    full_text = '\n\n'.join(text_parts)
    cleaned = _clean_text(full_text)

    # Truncate if too long for the AI model
    if len(cleaned) > MAX_TEXT_LENGTH:
        logger.info("Text truncated from %d to %d chars", len(cleaned), MAX_TEXT_LENGTH)
        cleaned = cleaned[:MAX_TEXT_LENGTH] + "\n\n[... document truncated due to length ...]"

    logger.info("Extracted %d characters of text", len(cleaned))
    return cleaned


def _clean_text(text):
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


def process_tender_pdf(url):
    """
    Full pipeline: download PDF (handling HTML pages) → extract text → clean → return.
    This is the main entry point for PDF processing.
    """
    pdf_bytes = download_pdf(url)
    text = extract_text_from_pdf(pdf_bytes)
    return text
