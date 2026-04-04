# # tenders/scrapers/utils.py
# """
# Shared utilities for all tender scrapers.
# Provides category classification, location extraction, date parsing,
# User-Agent rotation, and safe HTTP requests with retry logic.
# """

# import re
# import time
# import random
# import logging
# import requests
# from datetime import datetime

# logger = logging.getLogger('scrapers')

# # ---------------------------------------------------------------------------
# # USER-AGENT ROTATION
# # ---------------------------------------------------------------------------
# USER_AGENTS = [
#     "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
#     "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
#     "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
#     "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
#     "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
#     "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
#     "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0",
#     "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
#     "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
#     "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
#     "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
#     "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0",
# ]


# def get_random_headers():
#     """Return headers with a random User-Agent."""
#     return {
#         "User-Agent": random.choice(USER_AGENTS),
#         "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
#         "Accept-Language": "en-US,en;q=0.5",
#         "Accept-Encoding": "gzip, deflate",
#         "Connection": "keep-alive",
#     }


# # ---------------------------------------------------------------------------
# # SAFE HTTP REQUEST WITH RETRY
# # ---------------------------------------------------------------------------
# def safe_request(url, method='GET', max_retries=3, timeout=30, **kwargs):
#     """
#     Make an HTTP request with retry logic, random delays, and User-Agent rotation.
#     Returns a Response object or None on failure.
#     """
#     for attempt in range(1, max_retries + 1):
#         try:
#             # Random delay between requests (1-3 seconds)
#             delay = random.uniform(1.0, 3.0)
#             time.sleep(delay)

#             headers = kwargs.pop('headers', {})
#             headers.update(get_random_headers())

#             response = requests.request(
#                 method, url,
#                 headers=headers,
#                 timeout=timeout,
#                 **kwargs
#             )
#             response.raise_for_status()
#             return response

#         except requests.exceptions.RequestException as e:
#             logger.warning(
#                 f"[Attempt {attempt}/{max_retries}] Request failed for {url}: {e}"
#             )
#             if attempt < max_retries:
#                 backoff = attempt * 2 + random.uniform(0, 1)
#                 logger.info(f"Retrying in {backoff:.1f}s...")
#                 time.sleep(backoff)
#             else:
#                 logger.error(f"All {max_retries} attempts failed for {url}")
#                 return None


# # ---------------------------------------------------------------------------
# # CATEGORY CLASSIFICATION
# # ---------------------------------------------------------------------------
# CATEGORY_KEYWORDS = {
#     "IT & Technology": [
#         "software", "it ", "computer", "server", "network", "digital",
#         "website", "application", "system integration", "data center",
#         "cloud", "cyber", "iot", "erp", "hardware", "laptop", "printer",
#         "cctv", "surveillance", "cabling", "fiber", "internet", "telecom",
#     ],
#     "Infrastructure": [
#         "road", "bridge", "highway", "flyover", "overpass", "tunnel",
#         "infrastructure", "metro", "railway", "airport", "port",
#     ],
#     "Construction": [
#         "building", "construction", "civil", "cement", "concrete",
#         "renovation", "repair", "maintenance", "painting", "flooring",
#         "plumbing", "mason", "demolition", "housing", "quarters",
#     ],
#     "Healthcare": [
#         "hospital", "medical", "health", "pharma", "medicine",
#         "ambulance", "surgical", "diagnostic", "laboratory", "vaccine",
#         "clinic", "nursing", "oxygen", "biomedical",
#     ],
#     "Education": [
#         "school", "college", "university", "education", "training",
#         "scholarship", "academic", "library", "classroom", "hostel",
#     ],
#     "Transportation": [
#         "vehicle", "bus", "truck", "transport", "logistics", "fleet",
#         "cargo", "shipping", "warehouse", "automobile",
#     ],
#     "Supply & Procurement": [
#         "supply", "procurement", "purchase", "stationery", "furniture",
#         "equipment", "machinery", "uniform", "material",
#     ],
#     "Consulting": [
#         "consultancy", "consulting", "advisory", "audit", "survey",
#         "feasibility", "study", "evaluation", "assessment", "dpr",
#     ],
#     "Energy & Power": [
#         "electricity", "power", "solar", "renewable", "transformer",
#         "substation", "generator", "energy", "wind", "battery",
#     ],
#     "Water & Sanitation": [
#         "water supply", "sewage", "drainage", "sanitation", "pipeline",
#         "borewell", "tubewell", "irrigation", "canal", "dam",
#         "water treatment", "desalination",
#     ],
#     "Agriculture": [
#         "agriculture", "farming", "crop", "fertilizer", "pesticide",
#         "seed", "horticulture", "floriculture", "fishery", "dairy",
#     ],
# }


# def classify_category(text):
#     """
#     Classify a tender into a category based on keyword matching.
#     Returns the best matching category or 'General' if no match.
#     """
#     if not text:
#         return "General"

#     text_lower = text.lower()

#     # Score each category by number of keyword matches
#     best_category = "General"
#     best_score = 0

#     for category, keywords in CATEGORY_KEYWORDS.items():
#         score = sum(1 for kw in keywords if kw in text_lower)
#         if score > best_score:
#             best_score = score
#             best_category = category

#     return best_category


# # ---------------------------------------------------------------------------
# # LOCATION EXTRACTION
# # ---------------------------------------------------------------------------
# INDIAN_LOCATIONS = [
#     # States
#     "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh",
#     "Goa", "Gujarat", "Haryana", "Himachal Pradesh", "Jharkhand",
#     "Karnataka", "Kerala", "Madhya Pradesh", "Maharashtra", "Manipur",
#     "Meghalaya", "Mizoram", "Nagaland", "Odisha", "Punjab", "Rajasthan",
#     "Sikkim", "Tamil Nadu", "Telangana", "Tripura", "Uttar Pradesh",
#     "Uttarakhand", "West Bengal",
#     # Union Territories
#     "Delhi", "Chandigarh", "Puducherry", "Jammu", "Kashmir", "Ladakh",
#     # Major Cities
#     "Mumbai", "Pune", "Nagpur", "Nashik", "Aurangabad", "Thane", "Solapur",
#     "Ahmedabad", "Surat", "Vadodara", "Rajkot", "Gandhinagar", "Bhavnagar",
#     "Jamnagar", "Junagadh", "Anand", "Mehsana", "Bharuch", "Morbi",
#     "Bhopal", "Indore", "Jabalpur", "Gwalior", "Ujjain", "Sagar", "Rewa",
#     "Jaipur", "Jodhpur", "Udaipur", "Kota", "Bikaner", "Ajmer", "Alwar",
#     "Bengaluru", "Mysuru", "Hubli", "Mangalore", "Belgaum", "Dharwad",
#     "Shimoga", "Davangere", "Gulbarga", "Bellary",
#     "Hyderabad", "Chennai", "Kolkata", "Lucknow", "Patna", "Ranchi",
#     "Bhubaneswar", "Raipur", "Dehradun", "Thiruvananthapuram", "Kochi",
#     "Coimbatore", "Visakhapatnam", "Vijayawada", "Agra", "Varanasi",
#     "Kanpur", "Prayagraj", "Noida", "Gurgaon", "Faridabad", "Ghaziabad",
#     "Ludhiana", "Amritsar", "Jalandhar", "Panaji", "Imphal", "Shillong",
#     "Aizawl", "Kohima", "Gangtok", "Agartala", "Itanagar", "Dispur",
# ]

# # Pre-compile regex patterns for locations (case-insensitive)
# _LOCATION_PATTERNS = [
#     (loc, re.compile(r'\b' + re.escape(loc) + r'\b', re.IGNORECASE))
#     for loc in INDIAN_LOCATIONS
# ]


# def extract_location(text, default_source=None):
#     """
#     Extract location from tender text using keyword matching.
#     Falls back to the source state name if no specific location is found.
#     """
#     if not text:
#         return default_source or ""

#     for location_name, pattern in _LOCATION_PATTERNS:
#         if pattern.search(text):
#             return location_name

#     return default_source or ""


# # ---------------------------------------------------------------------------
# # DATE PARSING
# # ---------------------------------------------------------------------------
# DATE_FORMATS = [
#     "%d/%m/%Y %H:%M:%S",
#     "%d/%m/%Y %H:%M",
#     "%d/%m/%Y",
#     "%d-%m-%Y %H:%M:%S",
#     "%d-%m-%Y %H:%M",
#     "%d-%m-%Y",
#     "%Y-%m-%d %H:%M:%S",
#     "%Y-%m-%d",
#     "%d %b %Y",           # 01 Jan 2024
#     "%d %B %Y",           # 01 January 2024
#     "%d-%b-%Y",           # 01-Jan-2024
#     "%d-%B-%Y",           # 01-January-2024
#     "%d/%b/%Y",           # 01/Jan/2024
#     "%b %d, %Y",          # Jan 01, 2024
#     "%B %d, %Y",          # January 01, 2024
# ]


# def parse_date(date_str):
#     """
#     Parse a date string trying multiple common Indian date formats.
#     Returns a date object or None if parsing fails.
#     """
#     if not date_str:
#         return None

#     date_str = date_str.strip()

#     for fmt in DATE_FORMATS:
#         try:
#             return datetime.strptime(date_str, fmt).date()
#         except (ValueError, TypeError):
#             continue

#     # Try extracting date pattern from text
#     match = re.search(r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})', date_str)
#     if match:
#         extracted = match.group(1)
#         for fmt in ["%d/%m/%Y", "%d-%m-%Y", "%m/%d/%Y", "%d/%m/%y", "%d-%m-%y"]:
#             try:
#                 return datetime.strptime(extracted, fmt).date()
#             except (ValueError, TypeError):
#                 continue

#     logger.debug(f"Could not parse date: '{date_str}'")
#     return None


# def is_date_string(value):
#     """Check if a string looks like a date."""
#     if not value:
#         return False
#     return bool(re.search(r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}', value))


# # ---------------------------------------------------------------------------
# # TEXT CLEANING
# # ---------------------------------------------------------------------------
# def clean_text(text):
#     """Clean and normalize text from scraped data."""
#     if not text:
#         return ""
#     # Remove extra whitespace, newlines, tabs
#     text = re.sub(r'\s+', ' ', text).strip()
#     return text


# def generate_tender_id(source, *parts):
#     """
#     Generate a unique tender ID from source and identifying parts.
#     Used when a tender doesn't have a clear unique ID.
#     """
#     import hashlib
#     raw = f"{source}_{'_'.join(str(p) for p in parts if p)}"
#     hash_val = hashlib.md5(raw.encode()).hexdigest()[:12]
#     return f"{source.upper()[:3]}_{hash_val}"

"""
Shared utilities for all tender scrapers.
Production-ready version with:
- Retry + anti-blocking
- Safe parsing
- Data protection
- Smart classification
"""

import re
import time
import random
import logging
import requests
from datetime import datetime
from bs4 import BeautifulSoup

logger = logging.getLogger('scrapers')

# ---------------------------------------------------------------------------
# USER-AGENT ROTATION
# ---------------------------------------------------------------------------
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
]


def get_random_headers():
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive",
        "Referer": "https://www.google.com/",
        "DNT": "1",
        "Upgrade-Insecure-Requests": "1",
    }


# ---------------------------------------------------------------------------
# SAFE HTTP REQUEST WITH RETRY
# ---------------------------------------------------------------------------
def safe_request(url, method='GET', max_retries=5, timeout=60, use_cloudscraper=False, **kwargs):
    """
    Robust HTTP request handler with retry, delay, and anti-blocking.
    """

    if use_cloudscraper:
        try:
            import cloudscraper
            scraper = cloudscraper.create_scraper()
        except ImportError:
            scraper = None
    else:
        scraper = None

    session = requests.Session()

    for attempt in range(1, max_retries + 1):
        try:
            delay = random.uniform(2, 5)
            time.sleep(delay)

            headers = kwargs.pop('headers', {})
            headers.update(get_random_headers())

            if scraper:
                response = scraper.get(url, timeout=timeout)
            else:
                response = session.request(
                    method,
                    url,
                    headers=headers,
                    timeout=timeout,
                    verify=False,
                    **kwargs
                )

            if response.status_code in [403, 429]:
                raise requests.exceptions.RequestException(f"Blocked: {response.status_code}")

            response.raise_for_status()

            logger.info(f"SUCCESS {url} [{response.status_code}]")
            return response

        except requests.exceptions.RequestException as e:
            logger.warning(f"[Attempt {attempt}] Failed {url}: {e}")

            if attempt < max_retries:
                backoff = attempt * 3 + random.uniform(1, 2)
                time.sleep(backoff)
            else:
                logger.error(f"FAILED after {max_retries} attempts: {url}")
                return None


# ---------------------------------------------------------------------------
# SAFE HTML PARSER
# ---------------------------------------------------------------------------
def parse_html(content):
    try:
        return BeautifulSoup(content, "lxml")
    except Exception:
        return BeautifulSoup(content, "html.parser")


# ---------------------------------------------------------------------------
# SAFE TEXT HANDLING
# ---------------------------------------------------------------------------
def clean_text(text):
    if not text:
        return ""
    return re.sub(r'\s+', ' ', text).strip()


def safe_truncate(value, limit=2000):
    if not value:
        return value
    return value[:limit]


# ---------------------------------------------------------------------------
# CATEGORY CLASSIFICATION (IMPROVED)
# ---------------------------------------------------------------------------
CATEGORY_KEYWORDS = {
    "IT & Technology": ["software", "it ", "server", "network", "cloud", "erp", "cctv"],
    "Infrastructure": ["road", "bridge", "highway", "metro"],
    "Construction": ["building", "construction", "repair", "civil"],
    "Healthcare": ["hospital", "medical", "pharma"],
    "Education": ["school", "college", "university"],
    "Transportation": ["vehicle", "transport", "logistics"],
    "Supply & Procurement": ["supply", "purchase", "equipment"],
    "Consulting": ["consultancy", "audit", "survey"],
    "Energy & Power": ["electricity", "solar", "power"],
    "Water & Sanitation": ["water", "sewage", "pipeline"],
    "Agriculture": ["farming", "crop", "fertilizer"],
}


def classify_category(text):
    if not text:
        return "General"

    text_lower = text.lower()
    scores = {}

    for category, keywords in CATEGORY_KEYWORDS.items():
        scores[category] = sum(text_lower.count(k) for k in keywords)

    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "General"


# ---------------------------------------------------------------------------
# LOCATION EXTRACTION
# ---------------------------------------------------------------------------
INDIAN_LOCATIONS = ["Ahmedabad", "Surat", "Vadodara", "Rajkot", "Gandhinagar", "Mumbai", "Delhi", "Bangalore"]

_LOCATION_PATTERNS = [
    (loc, re.compile(r'\b' + re.escape(loc) + r'\b', re.IGNORECASE))
    for loc in INDIAN_LOCATIONS
]


def extract_location(text, default_source=None):
    if not text:
        return {"city": "", "state": default_source or ""}

    for loc, pattern in _LOCATION_PATTERNS:
        if pattern.search(text):
            return {"city": loc, "state": default_source or ""}

    return {"city": "", "state": default_source or ""}


# ---------------------------------------------------------------------------
# DATE PARSING
# ---------------------------------------------------------------------------
DATE_FORMATS = [
    "%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d",
    "%d %b %Y", "%d %B %Y"
]


def parse_date(date_str):
    if not date_str:
        return None

    date_str = date_str.strip()

    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(date_str, fmt).date()
        except:
            continue

    match = re.search(r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})', date_str)
    if match:
        try:
            return datetime.strptime(match.group(1), "%d/%m/%Y").date()
        except:
            pass

    return None


def is_date_string(value):
    return bool(re.search(r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}', value or ""))


# ---------------------------------------------------------------------------
# UNIQUE ID GENERATOR
# ---------------------------------------------------------------------------
def generate_tender_id(source, *parts):
    import hashlib
    raw = f"{source}_{'_'.join(str(p) for p in parts if p)}"
    return f"{source.upper()[:3]}_{hashlib.md5(raw.encode()).hexdigest()[:12]}"