import os
import sys
import io
import pytest
from django.core.management import call_command
from django.conf import settings
from django.contrib.sites.models import Site
from django.contrib.auth.models import User
from django.test import Client
from allauth.socialaccount.models import SocialApp
from cards.models import SpendingCategory

os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def seed_test_data(db):
    """Seed SocialApp and system card data silently for test cases."""
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

    # Fast seed if empty
    if not SpendingCategory.objects.exists():
        suppress_out = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = suppress_out
        try:
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
        finally:
            sys.stdout = old_stdout


@pytest.fixture
def page_with_js_error_tracker(page):
    """Fixture that wraps Playwright page and tracks uncaught JS errors."""
    page_errors = []
    console_errors = []

    def on_page_error(error):
        page_errors.append(error)

    def on_console(msg):
        if msg.type == "error":
            text = msg.text
            if not any(ignore in text for ignore in ["favicon.ico", "ERR_FILE_NOT_FOUND", "401", "Unauthorized"]):
                console_errors.append(text)

    page.on("pageerror", on_page_error)
    page.on("console", on_console)

    page.js_errors = page_errors
    page.console_errors = console_errors
    return page


@pytest.fixture
def authenticated_page(page_with_js_error_tracker, live_server):
    """Fixture that returns a Playwright page with a logged-in Django user session."""
    user, _ = User.objects.get_or_create(username="testuser", defaults={"email": "test@example.com"})
    user.set_password("password123")
    user.save()

    page = page_with_js_error_tracker
    page.goto(live_server.url + "/")

    client = Client()
    client.login(username="testuser", password="password123")
    session_cookie = client.cookies.get(settings.SESSION_COOKIE_NAME)

    if session_cookie:
        import urllib.parse
        parsed = urllib.parse.urlparse(live_server.url)
        page.context.add_cookies([{
            "name": settings.SESSION_COOKIE_NAME,
            "value": session_cookie.value,
            "domain": parsed.hostname,
            "path": "/",
        }])

    return page
