# tenders/scrapers/karnataka.py
"""
Scraper for Karnataka tenders via eProcure NIC.
Source: https://eproc.karnataka.gov.in → NIC eProcure platform

Searches for Karnataka state government organisations on eProcure.
"""

import logging
from .eprocure_base import scrape_eprocure_search

logger = logging.getLogger('scrapers')

# Karnataka-specific search keywords
SEARCH_KEYWORDS = [
    "Karnataka",
    "KRDCL",      # Karnataka Road Development Corporation Limited
    "BESCOM",     # Bangalore Electricity Supply Company
    "BMRCL",      # Bangalore Metro Rail Corporation Limited
    "PWD Karnataka",
    "KPCL",       # Karnataka Power Corporation Limited
    "Bengaluru",
    "BWSSB",      # Bangalore Water Supply and Sewerage Board
]


def scrape_karnataka():
    """Scrape Karnataka tenders from eProcure NIC."""
    return scrape_eprocure_search(
        state_name="Karnataka",
        search_keywords=SEARCH_KEYWORDS,
        max_pages=30,
    )
