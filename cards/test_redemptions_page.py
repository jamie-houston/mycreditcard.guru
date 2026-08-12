"""Story 12: the /redemptions/ page renders its curated ladders.

cards/test_smoke_routes.py already asserts this route returns 200, but it does
so against an empty database — which exercises only the "nothing curated yet"
branch. These tests cover the branch that actually ships content.
"""

from allauth.socialaccount.models import SocialApp
from django.conf import settings
from django.contrib.sites.models import Site
from django.test import TestCase
from django.urls import reverse

from .models import PointsProgram


class RedemptionsPageTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        # base.html 500s for logged-out visitors without a Google SocialApp
        # row — same fixture, and same reason, as test_smoke_routes.py.
        social_app = SocialApp.objects.create(
            provider='google', name='Google',
            client_id='redemptions-test-client-id', secret='redemptions-test-secret')
        social_app.sites.add(Site.objects.get(pk=settings.SITE_ID))

        cls.curated = PointsProgram.objects.create(
            name='Curated Program', slug='curated_program',
            portal_url='https://example.com/portal',
            transfer_partners=['World of Hyatt'],
            note='A curated program.',
            redemption_methods=[
                {'method': 'Transfer to World of Hyatt', 'cpp': 2.0,
                 'verdict': 'best', 'note': 'The good door.'},
                {'method': 'Cash out', 'cpp': 0.6,
                 'verdict': 'worst', 'note': 'The bad door.'},
            ])

        cls.bare = PointsProgram.objects.create(
            name='Bare Program', slug='bare_program', note='No ladder curated.')

    def test_page_renders_the_ladder_in_order(self):
        response = self.client.get(reverse('redemptions'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'redemptions.html')

        body = response.content.decode()
        self.assertIn('Transfer to World of Hyatt', body)
        self.assertIn('Cash out', body)
        self.assertLess(
            body.index('Transfer to World of Hyatt'), body.index('Cash out'),
            "Ladder must render best-to-worst, in the order it is stored")

    def test_page_states_the_figures_are_estimates(self):
        """The story requires the estimate caveat near the top — these are
        curated numbers, and presenting them as precise would undercut the
        project's trustworthy-math promise."""
        body = self.client.get(reverse('redemptions')).content.decode()
        self.assertIn('estimates', body)

    def test_program_without_a_ladder_is_omitted(self):
        body = self.client.get(reverse('redemptions')).content.decode()
        self.assertIn('Curated Program', body)
        self.assertNotIn('Bare Program', body)

    def test_malformed_rungs_are_dropped_rather_than_rendered(self):
        PointsProgram.objects.create(
            name='Messy Program', slug='messy_program',
            redemption_methods=['not a dict', {'cpp': 1.0}, {'method': 'Real door'}])
        body = self.client.get(reverse('redemptions')).content.decode()
        self.assertIn('Real door', body)
        self.assertNotIn('not a dict', body)

    def test_a_program_whose_rungs_are_all_malformed_is_omitted(self):
        PointsProgram.objects.create(
            name='Entirely Messy Program', slug='entirely_messy_program',
            redemption_methods=['not a dict', {'cpp': 1.0}])
        body = self.client.get(reverse('redemptions')).content.decode()
        self.assertNotIn('Entirely Messy Program', body)

    def test_curated_method_text_is_escaped(self):
        PointsProgram.objects.create(
            name='XSS Program', slug='xss_program',
            redemption_methods=[{'method': '<script>alert(1)</script>', 'cpp': 1.0}])
        body = self.client.get(reverse('redemptions')).content.decode()
        self.assertNotIn('<script>alert(1)</script>', body)
        self.assertIn('&lt;script&gt;', body)
