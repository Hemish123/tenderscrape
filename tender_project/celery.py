# tender_project/celery.py
"""
Celery configuration for the tender_project.
Sets up the Celery app with Django integration and Beat schedule.
"""

import os
from celery import Celery
from celery.schedules import crontab

# Set Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tender_project.settings')

app = Celery('tender_project')

# Load config from Django settings, namespaced with CELERY_
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks in all installed apps
app.autodiscover_tasks()

# Celery Beat schedule — scrape every 6 hours
app.conf.beat_schedule = {
    'scrape-all-tenders-every-6-hours': {
        'task': 'tenders.tasks.scrape_all_tenders',
        'schedule': crontab(minute=0, hour='*/6'),  # Every 6 hours
        'options': {'expires': 3600 * 5},  # Expire if not run within 5 hours
    },
}
app.conf.timezone = 'Asia/Kolkata'


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Debug task to verify Celery is working."""
    print(f'Request: {self.request!r}')
