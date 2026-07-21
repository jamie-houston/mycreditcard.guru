"""
Django management command that audits the card catalog JSON files in
data/input/cards/*.json for defects BEFORE they get imported into the DB.

Scope: this command mirrors the exact lookup semantics of the real importer
(cards/management/commands/import_cards.py) so a clean run here is a
reliable predictor of what that importer will actually do. It catches two
classes of bug that have previously slipped into the catalog by hand:

  1. Duplicate credit line items within a single card's `credits` array
     (e.g. the same "Global Entry, TSA PreCheck, NEXUS Credit" $100 credit
     listed twice), which double-counts the credit toward the card's
     computed annual value.
  2. Credits, reward categories, or points programs that reference names /
     slugs / currency codes that don't exist in the DB. import_cards.py
     only WARNs about these and silently drops the offending row -- it
     never blocks the import -- so this command surfaces them loudly,
     before verified: true gets flipped, instead of after.

Explicitly OUT of scope: this command cannot tell you whether a dollar
value is stale, or correctly transcribed from the issuer's real, current
terms. That is a data-accuracy problem, not a referential-integrity or
duplication problem, and still needs a human to check the issuer's
website. A clean ("PASS") run here means "the data is internally
consistent and will import faithfully" -- not "the numbers are still
correct."

This command is read-only: it never writes to the database and never
modifies the JSON files. All lookups are read-only Django ORM queries
against whatever reference data (issuers, spending categories, reward
types, points programs, spending credits) is already loaded in the dev
DB -- run `setup_data.py` / the seed import commands first if that data
isn't loaded yet.

Usage:
    python manage.py validate_cards
    python manage.py validate_cards --issuer american_express.json
    python manage.py validate_cards --errors-only

Exit code: 0 if no FAILs were found anywhere in the run, 1 otherwise --
suitable for use as a CI / pre-import gate (not currently wired into
import_cards.py itself).
"""
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from cards.models import Issuer, PointsProgram, RewardType, SpendingCategory, SpendingCredit
from cards.valuations import UNMAPPED_CURRENCY_RATE

CARDS_DIR: Path = settings.BASE_DIR / 'data' / 'input' / 'cards'

# personal.json is a dict of owned-card ownership records, not a card
# catalog array -- it has a completely different shape and is handled by
# import_cards.py's import_personal_cards(), not import_credit_cards().
EXCLUDED_FILES = {'personal.json'}


class Command(BaseCommand):
    help = (
        'Audit data/input/cards/*.json catalog files for duplicate credits and '
        'broken references before they are imported (read-only, does not touch the DB)'
    )

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            '--issuer',
            type=str,
            default=None,
            help='Only audit one issuer catalog file, e.g. --issuer american_express.json. '
                 'Accepts a bare filename or a path; resolved relative to data/input/cards/.'
        )
        parser.add_argument(
            '--errors-only',
            action='store_true',
            help='Suppress PASS and WARN lines; only print cards that have a FAIL.'
        )

    def handle(self, *args, **options) -> None:
        errors_only: bool = options['errors_only']
        files = self._catalog_files(options.get('issuer'))

        self._load_reference_data()

        overall_pass = overall_warn = overall_fail = 0
        overall_cards = 0
        any_fail = False

        for path in files:
            try:
                with open(path, 'r') as f:
                    data = json.load(f)
            except json.JSONDecodeError as e:
                self.stdout.write(self.style.ERROR(f'{path.name}: invalid JSON - {e}'))
                any_fail = True
                continue

            if not isinstance(data, list):
                self.stdout.write(
                    self.style.ERROR(
                        f'{path.name}: expected a JSON array of cards, got {type(data).__name__} '
                        f'-- is this actually a card catalog file?'
                    )
                )
                any_fail = True
                continue

            self.stdout.write('')
            self.stdout.write(self.style.MIGRATE_HEADING(f'=== {path.name} ({len(data)} cards) ==='))

            slug_counts = self._slug_counts(data)
            file_pass = file_warn = file_fail = 0

            for card_data in data:
                if not isinstance(card_data, dict):
                    self.stdout.write(self.style.ERROR(f'[FAIL] (malformed entry, not an object: {card_data!r})'))
                    file_fail += 1
                    any_fail = True
                    continue

                status, fails, warns, name, annual_fee = self._validate_card(card_data, slug_counts)
                overall_cards += 1
                if status == 'FAIL':
                    file_fail += 1
                    any_fail = True
                elif status == 'WARN':
                    file_warn += 1
                else:
                    file_pass += 1

                if errors_only and status != 'FAIL':
                    continue

                fee_display = f'${annual_fee:,.0f}' if annual_fee is not None else '(no/invalid fee)'
                line = f'[{status}] {name} — {fee_display}'
                if status == 'FAIL':
                    self.stdout.write(self.style.ERROR(line))
                elif status == 'WARN':
                    self.stdout.write(self.style.WARNING(line))
                else:
                    self.stdout.write(self.style.SUCCESS(line))

                for reason in fails:
                    self.stdout.write(self.style.ERROR(f'    FAIL: {reason}'))
                for reason in warns:
                    self.stdout.write(self.style.WARNING(f'    WARN: {reason}'))

            overall_pass += file_pass
            overall_warn += file_warn
            overall_fail += file_fail

            self.stdout.write(f'  -- {path.name}: {file_pass} pass, {file_warn} warn, {file_fail} fail')

        self.stdout.write('')
        self.stdout.write(self.style.MIGRATE_HEADING('=== Summary ==='))
        self.stdout.write(f'Scanned {overall_cards} card(s) across {len(files)} file(s)')
        self.stdout.write(f'  Pass: {overall_pass}')
        self.stdout.write(f'  Warn: {overall_warn}')
        self.stdout.write(f'  Fail: {overall_fail}')

        if any_fail:
            self.stdout.write(self.style.ERROR('Result: FAIL - one or more cards have blocking issues'))
            sys.exit(1)
        else:
            self.stdout.write(self.style.SUCCESS('Result: PASS - no blocking issues found'))

    # -- File resolution ---------------------------------------------------

    def _catalog_files(self, issuer_arg: Optional[str]) -> List[Path]:
        """Resolve the list of catalog files to audit.

        With no --issuer, every *.json file under data/input/cards/ except
        personal.json. With --issuer, a single file, accepting either a
        bare filename (with or without .json) or a path, resolved relative
        to data/input/cards/ if it isn't found as given.
        """
        if not issuer_arg:
            return sorted(p for p in CARDS_DIR.glob('*.json') if p.name not in EXCLUDED_FILES)

        given = Path(issuer_arg)
        candidates = [given, CARDS_DIR / given.name]
        if given.suffix != '.json':
            candidates.append(Path(f'{given}.json'))
            candidates.append(CARDS_DIR / f'{given.name}.json')

        for candidate in candidates:
            if candidate.is_file():
                if candidate.name in EXCLUDED_FILES:
                    raise CommandError(
                        f'{candidate.name} is not a card catalog file -- it holds personal '
                        f'ownership records, not cards, so there is nothing for this command to audit.'
                    )
                return [candidate]

        raise CommandError(f'Could not find issuer file "{issuer_arg}" (looked in {CARDS_DIR})')

    @staticmethod
    def _slug_counts(cards: List[Any]) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for card_data in cards:
            if not isinstance(card_data, dict):
                continue
            slug = card_data.get('slug')
            if slug:
                counts[slug] = counts.get(slug, 0) + 1
        return counts

    # -- Reference data ------------------------------------------------------

    def _load_reference_data(self) -> None:
        """Pull every reference table this audit resolves against, once, up front.

        Read-only queries -- these mirror exactly what import_cards.py looks
        up at import time (see module docstring), just batched instead of
        queried card-by-card.
        """
        self.issuer_names = set(Issuer.objects.values_list('name', flat=True))
        self.reward_type_names = set(RewardType.objects.values_list('name', flat=True))
        self.category_names = set(SpendingCategory.objects.values_list('name', flat=True))
        self.category_names_lower = {n.lower() for n in self.category_names}
        self.category_slugs = set(SpendingCategory.objects.values_list('slug', flat=True))
        self.spending_credit_names = set(SpendingCredit.objects.values_list('name', flat=True))
        self.points_program_slugs = set(PointsProgram.objects.values_list('slug', flat=True))
        self.currency_codes = {
            code.upper()
            for code in PointsProgram.objects.exclude(currency_code='').values_list('currency_code', flat=True)
        }

    # -- Per-card validation ---------------------------------------------------

    def _validate_card(
        self, card_data: Dict[str, Any], slug_counts: Dict[str, int]
    ) -> Tuple[str, List[str], List[str], str, Optional[float]]:
        """Validate one card dict against import_cards.py's exact semantics.

        Returns (status, fail_reasons, warn_reasons, display_name, annual_fee).
        """
        fails: List[str] = []
        warns: List[str] = []

        name = card_data.get('name') or '(unnamed card)'
        if not card_data.get('name'):
            fails.append('Missing or empty "name"')

        annual_fee = card_data.get('annual_fee')
        if not self._is_number(annual_fee):
            fails.append(f'"annual_fee" missing or not numeric (got {annual_fee!r})')
            annual_fee = None

        issuer_name = card_data.get('issuer')
        if not issuer_name or issuer_name not in self.issuer_names:
            fails.append(f'issuer {issuer_name!r} does not resolve to a known Issuer.name')

        reward_type_name = card_data.get('reward_type') or card_data.get('primary_reward_type')
        if not reward_type_name or reward_type_name not in self.reward_type_names:
            fails.append(
                f'reward_type/primary_reward_type {reward_type_name!r} does not resolve to a known RewardType.name'
            )

        reward_categories = card_data.get('reward_categories') or []
        if not reward_categories:
            fails.append('No reward_categories present')
        else:
            for i, rc in enumerate(reward_categories):
                if not isinstance(rc, dict):
                    fails.append(f'reward_categories[{i}] is not an object: {rc!r}')
                    continue
                if 'reward_rate' not in rc:
                    fails.append(
                        f'reward_categories[{i}] ("{rc.get("category", "?")}") missing required "reward_rate"'
                    )
                elif not self._is_number(rc['reward_rate']):
                    fails.append(
                        f'reward_categories[{i}] ("{rc.get("category", "?")}") has non-numeric '
                        f'reward_rate: {rc["reward_rate"]!r}'
                    )

                category_name = rc.get('category')
                if category_name and category_name not in self.category_names \
                        and category_name.lower() not in self.category_names_lower:
                    warns.append(
                        f'reward_categories[{i}].category "{category_name}" does not match any '
                        f'SpendingCategory.name, even case-insensitively -- import_cards.py will WARN and '
                        f'silently skip this reward category'
                    )

        credits_list = card_data.get('credits') or []
        for i, credit in enumerate(credits_list):
            if not isinstance(credit, dict):
                fails.append(f'credits[{i}] is not an object: {credit!r}')
                continue
            warns.extend(self._validate_credit(i, credit))

        for i, j, reason in self._find_duplicate_credits(credits_list):
            fails.append(
                f'credits[{i}] and credits[{j}] look like duplicate line items ({reason}) -- '
                f'this double-counts the credit\'s value toward the card\'s computed worth'
            )

        metadata = card_data.get('metadata')
        if not isinstance(metadata, dict):
            metadata = {}
        points_program = metadata.get('points_program')
        if points_program and points_program not in self.points_program_slugs:
            warns.append(f'metadata.points_program "{points_program}" does not match any PointsProgram.slug')

        if not card_data.get('url'):
            warns.append('Missing "url"')
        if not card_data.get('image_url'):
            warns.append('Missing "image_url"')

        slug = card_data.get('slug')
        if slug and slug_counts.get(slug, 0) > 1:
            warns.append(f'slug "{slug}" is used by {slug_counts[slug]} cards in this file')

        if annual_fee is not None and annual_fee > 0:
            total_value = self._credit_value_sum(credits_list)
            if total_value > 3 * float(annual_fee):
                warns.append(
                    f'Sum of credit value*times_per_year*weight (${total_value:,.2f}) is more than 3x the '
                    f'annual fee (${float(annual_fee):,.2f}) -- possible double-count or bad data entry'
                )

        if fails:
            status = 'FAIL'
        elif warns:
            status = 'WARN'
        else:
            status = 'PASS'
        return status, fails, warns, name, (float(annual_fee) if annual_fee is not None else None)

    def _validate_credit(self, index: int, credit: Dict[str, Any]) -> List[str]:
        """WARN-level checks for a single credits[] entry. Returns warning strings."""
        warns: List[str] = []
        desc = credit.get('description') or f'credit #{index}'

        if 'category' in credit and credit['category'] not in self.category_slugs:
            warns.append(
                f'credits[{index}] ("{desc}") category "{credit["category"]}" does not match any '
                f'SpendingCategory.slug -- import_cards.py will WARN and silently drop this credit'
            )

        if 'credit_type' in credit and credit['credit_type'] not in self.spending_credit_names:
            warns.append(
                f'credits[{index}] ("{desc}") credit_type "{credit["credit_type"]}" does not match any '
                f'SpendingCredit.name -- import_cards.py will WARN and silently drop this credit'
            )

        currency = credit.get('currency', '')
        if currency and currency.upper() != 'USD' and currency.upper() not in self.currency_codes:
            warns.append(
                f'credits[{index}] ("{desc}") currency "{currency}" has no seeded '
                f'PointsProgram.currency_code -- will silently degrade to ${UNMAPPED_CURRENCY_RATE}/unit '
                f'at runtime (see cards/valuations.py)'
            )

        if 'weight' in credit:
            weight = credit['weight']
            if not self._is_number(weight) or not (0 <= weight <= 1):
                warns.append(f'credits[{index}] ("{desc}") weight {weight!r} is outside the 0-1 range')

        if 'times_per_year' in credit:
            times_per_year = credit['times_per_year']
            is_positive_int = (
                isinstance(times_per_year, int)
                and not isinstance(times_per_year, bool)
                and times_per_year > 0
            )
            if not is_positive_int:
                warns.append(
                    f'credits[{index}] ("{desc}") times_per_year {times_per_year!r} is not a positive integer'
                )

        if 'value' in credit and not self._is_number(credit['value']):
            warns.append(f'credits[{index}] ("{desc}") value {credit["value"]!r} is not numeric')

        return warns

    def _find_duplicate_credits(self, credits_list: List[Dict[str, Any]]) -> List[Tuple[int, int, str]]:
        """Pairwise duplicate detection within one card's credits array.

        Two entries count as duplicates when they carry the same value AND
        share an identity signal: the same credit_type (if both have one),
        the same category (if both have one), or the same non-empty
        description. This is exactly the shape of the a00e4c2 bug: the same
        "Global Entry, TSA PreCheck, NEXUS Credit" $100 line listed twice.
        """
        dups: List[Tuple[int, int, str]] = []
        for i in range(len(credits_list)):
            a = credits_list[i]
            if not isinstance(a, dict):
                continue
            for j in range(i + 1, len(credits_list)):
                b = credits_list[j]
                if not isinstance(b, dict):
                    continue
                if not self._values_match(a.get('value', 0), b.get('value', 0)):
                    continue

                reasons = []
                if 'credit_type' in a and 'credit_type' in b and a['credit_type'] == b['credit_type']:
                    reasons.append(f'same credit_type "{a["credit_type"]}"')
                if 'category' in a and 'category' in b and a['category'] == b['category']:
                    reasons.append(f'same category "{a["category"]}"')
                desc_a, desc_b = a.get('description'), b.get('description')
                if desc_a and desc_a == desc_b:
                    reasons.append(f'same description "{desc_a}"')

                if reasons:
                    dups.append((i, j, ', '.join(reasons)))
        return dups

    @staticmethod
    def _credit_value_sum(credits_list: List[Dict[str, Any]]) -> float:
        total = 0.0
        for credit in credits_list:
            if not isinstance(credit, dict):
                continue
            value = credit.get('value', 0)
            times_per_year = credit.get('times_per_year', 1)
            weight = credit.get('weight', 1.0)
            if Command._is_number(value) and Command._is_number(times_per_year) and Command._is_number(weight):
                total += float(value) * float(times_per_year) * float(weight)
        return total

    @staticmethod
    def _values_match(a: Any, b: Any) -> bool:
        try:
            return float(a) == float(b)
        except (TypeError, ValueError):
            return a == b

    @staticmethod
    def _is_number(value: Any) -> bool:
        return isinstance(value, (int, float)) and not isinstance(value, bool)
