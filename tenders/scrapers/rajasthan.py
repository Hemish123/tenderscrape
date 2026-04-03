# tenders/scrapers/rajasthan.py
"""
Scraper for Rajasthan tenders via eProcure NIC.
Source: https://eproc.rajasthan.gov.in → NIC eProcure platform

Searches for Rajasthan state government organisations on eProcure.
"""

import logging
from .eprocure_base import scrape_eprocure_search

logger = logging.getLogger('scrapers')

# Rajasthan-specific search keywords
SEARCH_KEYWORDS = [
    "Rajasthan",
    "RIICO",      # Rajasthan State Industrial Development and Investment Corporation
    "JVVNL",      # Jaipur Vidyut Vitran Nigam Limited
    "PWD Rajasthan",
    "RSRTC",      # Rajasthan State Road Transport Corporation
    "Jaipur",
    "Jodhpur",
    "PHED Rajasthan",  # Public Health Engineering Department
]


def scrape_rajasthan():
    """Scrape Rajasthan tenders from eProcure NIC."""
    return scrape_eprocure_search(
        state_name="Rajasthan",
        search_keywords=SEARCH_KEYWORDS,
        max_pages=30,
    )
