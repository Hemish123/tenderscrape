# tenders/scrapers/madhya_pradesh.py
"""
Scraper for Madhya Pradesh tenders via eProcure NIC.
Source: https://mptenders.gov.in → NIC eProcure platform

Searches for MP state government organisations on eProcure.
"""

import logging
from .eprocure_base import scrape_eprocure_search

logger = logging.getLogger('scrapers')

# Madhya Pradesh-specific search keywords
SEARCH_KEYWORDS = [
    "Madhya Pradesh",
    "MPSIDC",     # Madhya Pradesh State Industrial Development Corporation
    "MPPKVVCL",   # MP Paschim Kshetra Vidyut Vitaran Company
    "PWD Madhya Pradesh",
    "MPRDC",      # Madhya Pradesh Road Development Corporation
    "Bhopal",
    "Indore",
]


def scrape_madhya_pradesh():
    """Scrape Madhya Pradesh tenders from eProcure NIC."""
    return scrape_eprocure_search(
        state_name="Madhya Pradesh",
        search_keywords=SEARCH_KEYWORDS,
        max_pages=30,
    )
