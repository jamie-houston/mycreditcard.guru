"""Import statement-credit usage history from a JSON file.

The scorecard (`/scorecard/`) can only be checked against real data if a
year of real usage can get into UserCreditUsage, and the card modal only
records the current period as a bool. This loads a hand-built list instead:

    [{"card": "the-platinum-card-from-american-express", "owner": "Jamie",
      "credit": "resy", "period": "2026-Q4", "amount": 61.73}, ...]

- `card` + `owner` resolve to an OPEN UserCard (catalog slug, entity name).
- `credit` resolves to that card's active CardCredit: an exact spending-credit
  name or category slug first, else a case-insensitive substring of the
  description that matches exactly one credit.
- `period` must be in the credit's own scheme (YYYY-MM, YYYY-Qn, YYYY-Hn, YYYY).
- Rows that share a (credit, period) are summed — a statement can post one
  credit in two pieces. The total is SET, not added, so a rerun is idempotent.

An unresolved row is reported by name and skipped, never dropped silently —
the same contract seed_profile keeps. The real file is gitignored; see
data/local/seed/example-credits.json for the format.
"""
import json
import os
import re
from collections import defaultdict
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from cards.models import UserCard, UserCreditUsage, UserSpendingProfile

PERIOD_PATTERNS = {
    12: r'\d{4}-(0[1-9]|1[0-2])',
    4: r'\d{4}-Q[1-4]',
    2: r'\d{4}-H[12]',
}
ANNUAL_PATTERN = r'\d{4}'


def resolve_credit(card, key):
    """The card's active credit named by `key`, or (None, why)."""
    credits = list(card.credits.filter(is_active=True).select_related(
        'spending_credit', 'category'))
    key = key.strip().lower()
    exact = [c for c in credits
             if (c.spending_credit and c.spending_credit.name.lower() == key)
             or (c.category and c.category.slug.lower() == key)]
    if len(exact) == 1:
        return exact[0], None
    if len(exact) > 1:
        return None, f"'{key}' names {len(exact)} credits on {card.slug}"
    by_description = [c for c in credits if key in c.description.lower()]
    if len(by_description) == 1:
        return by_description[0], None
    if by_description:
        return None, f"'{key}' matches {len(by_description)} credit descriptions on {card.slug}"
    return None, f"no credit '{key}' on {card.slug}"


class Command(BaseCommand):
    help = 'Import statement-credit usage history (amounts per period) from a JSON file'

    def add_arguments(self, parser):
        parser.add_argument('--file', type=str, required=True,
                            help='Path to the usage JSON list')
        parser.add_argument('--username', type=str, required=True,
                            help='User whose profile receives the usage')

    def handle(self, *args, **options):
        file_path = options['file']
        if not os.path.exists(file_path):
            raise CommandError(f'Usage file not found: {file_path}')
        with open(file_path) as f:
            rows = json.load(f)
        if not isinstance(rows, list):
            raise CommandError('Usage file must be a JSON list of rows')

        try:
            user = User.objects.get(username=options['username'])
        except User.DoesNotExist:
            raise CommandError(f"No user '{options['username']}'")
        profile, _ = UserSpendingProfile.objects.get_or_create(user=user)

        totals = defaultdict(Decimal)
        credits = {}
        skipped = []
        for row in rows:
            label = (f"{row.get('card')} / {row.get('owner')} / "
                     f"{row.get('credit')} / {row.get('period')}")
            credit, why = self._resolve(user, row)
            if credit is None:
                skipped.append((label, why))
                continue
            credits[credit.id] = credit
            totals[(credit.id, row['period'])] += Decimal(str(row['amount']))

        with transaction.atomic():
            for (credit_id, period), amount in totals.items():
                UserCreditUsage.objects.update_or_create(
                    profile=profile, card_credit=credits[credit_id], period_key=period,
                    defaults={'used': True, 'amount_used': amount})

        self.stdout.write(self.style.SUCCESS(
            f'{len(rows) - len(skipped)} rows imported into {len(totals)} credit periods '
            f"for '{user.username}'"))
        if skipped:
            self.stdout.write(self.style.WARNING(f'  {len(skipped)} rows skipped:'))
            for label, why in skipped:
                self.stdout.write(f'    - {label}: {why}')

    def _resolve(self, user, row):
        missing = [k for k in ('card', 'owner', 'credit', 'period', 'amount') if row.get(k) in (None, '')]
        if missing:
            return None, f"missing {', '.join(missing)}"
        try:
            amount = Decimal(str(row['amount']))
        except Exception:
            return None, f"amount '{row['amount']}' is not a number"
        if not amount.is_finite() or amount < 0:
            return None, f"amount {row['amount']} is negative"

        holding = UserCard.objects.filter(
            user=user, card__slug=row['card'], owner__name=row['owner'],
            closed_date__isnull=True).select_related('card').first()
        if holding is None:
            return None, f"no open {row['card']} owned by '{row['owner']}'"

        credit, why = resolve_credit(holding.card, row['credit'])
        if credit is None:
            return None, why

        pattern = PERIOD_PATTERNS.get(credit.times_per_year, ANNUAL_PATTERN)
        if not re.fullmatch(pattern, row['period']):
            return None, (f"period '{row['period']}' is not in this credit's scheme "
                          f"({credit.times_per_year}x/yr)")
        return credit, None
