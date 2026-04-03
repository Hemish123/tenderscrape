# tenders/scrapers/__init__.py
"""
Scraper orchestration module.
Provides run_all_scrapers() to execute all state scrapers with error isolation.
"""

import logging

logger = logging.getLogger('scrapers')


def run_all_scrapers():
    """
    Run all tender scrapers sequentially.
    Each scraper is isolated — failure in one does not affect others.
    Returns a summary dict with results per state.
    """
    results = {}

    scrapers = [
        ("Gujarat", "tenders.scrapers.gil", "scrape_gil"),
        ("Maharashtra", "tenders.scrapers.maharashtra", "scrape_maharashtra"),
        ("Madhya Pradesh", "tenders.scrapers.madhya_pradesh", "scrape_madhya_pradesh"),
        ("Rajasthan", "tenders.scrapers.rajasthan", "scrape_rajasthan"),
        ("Karnataka", "tenders.scrapers.karnataka", "scrape_karnataka"),
    ]

    for state_name, module_path, func_name in scrapers:
        try:
            logger.info(f"{'='*50}")
            logger.info(f"Running scraper: {state_name}")
            logger.info(f"{'='*50}")

            # Dynamic import to avoid circular imports
            import importlib
            module = importlib.import_module(module_path)
            scraper_func = getattr(module, func_name)

            count = scraper_func()
            results[state_name] = {"status": "success", "new_tenders": count or 0}
            logger.info(f"✅ {state_name}: completed successfully")

        except Exception as e:
            results[state_name] = {"status": "error", "error": str(e)}
            logger.error(f"❌ {state_name}: scraper failed — {e}")

    # Print summary
    logger.info(f"\n{'='*50}")
    logger.info("SCRAPING SUMMARY")
    logger.info(f"{'='*50}")
    for state, result in results.items():
        if result["status"] == "success":
            logger.info(f"  ✅ {state}: {result['new_tenders']} new tenders")
        else:
            logger.info(f"  ❌ {state}: FAILED — {result['error']}")

    return results
