# tenders/scrapers/gil.py
"""
Scraper for Gujarat tenders via eProcure NIC.
Source: https://eprocure.gov.in

Previously scraped directly from https://gil.gujarat.gov.in/tenders,
but that site blocks data center IPs. Now uses the central eProcure NIC
platform (same as Maharashtra, Karnataka, etc.) which is reliably accessible.
"""

import logging
from .eprocure_base import scrape_eprocure_search

logger = logging.getLogger('scrapers')

# Gujarat-specific search keywords (state org names on eProcure)
SEARCH_KEYWORDS = [
    "Gujarat",
    "GIDC",        # Gujarat Industrial Development Corporation
    "GSPC",        # Gujarat State Petroleum Corporation
    "GWSSB",       # Gujarat Water Supply & Sewerage Board
    "GSECL",       # Gujarat State Electricity Corporation Limited
    "GETCO",       # Gujarat Energy Transmission Corporation
    "GUVNL",       # Gujarat Urja Vikas Nigam Limited
    "GMDC",        # Gujarat Mineral Development Corporation
    "GNFC",        # Gujarat Narmada Valley Fertilizers & Chemicals
    "GIL Gujarat",
    "PWD Gujarat",
    "GSRTC",       # Gujarat State Road Transport Corporation
]


def scrape_gil():
    """Scrape Gujarat tenders from eProcure NIC."""
    return scrape_eprocure_search(
        state_name="Gujarat",
        search_keywords=SEARCH_KEYWORDS,
        max_pages=30,
    )