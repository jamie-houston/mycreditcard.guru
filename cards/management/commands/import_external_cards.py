"""Refresh signup bonuses and annual fees from the andenacitelli community API.

The per-issuer JSON files in data/input/cards/ stay the source of truth for
card detail (reward categories, credits, point valuations, referral URLs).
This command only refreshes the fields that churn — signup bonus offers,
annual fees, discontinued status — by matching API cards to catalog entries,
editing the JSON in place, and re-importing changed files into the DB.

Run `git diff data/input/cards/` after a run for an audit trail of offer
changes. Designed for a monthly scheduled task; safe to run repeatedly.
"""

import json
import os

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError

API_URL = ('https://raw.githubusercontent.com/andenacitelli/'
           'credit-card-bonuses-api/main/exports/data.json')

DATA_DIR = os.path.join(settings.BASE_DIR, 'data')
CARDS_DIR = os.path.join(DATA_DIR, 'input', 'cards')
CACHE_PATH = os.path.join(DATA_DIR, 'external', 'andenacitelli.json')
MAP_PATH = os.path.join(DATA_DIR, 'input', 'overrides', 'external_card_map.json')

# API issuer enum -> catalog issuer name, where .title() isn't enough
ISSUER_NAMES = {
    'AMERICAN_EXPRESS': 'American Express',
    'BANK_OF_AMERICA': 'Bank of America',
    'US_BANK': 'US Bank',
}


def issuer_name(api_issuer):
    return ISSUER_NAMES.get(api_issuer, api_issuer.replace('_', ' ').title())


def norm_name(name, issuer=''):
    """Normalize a card name for matching across the two datasets.

    'from american express' must be stripped before the issuer name,
    otherwise stripping 'american express' first leaves a dangling 'from'.
    '+' is kept so 'Expedia One Key+' stays distinct from 'Expedia One Key'.
    """
    s = name.lower()
    for junk in ('from american express', issuer.lower(), 'credit card',
                 'card', '®', '℠', '™', 'the ', 'rapid rewards'):
        if junk:
            s = s.replace(junk, '')
    return ''.join(ch for ch in s if ch.isalnum() or ch == '+')


class Command(BaseCommand):
    help = ('Refresh signup bonuses/fees in data/input/cards/*.json from the '
            'andenacitelli community API, then re-import changed files')

    def add_arguments(self, parser):
        parser.add_argument(
            '--file', dest='file',
            help='Read API data from a local JSON file instead of fetching')
        parser.add_argument(
            '--dry-run', action='store_true',
            help='Report what would change without writing anything')
        parser.add_argument(
            '--no-import', action='store_true',
            help='Update the JSON files but skip the DB re-import')

    def handle(self, *args, **options):
        api_cards = self.load_api_data(options.get('file'))
        manual_map = self.load_manual_map()
        catalog = self.load_catalog()

        # Index catalog entries two ways: exact (issuer, name) for the manual
        # map, normalized (issuer, norm_name) for auto-matching. A normalized
        # key shared by two entries is ambiguous and excluded from automatch.
        by_exact = {}
        by_norm = {}
        for entry in catalog:
            card, fname = entry['card'], entry['file']
            by_exact[(card['issuer'], card['name'])] = entry
            nkey = (card['issuer'], norm_name(card['name'], card['issuer']))
            by_norm[nkey] = entry if nkey not in by_norm else None

        changed_files = set()
        changes = []
        new_cards = []
        matched_ids = set()

        for ext in api_cards:
            entry = None
            mapped = manual_map.get(ext['cardId'])
            if mapped:
                entry = by_exact.get((mapped['issuer'], mapped['name']))
                if entry is None:
                    self.stderr.write(self.style.WARNING(
                        f"Map entry for {ext['cardId']} points at "
                        f"{mapped['issuer']} / {mapped['name']}, which isn't "
                        f"in the catalog — fix external_card_map.json"))
            else:
                iss = issuer_name(ext['issuer'])
                entry = by_norm.get((iss, norm_name(ext['name'], iss)))

            if entry is None:
                if not ext.get('discontinued'):
                    new_cards.append(f"{issuer_name(ext['issuer'])} | "
                                     f"{ext['name']} (fee ${ext['annualFee']})")
                continue

            matched_ids.add(ext['cardId'])
            diffs = self.apply_updates(entry['card'], ext)
            if diffs:
                changed_files.add(entry['file'])
                label = f"{entry['card']['issuer']} {entry['card']['name']}"
                changes.append((label, diffs))

        self.report(changes, new_cards, catalog, matched_ids,
                    dry_run=options['dry_run'])

        if options['dry_run'] or not changed_files:
            return

        for fname in sorted(changed_files):
            path = os.path.join(CARDS_DIR, fname)
            cards = [e['card'] for e in catalog if e['file'] == fname]
            with open(path, 'w') as f:
                json.dump(cards, f, indent=2, ensure_ascii=False)
                f.write('\n')
            self.stdout.write(f'Wrote {path}')

        if not options['no_import']:
            for fname in sorted(changed_files):
                self.stdout.write(f'Re-importing {fname} into the DB...')
                call_command('import_cards', os.path.join(CARDS_DIR, fname))

    # ------------------------------------------------------------------
    # Loading

    def load_api_data(self, local_file):
        if local_file:
            with open(local_file) as f:
                return json.load(f)

        import requests
        try:
            resp = requests.get(API_URL, timeout=30)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            if os.path.exists(CACHE_PATH):
                self.stderr.write(self.style.WARNING(
                    f'Fetch failed ({e}); using cached {CACHE_PATH}'))
                with open(CACHE_PATH) as f:
                    return json.load(f)
            raise CommandError(f'Failed to fetch API data and no cache: {e}')

        os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)
        with open(CACHE_PATH, 'w') as f:
            json.dump(data, f, indent=1)
        self.stdout.write(f'Fetched {len(data)} cards; cached to {CACHE_PATH}')
        return data

    def load_manual_map(self):
        if not os.path.exists(MAP_PATH):
            return {}
        with open(MAP_PATH) as f:
            return json.load(f).get('mappings', {})

    def load_catalog(self):
        """All card entries from data/input/cards/*.json, with provenance."""
        catalog = []
        for fname in sorted(os.listdir(CARDS_DIR)):
            if not fname.endswith('.json'):
                continue
            with open(os.path.join(CARDS_DIR, fname)) as f:
                data = json.load(f)
            if not isinstance(data, list):
                continue  # spending_categories.json etc.
            for card in data:
                if isinstance(card, dict) and 'issuer' in card and 'name' in card:
                    catalog.append({'file': fname, 'card': card})
        return catalog

    # ------------------------------------------------------------------
    # Updating

    def apply_updates(self, card, ext):
        """Mutate a catalog entry from its API counterpart; return diff strings."""
        diffs = []

        if card.get('annual_fee') != ext['annualFee']:
            diffs.append(f"annual_fee {card.get('annual_fee')} -> {ext['annualFee']}")
            card['annual_fee'] = ext['annualFee']

        offer = (ext.get('offers') or [None])[0]
        amount = 0
        if offer:
            amounts = offer.get('amount') or []
            amount = int(amounts[0].get('amount', 0)) if amounts else 0
        if offer and amount > 0:
            bonus = card.get('signup_bonus')
            if not isinstance(bonus, dict):
                bonus = {}
                card['signup_bonus'] = bonus
            updates = {
                'bonus_amount': amount,
                'spending_requirement': offer.get('spend') or 0,
                'time_limit_months': max(1, round((offer.get('days') or 90) / 30)),
            }
            for key, new in updates.items():
                old = bonus.get(key)
                if old != new:
                    diffs.append(f'signup_bonus.{key} {old} -> {new}')
                    bonus[key] = new
        elif (card.get('signup_bonus') or {}).get('bonus_amount') and card.get('verified'):
            # Don't clobber a curated bonus just because the API dropped the
            # offer, but do flag it — the offer may genuinely be gone.
            self.stderr.write(self.style.WARNING(
                f"{card['issuer']} {card['name']}: API shows no current "
                f"offer; catalog still has "
                f"{card['signup_bonus']['bonus_amount']} — verify manually"))

        if bool(card.get('discontinued')) != bool(ext.get('discontinued')):
            diffs.append(f"discontinued {card.get('discontinued')} -> "
                         f"{ext.get('discontinued')}")
            card['discontinued'] = bool(ext.get('discontinued'))

        if ext.get('isAnnualFeeWaived'):
            meta = card.setdefault('metadata', {})
            if not meta.get('annual_fee_waived_first_year'):
                diffs.append('annual_fee_waived_first_year -> True')
                meta['annual_fee_waived_first_year'] = True

        return diffs

    # ------------------------------------------------------------------
    # Reporting

    def report(self, changes, new_cards, catalog, matched_ids, dry_run):
        prefix = '[dry-run] ' if dry_run else ''
        if changes:
            self.stdout.write(self.style.MIGRATE_HEADING(
                f'{prefix}{len(changes)} cards changed:'))
            for label, diffs in changes:
                self.stdout.write(f'  {label}')
                for d in diffs:
                    self.stdout.write(f'    {d}')
        else:
            self.stdout.write(f'{prefix}No changes — catalog is current.')

        if new_cards:
            self.stdout.write(self.style.MIGRATE_HEADING(
                f'{len(new_cards)} API cards not in the catalog '
                f'(add to data/input/cards/ or map in external_card_map.json '
                f'if wanted):'))
            for n in sorted(new_cards):
                self.stdout.write(f'  {n}')
