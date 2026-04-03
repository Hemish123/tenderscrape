# tenders/scrapers/eprocure_base.py
"""
Base scraper for Indian government tenders from the Central Public Procurement Portal (eProcure NIC).
Source: https://eprocure.gov.in

Many state e-procurement portals (Maharashtra, Madhya Pradesh, Rajasthan, Karnataka, etc.)
are built on the NIC eProcure platform. This base module provides reusable scraping logic
that can be parameterized per state by searching for state-specific organisation names.

The eProcure Active Tenders page lists all currently active tenders with pagination.
We search for tenders matching specific state organisations to get state-specific data.
"""

import logging
import re
import time
import random
import requests
from bs4 import BeautifulSoup
from tenders.models import Tender
from .utils import (
    classify_category, extract_location,
    parse_date, clean_text, generate_tender_id, get_random_headers
)

logger = logging.getLogger('scrapers')

EPROCURE_BASE = "https://eprocure.gov.in/eprocure/app"
ACTIVE_TENDERS_URL = f"{EPROCURE_BASE}?page=FrontEndLatestActiveTenders&service=page"
SEARCH_URL = f"{EPROCURE_BASE}?page=FrontEndAdvancedSearch&service=page"


def scrape_eprocure_search(state_name, search_keywords, max_pages=30):
    """
    Scrape tenders from eProcure NIC for a specific state using the search page.
    
    Args:
        state_name: Name of the state (e.g., "Maharashtra")
        search_keywords: List of keywords to search for (organisation names)
        max_pages: Maximum number of pages to scrape per keyword
    
    Returns:
        Total number of new tenders created
    """
    logger.info(f"🚀 Starting {state_name} scraper (via eProcure NIC)...")
    total_created = 0
    total_updated = 0

    session = requests.Session()
    session.headers.update(get_random_headers())

    for keyword in search_keywords:
        logger.info(f"  Searching for: '{keyword}'")
        page_created, page_updated = _scrape_keyword(
            session, state_name, keyword, max_pages
        )
        total_created += page_created
        total_updated += page_updated

    logger.info(
        f"✅ {state_name} scraper completed: {total_created} new, {total_updated} updated"
    )
    return total_created


def _scrape_keyword(session, state_name, keyword, max_pages):
    """Scrape all pages for a single search keyword."""
    created = 0
    updated = 0

    # Step 1: GET the search page to get form state
    try:
        response = session.get(SEARCH_URL, timeout=30)
        response.raise_for_status()
    except Exception as e:
        logger.error(f"  Failed to load search page: {e}")
        return created, updated

    soup = BeautifulSoup(response.text, "lxml")

    # Step 2: Submit search form
    form_data = _extract_form_fields(soup)
    # Set the search keyword in the organisation/title field
    form_data['searchText'] = keyword
    form_data['searchIn'] = '0'  # Search in all fields

    # Look for the actual form field names
    search_input = soup.find('input', {'name': re.compile(r'.*[Ss]earch.*|.*[Kk]eyword.*|.*[Qq]uery.*')})
    if search_input:
        form_data[search_input['name']] = keyword

    time.sleep(random.uniform(1.0, 2.5))

    try:
        response = session.post(SEARCH_URL, data=form_data, timeout=30)
        response.raise_for_status()
    except Exception as e:
        logger.error(f"  Search POST failed: {e}")
        # Fall back to direct active tenders page
        return _scrape_active_tenders(session, state_name, keyword, max_pages)

    soup = BeautifulSoup(response.text, "lxml")

    page = 1
    while page <= max_pages:
        logger.info(f"    Processing page {page} for '{keyword}'...")

        # Parse tenders from current page
        page_created, page_updated = _parse_eprocure_page(soup, state_name)
        created += page_created
        updated += page_updated

        if page_created == 0 and page_updated == 0:
            logger.info(f"    No tenders found on page {page}, stopping.")
            break

        # Try to navigate to next page
        soup = _navigate_next_page(session, soup, SEARCH_URL)
        if soup is None:
            logger.info(f"    No more pages after page {page}.")
            break

        page += 1

    return created, updated


def _scrape_active_tenders(session, state_name, keyword, max_pages):
    """
    Fallback: scrape from the Active Tenders page and filter by state keyword.
    """
    logger.info(f"  Falling back to Active Tenders page for '{keyword}'...")
    created = 0
    updated = 0

    try:
        response = session.get(ACTIVE_TENDERS_URL, timeout=30)
        response.raise_for_status()
    except Exception as e:
        logger.error(f"  Failed to load Active Tenders: {e}")
        return created, updated

    soup = BeautifulSoup(response.text, "lxml")
    page = 1

    while page <= max_pages:
        logger.info(f"    Processing Active Tenders page {page}...")

        page_created, page_updated = _parse_eprocure_page(
            soup, state_name, filter_keyword=keyword
        )
        created += page_created
        updated += page_updated

        if page_created == 0 and page_updated == 0 and page > 3:
            break

        soup = _navigate_next_page(session, soup, ACTIVE_TENDERS_URL)
        if soup is None:
            break

        page += 1

    return created, updated


def _parse_eprocure_page(soup, state_name, filter_keyword=None):
    """
    Parse tenders from an eProcure NIC page.
    
    The typical eProcure table structure has columns:
    S.No | e-Published Date | Bid Submission Closing Date | Opening Date | Title/Ref No/Tender ID | Organisation Chain
    
    Some pages may have different column orders, so we use heuristics.
    """
    created = 0
    updated = 0

    # Find all tables and pick the one with tender data
    tables = soup.find_all("table")
    data_table = None

    for table in tables:
        rows = table.find_all("tr")
        if len(rows) > 2:
            # Check if this looks like a tender table
            first_row_text = rows[0].get_text().lower()
            if any(kw in first_row_text for kw in ["tender", "closing", "published", "organisation", "s.no"]):
                data_table = table
                break

    if not data_table:
        # Use the table with the most rows
        if tables:
            tables_with_rows = [(t, len(t.find_all("tr"))) for t in tables]
            tables_with_rows.sort(key=lambda x: x[1], reverse=True)
            if tables_with_rows and tables_with_rows[0][1] > 2:
                data_table = tables_with_rows[0][0]

    if not data_table:
        return created, updated

    rows = data_table.find_all("tr")

    # Determine column mapping from header
    col_map = _detect_columns(rows[0] if rows else None)

    for row in rows[1:]:
        try:
            cols = row.find_all("td")
            if not cols or len(cols) < 4:
                continue

            cols_data = [clean_text(col.get_text()) for col in cols]

            # Skip pagination/nav rows
            all_text = ' '.join(cols_data).lower()
            if any(nav in all_text for nav in ['next', 'previous', 'first', 'last', 'page']):
                if len(all_text) < 100:  # Short rows are likely nav
                    continue

            # Extract fields using column map
            title = _get_col(cols_data, col_map, 'title', fallback_indices=[4, 1, 3])
            department = _get_col(cols_data, col_map, 'organisation', fallback_indices=[5, -1])
            closing_date_raw = _get_col(cols_data, col_map, 'closing_date', fallback_indices=[2])
            published_date_raw = _get_col(cols_data, col_map, 'published_date', fallback_indices=[1])

            if not title or len(title) < 5:
                continue

            # Optionally filter by keyword
            if filter_keyword:
                combined = (title + ' ' + (department or '')).lower()
                if filter_keyword.lower() not in combined:
                    continue

            closing_date = parse_date(closing_date_raw)
            if not closing_date:
                closing_date = parse_date(published_date_raw)

            # Extract link
            link = "https://eprocure.gov.in"
            for col in cols:
                for link_tag in col.find_all("a", href=True):
                    href = link_tag.get('href', '').strip()
                    if not href or href == '#':
                        continue
                    # Skip pagination/navigation links
                    link_text = link_tag.get_text(strip=True).lower()
                    if link_text in ('next', 'previous', 'first', 'last', '>', '<', '>>', '<<'):
                        continue
                    # Direct HTTP links
                    if href.startswith("http"):
                        link = href
                        break
                    # Relative links
                    elif href.startswith("/"):
                        link = "https://eprocure.gov.in" + href
                        break
                    # JavaScript postback links — extract the tender ID/reference
                    elif '__doPostBack' in href:
                        # These can't be directly navigated but we try to extract useful info
                        import re as _re
                        pb_match = _re.search(r"__doPostBack\('([^']+)','([^']*)'\)", href)
                        if pb_match:
                            event_target = pb_match.group(1)
                            event_arg = pb_match.group(2)
                            # Store as a recognizable eProcure reference link
                            link = "https://eprocure.gov.in/eprocure/app?page=FrontEndTenderPreview&service=page"
                        break
                else:
                    continue
                break

            tender_id = generate_tender_id(
                state_name[:3].upper(), title[:80], closing_date_raw or published_date_raw or ''
            )

            category = classify_category(title + ' ' + (department or ''))
            location = extract_location(
                title + ' ' + (department or ''), default_source=state_name
            )

            obj, obj_created = Tender.objects.update_or_create(
                tender_id=tender_id,
                defaults={
                    "source": state_name,
                    "title": title,
                    "department": department or '',
                    "category": category,
                    "location": location,
                    "closing_date": closing_date,
                    "link": link,
                }
            )

            if obj_created:
                created += 1
            else:
                updated += 1

        except Exception as e:
            logger.error(f"    Error parsing row: {e}")
            continue

    return created, updated


def _detect_columns(header_row):
    """Detect column indices from a header row."""
    col_map = {}
    if not header_row:
        return col_map

    headers = header_row.find_all(["th", "td"])
    for i, header in enumerate(headers):
        text = clean_text(header.get_text()).lower()
        if 'title' in text or 'tender' in text or 'work' in text or 'ref' in text:
            col_map['title'] = i
        elif 'organisation' in text or 'department' in text or 'ministry' in text:
            col_map['organisation'] = i
        elif 'closing' in text or 'submission' in text:
            col_map['closing_date'] = i
        elif 'publish' in text or 'e-publish' in text:
            col_map['published_date'] = i
        elif 'opening' in text:
            col_map['opening_date'] = i
        elif 's.no' in text or 'sr' in text or 'sl' in text:
            col_map['sr_no'] = i

    return col_map


def _get_col(cols_data, col_map, key, fallback_indices=None):
    """Get column value using detected map or fallback indices."""
    if key in col_map and col_map[key] < len(cols_data):
        return cols_data[col_map[key]]
    if fallback_indices:
        for idx in fallback_indices:
            if idx < 0:
                idx = len(cols_data) + idx
            if 0 <= idx < len(cols_data):
                return cols_data[idx]
    return ''


def _extract_form_fields(soup):
    """Extract all form fields from the page."""
    fields = {}
    for inp in soup.find_all('input', {'type': ['hidden', 'text', 'submit']}):
        name = inp.get('name')
        if name:
            fields[name] = inp.get('value', '')
    return fields


def _navigate_next_page(session, soup, base_url):
    """
    Try to navigate to the next page via ASP.NET postback or regular link.
    Returns new BeautifulSoup object or None if no next page.
    """
    # Method 1: Look for ASP.NET postback pagination links
    pagination_links = soup.find_all('a', href=re.compile(r'__doPostBack'))
    next_link = None

    for link in pagination_links:
        text = link.get_text(strip=True)
        if text in ['Next', '>', '>>', 'next', '→']:
            next_link = link
            break

    # Also check for numbered page links
    if not next_link:
        # Find current page number
        current_span = soup.find('span', class_=re.compile(r'current|active|selected'))
        if current_span:
            try:
                current_page = int(current_span.get_text(strip=True))
                # Look for next page number
                for link in pagination_links:
                    try:
                        if int(link.get_text(strip=True)) == current_page + 1:
                            next_link = link
                            break
                    except ValueError:
                        continue
            except ValueError:
                pass

    if next_link:
        href = next_link.get('href', '')
        match = re.search(r"__doPostBack\('([^']+)','([^']*)'\)", href)
        if match:
            event_target = match.group(1)
            event_arg = match.group(2)

            form_fields = _extract_form_fields(soup)
            post_data = {
                '__EVENTTARGET': event_target,
                '__EVENTARGUMENT': event_arg,
            }
            post_data.update(form_fields)

            time.sleep(random.uniform(1.5, 3.0))

            try:
                response = session.post(base_url, data=post_data, timeout=30)
                response.raise_for_status()
                return BeautifulSoup(response.text, "lxml")
            except Exception as e:
                logger.error(f"    Failed to navigate to next page: {e}")
                return None

    # Method 2: Look for regular href pagination
    for link in soup.find_all('a', href=True):
        text = link.get_text(strip=True).lower()
        if text in ['next', '>', '>>', 'next page', '→', 'next »']:
            href = link['href']
            if href.startswith('http'):
                url = href
            else:
                url = f"https://eprocure.gov.in{href}"

            time.sleep(random.uniform(1.5, 3.0))
            try:
                response = session.get(url, timeout=30)
                response.raise_for_status()
                return BeautifulSoup(response.text, "lxml")
            except Exception as e:
                logger.error(f"    Failed to follow next link: {e}")
                return None

    return None
