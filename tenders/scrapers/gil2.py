# # tenders/scrapers/gil.py
# """
# Scraper for Gujarat Industrial Development Corporation (GIL) tenders.
# Source: https://gil.gujarat.gov.in/tenders

# Table columns:
#   Sr No | Description | Published Date & Time | Due Date & Time | Opening Date & Time | Details

# Pagination: ASP.NET GridView with __doPostBack('ctl00$body$gvTenderList','Page$N')
# """

# import logging
# import re
# import time
# import random
# import hashlib
# import requests
# from bs4 import BeautifulSoup
# from tenders.models import Tender
# from .utils import (
#     classify_category, extract_location,
#     parse_date, clean_text, get_random_headers
# )

# logger = logging.getLogger('scrapers')

# BASE_URL = "https://gil.gujarat.gov.in/tenders"
# GRIDVIEW_ID = "ctl00$body$gvTenderList"

# DEPARTMENT_KEYWORDS = {
#     "health": "Health Department",
#     "education": "Education Department",
#     "water": "Water Department",
#     "narmada": "Water Department",
#     "police": "Police Department",
#     "revenue": "Revenue Department",
#     "public works": "Public Works Department",
#     "panchayat": "Panchayat Department",
#     "urban": "Urban Development Department",
#     "agriculture": "Agriculture Department",
#     "forest": "Forest Department",
#     "energy": "Energy Department",
#     "transport": "Transport Department",
#     "finance": "Finance Department",
#     "industries": "Industries Department",
# }


# def extract_department(title):
#     title_lower = title.lower()
#     for keyword, dept in DEPARTMENT_KEYWORDS.items():
#         if keyword in title_lower:
#             return dept
#     return ""


# def extract_all_form_fields(soup):
#     """Extract ALL form fields from the ASP.NET page."""
#     fields = {}
#     form = soup.find("form")
#     if not form:
#         return fields

#     for inp in form.find_all("input"):
#         name = inp.get("name")
#         if name:
#             fields[name] = inp.get("value", "")

#     for sel in form.find_all("select"):
#         name = sel.get("name")
#         if name:
#             selected = sel.find("option", selected=True)
#             fields[name] = selected.get("value", "") if selected else ""

#     return fields


# def find_data_table(soup):
#     """Find the main tender data table."""
#     # Try by ID first
#     table = soup.find("table", id=re.compile(r"gvTenderList", re.I))
#     if table:
#         return table
#     # Fallback: find largest table
#     tables = soup.find_all("table")
#     best = None
#     best_rows = 0
#     for t in tables:
#         row_count = len(t.find_all("tr"))
#         if row_count > best_rows:
#             best_rows = row_count
#             best = t
#     return best


# def parse_page_tenders(soup):
#     """
#     Parse all tenders from the current page.
#     Returns list of dicts with tender data.
#     """
#     tenders = []
#     table = find_data_table(soup)
#     if not table:
#         return tenders

#     for row in table.find_all("tr"):
#         cols = row.find_all("td")
#         if not cols or len(cols) < 5:
#             continue

#         cols_text = [clean_text(col.get_text()) for col in cols]
#         sr_no = cols_text[0].strip()

#         if not sr_no.isdigit():
#             continue

#         title = cols_text[1].strip()
#         if not title or len(title) < 5:
#             continue

#         # Col 2: Published Date & Time
#         # Col 3: Due Date & Time (closing)
#         # Col 4: Opening Date & Time
#         closing_date = parse_date(cols_text[3]) if len(cols_text) > 3 else None
#         if not closing_date and len(cols_text) > 2:
#             closing_date = parse_date(cols_text[2])

#         # Detail link
#         link = BASE_URL
#         detail_link = row.find("a", href=re.compile(r"TenderDetails", re.I))
#         if detail_link:
#             href = detail_link.get("href", "")
#             if href.startswith("http"):
#                 link = href
#             elif href:
#                 link = f"https://gil.gujarat.gov.in/{href.lstrip('/')}"

#         # Unique ID from Sr No + full title
#         full_hash = hashlib.md5(f"GIL_{sr_no}_{title}".encode()).hexdigest()[:16]

#         tenders.append({
#             "sr_no": int(sr_no),
#             "tender_id": f"GIL_{full_hash}",
#             "title": title,
#             "department": extract_department(title),
#             "closing_date": closing_date,
#             "link": link,
#             "category": classify_category(title),
#             "location": extract_location(title, default_source="Gujarat"),
#         })

#     return tenders


# def scrape_gil():
#     """
#     Scrape ALL tenders from Gujarat GIL portal.
#     Strategy: POST with Page$2, Page$3 etc. directly, tracking by Sr No to detect end.
#     """
#     logger.info("🚀 Starting Gujarat (GIL) scraper...")

#     # Clear old Gujarat data for clean re-scrape
#     old_count = Tender.objects.filter(source="Gujarat").count()
#     if old_count > 0:
#         Tender.objects.filter(source="Gujarat").delete()
#         logger.info(f"  Cleared {old_count} old Gujarat records")

#     total_created = 0
#     session = requests.Session()
#     session.headers.update(get_random_headers())
#     session.headers.update({
#         "Referer": BASE_URL,
#         "Origin": "https://gil.gujarat.gov.in",
#     })

#     # GET the first page
#     try:
#         logger.info("  Fetching page 1 (initial GET)...")
#         response = session.get(BASE_URL, timeout=30)
#         response.raise_for_status()
#     except Exception as e:
#         logger.error(f"  Failed to fetch initial page: {e}")
#         return 0

#     soup = BeautifulSoup(response.text, "lxml")
#     seen_sr_nos = set()
#     page = 1

#     while True:
#         # Parse tenders from current page
#         tenders = parse_page_tenders(soup)
#         page_new = 0

#         sr_range = ""
#         if tenders:
#             sr_nums = [t["sr_no"] for t in tenders]
#             sr_range = f"Sr {min(sr_nums)}-{max(sr_nums)}"

#         for t in tenders:
#             if t["sr_no"] in seen_sr_nos:
#                 continue  # Already scraped (cycle detection)
#             seen_sr_nos.add(t["sr_no"])

#             try:
#                 Tender.objects.create(
#                     tender_id=t["tender_id"],
#                     source="Gujarat",
#                     title=t["title"],
#                     department=t["department"],
#                     category=t["category"],
#                     location=t["location"],
#                     closing_date=t["closing_date"],
#                     link=t["link"],
#                 )
#                 page_new += 1
#                 total_created += 1
#             except Exception as e:
#                 logger.error(f"  Error saving tender {t['tender_id']}: {e}")

#         logger.info(f"  Page {page}: {page_new} new tenders ({sr_range})")

#         # Stop if cycling (all tenders on this page already seen)
#         if tenders and page_new == 0:
#             logger.info(f"  All tenders on page {page} already seen. Stopping.")
#             break

#         # Stop if no tenders found
#         if not tenders:
#             logger.info(f"  No tenders found on page {page}. Stopping.")
#             break

#         # Navigate to next page via direct Page$N postback
#         next_page = page + 1
#         form_fields = extract_all_form_fields(soup)
#         form_fields["__EVENTTARGET"] = GRIDVIEW_ID
#         form_fields["__EVENTARGUMENT"] = f"Page${next_page}"

#         delay = random.uniform(1.0, 2.5)
#         time.sleep(delay)

#         try:
#             response = session.post(BASE_URL, data=form_fields, timeout=30)
#             response.raise_for_status()
#             soup = BeautifulSoup(response.text, "lxml")
#             page += 1
#         except Exception as e:
#             logger.error(f"  Failed to navigate to page {next_page}: {e}")
#             break

#         # Safety limit
#         if page > 50:
#             logger.warning("  Reached safety page limit. Stopping.")
#             break

#     logger.info(
#         f"✅ Gujarat scraper completed: {total_created} tenders scraped from {page} pages"
#     )
#     return total_created

########################################################################################

# tenders/scrapers/gil.py

import logging
import re
import time
import random
import hashlib

import cloudscraper  # ✅ NEW (important)
from bs4 import BeautifulSoup

from tenders.models import Tender
from .utils import (
    classify_category, extract_location,
    parse_date, clean_text, get_random_headers
)

logger = logging.getLogger('scrapers')

BASE_URL = "https://gil.gujarat.gov.in/tenders"
GRIDVIEW_ID = "ctl00$body$gvTenderList"

# ✅ Retry Config
MAX_RETRIES = 3
REQUEST_TIMEOUT = 60

DEPARTMENT_KEYWORDS = {
    "health": "Health Department",
    "education": "Education Department",
    "water": "Water Department",
    "narmada": "Water Department",
    "police": "Police Department",
    "revenue": "Revenue Department",
    "public works": "Public Works Department",
    "panchayat": "Panchayat Department",
    "urban": "Urban Development Department",
    "agriculture": "Agriculture Department",
    "forest": "Forest Department",
    "energy": "Energy Department",
    "transport": "Transport Department",
    "finance": "Finance Department",
    "industries": "Industries Department",
}


def extract_department(title):
    title_lower = title.lower()
    for keyword, dept in DEPARTMENT_KEYWORDS.items():
        if keyword in title_lower:
            return dept
    return ""


def create_scraper():
    """Create a cloudscraper session with browser-like behavior"""
    scraper = cloudscraper.create_scraper(
        browser={
            "browser": "chrome",
            "platform": "windows",
            "mobile": False
        }
    )

    scraper.headers.update(get_random_headers())
    scraper.headers.update({
        "Referer": BASE_URL,
        "Origin": "https://gil.gujarat.gov.in",
        "Connection": "keep-alive",
    })

    return scraper


def fetch_with_retry(scraper, method, url, **kwargs):
    """Retry wrapper for GET/POST requests"""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = scraper.request(method, url, timeout=REQUEST_TIMEOUT, **kwargs)
            response.raise_for_status()
            return response

        except Exception as e:
            logger.warning(f"Attempt {attempt} failed: {e}")

            if attempt == MAX_RETRIES:
                logger.error("❌ Max retries reached.")
                return None

            sleep_time = random.uniform(2, 5)
            time.sleep(sleep_time)

    return None


def extract_all_form_fields(soup):
    fields = {}
    form = soup.find("form")
    if not form:
        return fields

    for inp in form.find_all("input"):
        name = inp.get("name")
        if name:
            fields[name] = inp.get("value", "")

    for sel in form.find_all("select"):
        name = sel.get("name")
        if name:
            selected = sel.find("option", selected=True)
            fields[name] = selected.get("value", "") if selected else ""

    return fields


def find_data_table(soup):
    table = soup.find("table", id=re.compile(r"gvTenderList", re.I))
    if table:
        return table

    tables = soup.find_all("table")
    best = None
    best_rows = 0

    for t in tables:
        row_count = len(t.find_all("tr"))
        if row_count > best_rows:
            best_rows = row_count
            best = t

    return best


def parse_page_tenders(soup):
    tenders = []
    table = find_data_table(soup)

    if not table:
        return tenders

    for row in table.find_all("tr"):
        cols = row.find_all("td")

        if not cols or len(cols) < 5:
            continue

        cols_text = [clean_text(col.get_text()) for col in cols]
        sr_no = cols_text[0].strip()

        if not sr_no.isdigit():
            continue

        title = cols_text[1].strip()

        if not title or len(title) < 5:
            continue

        closing_date = parse_date(cols_text[3]) if len(cols_text) > 3 else None
        if not closing_date and len(cols_text) > 2:
            closing_date = parse_date(cols_text[2])

        link = BASE_URL
        detail_link = row.find("a", href=re.compile(r"TenderDetails", re.I))

        if detail_link:
            href = detail_link.get("href", "")
            if href.startswith("http"):
                link = href
            elif href:
                link = f"https://gil.gujarat.gov.in/{href.lstrip('/')}"

        full_hash = hashlib.md5(f"GIL_{sr_no}_{title}".encode()).hexdigest()[:16]

        tenders.append({
            "sr_no": int(sr_no),
            "tender_id": f"GIL_{full_hash}",
            "title": title,
            "department": extract_department(title),
            "closing_date": closing_date,
            "link": link,
            "category": classify_category(title),
            "location": extract_location(title, default_source="Gujarat"),
        })

    return tenders


def scrape_gil():
    logger.info("🚀 Starting Gujarat (GIL) scraper...")

    old_count = Tender.objects.filter(source="Gujarat").count()
    if old_count > 0:
        Tender.objects.filter(source="Gujarat").delete()
        logger.info(f"Cleared {old_count} old Gujarat records")

    total_created = 0
    scraper = create_scraper()

    # ✅ INITIAL GET WITH RETRY
    logger.info("Fetching page 1...")
    response = fetch_with_retry(scraper, "GET", BASE_URL)

    if not response:
        logger.error("❌ Failed to load initial page")
        return 0

    soup = BeautifulSoup(response.text, "lxml")
    seen_sr_nos = set()
    page = 1

    while True:
        tenders = parse_page_tenders(soup)
        page_new = 0

        for t in tenders:
            if t["sr_no"] in seen_sr_nos:
                continue

            seen_sr_nos.add(t["sr_no"])

            try:
                Tender.objects.create(
                    tender_id=t["tender_id"],
                    source="Gujarat",
                    title=t["title"],
                    department=t["department"],
                    category=t["category"],
                    location=t["location"],
                    closing_date=t["closing_date"],
                    link=t["link"],
                )
                page_new += 1
                total_created += 1

            except Exception as e:
                logger.error(f"DB error: {e}")

        logger.info(f"Page {page}: {page_new} new tenders")

        if not tenders or page_new == 0:
            logger.info("Stopping pagination")
            break

        next_page = page + 1
        form_fields = extract_all_form_fields(soup)

        form_fields["__EVENTTARGET"] = GRIDVIEW_ID
        form_fields["__EVENTARGUMENT"] = f"Page${next_page}"

        time.sleep(random.uniform(2, 4))

        response = fetch_with_retry(scraper, "POST", BASE_URL, data=form_fields)

        if not response:
            logger.error("Pagination failed")
            break

        soup = BeautifulSoup(response.text, "lxml")
        page += 1

        if page > 50:
            logger.warning("Safety break")
            break

    logger.info(f"✅ Completed: {total_created} tenders")
    return total_created