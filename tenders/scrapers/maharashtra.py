# tenders/scrapers/maharashtra.py
"""
Scraper for Maharashtra tenders via eProcure NIC.
Source: https://mahatenders.gov.in → redirects to eProcure NIC

Searches for Maharashtra state government organisations on eProcure.
"""

import logging
from .eprocure_base import scrape_eprocure_search

logger = logging.getLogger('scrapers')

# Maharashtra-specific search keywords (state org names on eProcure)
SEARCH_KEYWORDS = [
    "Maharashtra",
    "MSRDC",      # Maharashtra State Road Development Corporation
    "MHADA",      # Maharashtra Housing and Area Development Authority
    "CIDCO",      # City and Industrial Development Corporation
    "MSEDCL",     # Maharashtra State Electricity Distribution
    "PCMC",       # Pimpri-Chinchwad Municipal Corporation
    "PWD Maharashtra",
]


def scrape_maharashtra():
    """Scrape Maharashtra tenders from eProcure NIC."""
    return scrape_eprocure_search(
        state_name="Maharashtra",
        search_keywords=SEARCH_KEYWORDS,
        max_pages=30,
    )
