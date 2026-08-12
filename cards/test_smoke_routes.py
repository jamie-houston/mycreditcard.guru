"""Smoke tests: every page route renders and returns 200.

These exist because `ba84170` fixed two pages (`/categories/<slug>/` and
`/issuers/`) that had been hard-500ing on every request — both templates used
`{% static %}` without `{% load static %}`, which raises TemplateSyntaxError at
render time. All four verification gates stayed green throughout, because none
of them requests a URL. A template that fails to *render* is invisible to tests
that only exercise models, serializers and the engine.

Status codes only. Page content belongs to tests/e2e/ and the manual passes;
asserting on it here would make this a brittle second copy of those.
"""

import uuid

from allauth.socialaccount.models import SocialApp
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.test import TestCase
from django.urls import get_resolver, reverse
from django.urls.resolvers import URLPattern

from .models import SpendingCategory, UserSpendingProfile
from roadmaps.models import Roadmap

# Root-level named routes that are not pages, and so are out of scope here.
# The API routes under api/cards/, api/roadmaps/ and api/users/ are URLResolver
# includes and drop out on their own; `api_home` is a bare path() at the root
# and has to be named explicitly.
NON_PAGE_ROUTE_NAMES = {'api_home'}

# `wallet` is the one page route that requires a login. It has no
# `login_required` decorator — cards/wallet.py:94 redirects by hand — which is
# why a grep for the decorator says every page is anonymous.
LOGIN_REQUIRED_ROUTE_NAMES = {'wallet'}


class PageRouteSmokeTests(TestCase):
    """Every page route returns 200.

    The three routes taking an argument get real objects: a bogus share UUID or
    category slug takes the 404 branch, which renders a *different* template —
    the page's own template would never execute and the check would pass while
    the page was broken.
    """

    @classmethod
    def setUpTestData(cls):
        cls.category = SpendingCategory.objects.create(
            name='dining', slug='dining', display_name='Dining')

        cls.profile = UserSpendingProfile.objects.create(
            privacy_setting='public', share_uuid=uuid.uuid4())

        cls.roadmap = Roadmap.objects.create(
            profile=cls.profile, name='Shared roadmap',
            privacy_setting='public', share_uuid=uuid.uuid4())

        cls.user = User.objects.create_user(username='smoke', password='smoke-pw')

        # base.html:53 calls {% provider_login_url 'google' %} for logged-out
        # visitors, and that tag raises SocialApp.DoesNotExist if no Google
        # SocialApp row exists — taking down every page that extends base.html.
        # Real deployments have this row (it is what makes Google login work);
        # a fresh test DB does not, so create it.
        social_app = SocialApp.objects.create(
            provider='google', name='Google',
            client_id='smoke-test-client-id', secret='smoke-test-secret')
        social_app.sites.add(Site.objects.get(pk=settings.SITE_ID))

    def covered_routes(self):
        """{route name: reverse() args} — the set this test class covers."""
        return {
            'landing': {},
            'roadmap': {},
            'cards_list': {},
            'categories_list': {},
            'category_detail': {'category_slug': self.category.slug},
            'issuers_list': {},
            'profile': {},
            'wallet': {},
            'help': {},
            'resources': {},
            'redemptions': {},
            'shared_profile': {'share_uuid': self.profile.share_uuid},
            'shared_roadmap': {'share_uuid': self.roadmap.share_uuid},
        }

    def test_every_page_route_returns_200(self):
        for name, kwargs in self.covered_routes().items():
            with self.subTest(route=name):
                if name in LOGIN_REQUIRED_ROUTE_NAMES:
                    self.client.force_login(self.user)
                else:
                    self.client.logout()
                response = self.client.get(reverse(name, kwargs=kwargs))
                self.assertEqual(
                    response.status_code, 200,
                    f"Page route '{name}' returned {response.status_code}, not 200")

    def test_login_required_pages_redirect_when_anonymous(self):
        """Pins the other half of `wallet`'s contract, so a page can't quietly
        stop being gated (or start being gated) without this suite noticing."""
        for name in LOGIN_REQUIRED_ROUTE_NAMES:
            with self.subTest(route=name):
                response = self.client.get(reverse(name, kwargs=self.covered_routes()[name]))
                self.assertEqual(response.status_code, 302)

    def test_shared_pages_render_their_own_template(self):
        """Guards the fixtures above: if a shared page ever silently 404s, the
        200 assertion would still pass on the error template. Pin the template
        so that can't happen."""
        for name, kwargs, template in [
            ('shared_profile', {'share_uuid': self.profile.share_uuid},
             'shared_profile.html'),
            ('shared_roadmap', {'share_uuid': self.roadmap.share_uuid},
             'shared_roadmap.html'),
        ]:
            with self.subTest(route=name):
                response = self.client.get(reverse(name, kwargs=kwargs))
                self.assertTemplateUsed(response, template)

    def test_route_list_is_not_stale(self):
        """An explicit list stops covering the app the moment someone adds a
        thirteenth page route. Walk the root URLconf and assert the covered set
        is exactly the app's named page routes."""
        page_route_names = {
            pattern.name
            for pattern in get_resolver().url_patterns
            # URLResolver entries are the admin/, accounts/ and api/ includes.
            if isinstance(pattern, URLPattern) and pattern.name
        } - NON_PAGE_ROUTE_NAMES

        covered = set(self.covered_routes())

        self.assertEqual(
            page_route_names, covered,
            "Page routes and smoke-tested routes have diverged. "
            f"Not smoke-tested: {sorted(page_route_names - covered)}. "
            f"Covered but no longer a page route: {sorted(covered - page_route_names)}.")
