# tenders/tasks.py
"""
Celery tasks for the tenders app.
Provides background task for running all scrapers.
"""

import logging
from celery import shared_task

logger = logging.getLogger('scrapers')


@shared_task(bind=True, max_retries=2, default_retry_delay=300)
def scrape_all_tenders(self):
    """
    Celery task to run all tender scrapers.
    Scheduled to run every 6 hours via Celery Beat.
    Can also be triggered manually: scrape_all_tenders.delay()
    """
    try:
        logger.info("=" * 60)
        logger.info("CELERY TASK: Starting scheduled tender scraping...")
        logger.info("=" * 60)

        from tenders.scrapers import run_all_scrapers
        results = run_all_scrapers()

        # Count totals
        total_new = sum(
            r.get('new_tenders', 0)
            for r in results.values()
            if r.get('status') == 'success'
        )
        failed = sum(
            1 for r in results.values()
            if r.get('status') == 'error'
        )

        logger.info(f"CELERY TASK: Scraping complete — {total_new} new tenders, {failed} failures")
        return {
            'total_new': total_new,
            'failed_scrapers': failed,
            'details': results,
        }

    except Exception as exc:
        logger.error(f"CELERY TASK: Scraping failed — {exc}")
        raise self.retry(exc=exc)
