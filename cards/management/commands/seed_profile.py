"""Seed a real logged-in household profile from a card file.

Development tool, not a product feature. Every manual browser pass needs a
household with several entities, business cards, closed cards and real open
dates; hand-building that through the UI before each pass is why passes get
run against thin, unrepresentative data.

Unlike run_scenario, this binds to the REAL imported catalog by slug and to a
real named User, and leaves an unknown opened_date null — defaulting a 2007
Chase Freedom to six months ago silently corrupts every 5/24 number on the
page.
"""
import glob
import json
import os
import secrets
from datetime import date

from django.conf import settings
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from cards.models import (
    CreditCard, ProfileEntity, SpendingAmount, SpendingCategory,
    SpendingCredit, UserCard, UserSpendingCreditPreference,
    UserSpendingProfile,
)

SCENARIO_DIR = 'data/tests/scenarios'


class Command(BaseCommand):
    help = 'Seed a logged-in household profile from a seed card file (DEBUG only)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file', type=str, default='data/local/seed/jamie.json',
            help='Path to the seed JSON file')
        parser.add_argument(
            '--username', type=str, default=None,
            help="Username to seed (default: the file's \"username\", else 'jamie')")
        parser.add_argument(
            '--password', type=str, default=None,
            help='Password for the seeded user (else $SEED_PASSWORD, else generated)')

    def handle(self, *args, **options):
        # This creates a login and overwrites profile data; it has no business
        # running against production.
        if not settings.DEBUG:
            raise CommandError(
                'seed_profile refuses to run with DEBUG=False — it creates a '
                'login and overwrites profile data.')

        file_path = options['file']
        if not os.path.exists(file_path):
            raise CommandError(
                f'Seed file not found: {file_path}\n'
                f'The real portfolio is gitignored; see data/local/seed/example.json '
                f'for the format.')

        with open(file_path) as f:
            seed = json.load(f)

        username = options['username'] or seed.get('username') or 'jamie'
        password = options['password'] or os.environ.get('SEED_PASSWORD')
        generated = password is None
        if generated:
            password = secrets.token_urlsafe(12)

        with transaction.atomic():
            user, user_created = User.objects.get_or_create(
                username=username, defaults={'email': f'{username}@example.com'})
            user.set_password(password)
            user.save()

            profile, _ = UserSpendingProfile.objects.get_or_create(user=user)

            # Order matters: UserCard has a RESTRICT FK to ProfileEntity, so
            # the cards must go before the entities they point at.
            UserCard.objects.filter(user=user).delete()
            ProfileEntity.objects.filter(profile=profile).delete()
            SpendingAmount.objects.filter(profile=profile).delete()
            UserSpendingCreditPreference.objects.filter(profile=profile).delete()

            entities = self._create_entities(profile, seed)
            created, skipped = self._create_cards(user, seed, entities)
            categories, credits = self._create_spending(profile, seed)

        self._report(username, password, generated, user_created,
                     entities, created, skipped, categories, credits)

    def _create_entities(self, profile, seed):
        entities = {}
        for spec in seed['entities']:
            entities[spec['name']] = ProfileEntity.objects.create(
                profile=profile,
                name=spec['name'],
                kind=spec.get('kind', 'personal'),
                is_primary=spec.get('primary', False),
            )
        if not any(e.is_primary for e in entities.values()):
            raise CommandError(
                'Seed file declares no primary entity — exactly one entity '
                'needs "primary": true.')
        return entities

    def _create_cards(self, user, seed, entities):
        created, skipped = [], []
        for spec in seed['cards']:
            slug = spec['card']
            nickname = spec.get('nickname', '')
            label = f'{nickname} ({slug})' if nickname else slug

            card = CreditCard.objects.filter(slug=slug).first()
            if card is None:
                # A silently short portfolio is a wrong fixture.
                skipped.append((label, 'no card in the catalog with that slug'))
                continue

            owner_name = spec['owner']
            if owner_name not in entities:
                raise CommandError(
                    f"Card {label} names owner '{owner_name}', which is not a "
                    f"declared entity (known: {sorted(entities)})")

            UserCard.objects.create(
                user=user,
                card=card,
                owner=entities[owner_name],
                nickname=nickname,
                opened_date=self._parse_date(spec.get('opened_date'), label, 'opened_date'),
                closed_date=self._parse_date(spec.get('closed_date'), label, 'closed_date'),
                bonus_earned_date=self._parse_date(
                    spec.get('bonus_earned_date'), label, 'bonus_earned_date'),
                notes=spec.get('note', ''),
            )
            created.append(label)

        for spec in seed.get('skipped_cards', []):
            skipped.append((spec['nickname'], spec['reason']))
        return created, skipped

    def _parse_date(self, value, label, field):
        if not value:
            return None
        try:
            return date.fromisoformat(value)
        except ValueError:
            raise CommandError(
                f'Card {label} has an unparseable {field}: {value!r} '
                f'(expected YYYY-MM-DD)')

    def _create_spending(self, profile, seed):
        """Spending comes from a scenario file, never copied into the seed.

        data/tests/scenarios/ already owns the real monthly numbers and is
        exercised by the test suite, so the two can't drift.
        """
        scenario_name = seed['spending_from_scenario']
        scenario = self._find_scenario(scenario_name)
        user_profile = scenario['user_profile']

        categories = 0
        for slug, amount in user_profile['spending'].items():
            category = SpendingCategory.objects.filter(slug=slug).first()
            if category is None:
                raise CommandError(
                    f"Scenario '{scenario_name}' spends on category '{slug}', "
                    f"which is not a SpendingCategory — import categories first "
                    f"(manage.py import_cards data/input/system/spending_categories.json)")
            SpendingAmount.objects.create(
                profile=profile, category=category, monthly_amount=amount)
            categories += 1

        credits = 0
        for slug in user_profile.get('spending_credit_preferences', []):
            credit = SpendingCredit.objects.filter(slug=slug).first()
            if credit is None:
                raise CommandError(
                    f"Scenario '{scenario_name}' prefers credit '{slug}', which "
                    f"is not a SpendingCredit — run manage.py import_spending_credits")
            UserSpendingCreditPreference.objects.create(
                profile=profile, spending_credit=credit, values_credit=True)
            credits += 1

        return categories, credits

    def _find_scenario(self, name):
        for path in sorted(glob.glob(os.path.join(SCENARIO_DIR, '*.json'))):
            with open(path) as f:
                data = json.load(f)
            for scenario in data.get('scenarios', []):
                if scenario.get('name') == name:
                    return scenario
        raise CommandError(
            f"No scenario named '{name}' in {SCENARIO_DIR}/*.json")

    def _report(self, username, password, generated, user_created,
                entities, created, skipped, categories, credits):
        out, style = self.stdout, self.style
        out.write(style.SUCCESS(
            f"{'Created' if user_created else 'Reused'} user '{username}'"))
        if generated:
            out.write(style.WARNING(f'  generated password: {password}'))
        out.write(f'  {len(entities)} entities: {", ".join(entities)}')
        out.write(f'  {len(created)} cards')
        out.write(f'  {categories} spending categories, {credits} credit preferences')

        if skipped:
            out.write(style.WARNING(f'  {len(skipped)} cards skipped:'))
            for label, reason in skipped:
                out.write(style.WARNING(f'    - {label}: {reason}'))
