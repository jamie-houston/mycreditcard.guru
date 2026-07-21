import os
import pytest
from django.core.management import call_command
from django.conf import settings
from django.contrib.sites.models import Site
from allauth.socialaccount.models import SocialApp
from cards.models import SpendingCategory

# Allow Django ORM access when Playwright runs async event loops in background
os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def seed_test_data(db):
    """Seed SocialApp and initial card data into test DB for each test."""
    site = Site.objects.get_current()
    app, _ = SocialApp.objects.get_or_create(
        provider='google',
        defaults={
            'name': 'Google',
            'client_id': 'test-client-id',
            'secret': 'test-secret',
        }
    )
    if site not in app.sites.all():
        app.sites.add(site)

    # Load system data & verified card data if not present
    if not SpendingCategory.objects.exists():
        system_files = [
            'data/input/system/spending_categories.json',
            'data/input/system/issuers.json',
            'data/input/system/reward_types.json',
            'data/input/system/points_programs.json',
        ]
        for file_path in system_files:
            abs_path = os.path.join(settings.BASE_DIR, file_path)
            if os.path.exists(abs_path):
                call_command('import_cards', abs_path)

        card_files = [
            os.path.join(settings.BASE_DIR, 'data/input/cards/chase.json'),
            os.path.join(settings.BASE_DIR, 'data/input/cards/american_express.json'),
        ]
        for card_file in card_files:
            if os.path.exists(card_file):
                call_command('import_cards', card_file)


@pytest.fixture
def page_with_js_error_tracker(page):
    """Fixture that wraps Playwright page and tracks uncaught JS errors or console errors."""
    page_errors = []
    console_errors = []

    def on_page_error(error):
        page_errors.append(error)

    def on_console(msg):
        if msg.type == "error":
            text = msg.text
            if "favicon.ico" not in text and "net::ERR_FILE_NOT_FOUND" not in text:
                console_errors.append(text)

    page.on("pageerror", on_page_error)
    page.on("console", on_console)

    page.js_errors = page_errors
    page.console_errors = console_errors
    return page
