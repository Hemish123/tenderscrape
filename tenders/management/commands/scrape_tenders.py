# tenders/management/commands/scrape_tenders.py
"""
Django management command to run all tender scrapers.
Usage: python manage.py scrape_tenders
"""

from django.core.management.base import BaseCommand
from tenders.scrapers import run_all_scrapers


class Command(BaseCommand):
    help = "Scrape tenders from all configured state portals"

    def add_arguments(self, parser):
        parser.add_argument(
            '--state',
            type=str,
            help='Run scraper for a specific state only (Gujarat, Maharashtra, etc.)',
        )

    def handle(self, *args, **kwargs):
        state = kwargs.get('state')

        if state:
            # Run a single state scraper
            state_map = {
                'gujarat': ('tenders.scrapers.gil', 'scrape_gil'),
                'maharashtra': ('tenders.scrapers.maharashtra', 'scrape_maharashtra'),
                'madhya_pradesh': ('tenders.scrapers.madhya_pradesh', 'scrape_madhya_pradesh'),
                'rajasthan': ('tenders.scrapers.rajasthan', 'scrape_rajasthan'),
                'karnataka': ('tenders.scrapers.karnataka', 'scrape_karnataka'),
            }
            key = state.lower().replace(' ', '_')
            if key in state_map:
                import importlib
                module_path, func_name = state_map[key]
                module = importlib.import_module(module_path)
                scraper_func = getattr(module, func_name)
                scraper_func()
                self.stdout.write(self.style.SUCCESS(f"✅ {state} scraper completed"))
            else:
                self.stderr.write(self.style.ERROR(
                    f"Unknown state: {state}. Available: {', '.join(state_map.keys())}"
                ))
        else:
            # Run all scrapers
            self.stdout.write("Starting all scrapers...\n")
            results = run_all_scrapers()

            for state_name, result in results.items():
                if result['status'] == 'success':
                    self.stdout.write(self.style.SUCCESS(
                        f"  ✅ {state_name}: {result['new_tenders']} new tenders"
                    ))
                else:
                    self.stdout.write(self.style.ERROR(
                        f"  ❌ {state_name}: {result['error']}"
                    ))

            self.stdout.write(self.style.SUCCESS("\n🎉 All scrapers completed!"))