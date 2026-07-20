"""Refresh signup bonuses, fees, and credits from the andenacitelli community API.

The per-issuer JSON files in data/input/cards/ stay the source of truth for
card detail. Each card carries a "_sources" map tagging which side owns each
section ("andenacitelli" or "manual"). Sections tagged (or defaulted to)
andenacitelli are refreshed automatically here; sections tagged "manual" are
never overwritten — if andenacitelli's data disagrees with a manual section,
a PendingCardUpdate row is queued instead, reviewable (approve/reject) in the
Django admin. Reward categories have no andenacitelli source and are never
touched by this command.

Run `git diff data/input/cards/` after a run for an audit trail of offer
changes. Designed for a monthly scheduled task; safe to run repeatedly.
"""

import json
import os

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError

from cards.models import CreditCard, PendingCardUpdate

API_URL = ('https://raw.githubusercontent.com/andenacitelli/'
           'credit-card-bonuses-api/main/exports/data.json')

DATA_DIR = os.path.join(settings.BASE_DIR, 'data')
CARDS_DIR = os.path.join(DATA_DIR, 'input', 'cards')
CACHE_PATH = os.path.join(DATA_DIR, 'external', 'andenacitelli.json')
MAP_PATH = os.path.join(DATA_DIR, 'input', 'overrides', 'external_card_map.json')
CREDIT_MAP_PATH = os.path.join(DATA_DIR, 'input', 'overrides', 'external_credit_map.json')

# Sections this command can propose changes for. Reward categories aren't
# here — andenacitelli has no per-category earn-rate data at all.
SYNCABLE_SECTIONS = ('annual_fee', 'signup_bonus', 'discontinued',
                     'annual_fee_waived', 'credits')

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


def get_source(card, section):
    """Which side owns this section: 'andenacitelli' or 'manual'.

    Untagged cards default to preserving today's behavior: the four churn
    fields auto-update, credits default to 'manual' if the card already has
    curated credits (protect existing curation) or 'andenacitelli' if the
    card has none yet (nothing to protect, so let the API fill it in).
    """
    sources = card.get('_sources') or {}
    if section in sources:
        return sources[section]
    if section == 'credits':
        return 'manual' if card.get('credits') else 'andenacitelli'
    return 'andenacitelli'


def set_source(card, section):
    """Explicitly tag a section as andenacitelli-owned once we've touched it,
    so a later run doesn't misapply the 'credits' emptiness heuristic once
    the section is no longer empty."""
    sources = card.setdefault('_sources', {})
    sources[section] = 'andenacitelli'


def map_external_credits(ext_credits, credit_map=None):
    """andenacitelli credits are {description, value, weight, currency?},
    already annualized, with no cadence and no link into our credit_type
    taxonomy. Our schema splits value from a per-occurrence count
    (times_per_year), so a straight import always sets times_per_year=1 —
    the annualized total is preserved even though the split isn't.

    external_credit_map.json (data/input/overrides/) opts specific
    descriptions into the curated shape instead: it supplies credit_type
    (and/or category) plus times_per_year, and the per-period value is
    derived by dividing andenacitelli's annual value by that count.
    """
    overrides = (credit_map or {}).get('credits', {})
    mapped = []
    for c in ext_credits or []:
        description = c.get('description', '')
        override = overrides.get(description)
        if override:
            times_per_year = override['times_per_year']
            annual = c.get('value', 0)
            per_period = annual / times_per_year
            if per_period == int(per_period):
                per_period = int(per_period)
            else:
                per_period = round(per_period, 2)
            entry = {'description': description}
            if 'credit_type' in override:
                entry['credit_type'] = override['credit_type']
            if 'category' in override:
                entry['category'] = override['category']
            entry['value'] = per_period
            entry['times_per_year'] = times_per_year
            entry['weight'] = override.get('weight', c.get('weight', 1.0))
        else:
            entry = {
                'description': description,
                'value': c.get('value', 0),
                'times_per_year': 1,
                'weight': c.get('weight', 1.0),
            }
        if c.get('currency') and c['currency'] != 'USD':
            entry['currency'] = c['currency']
        mapped.append(entry)
    return mapped


def compute_proposal(card, ext, section, credit_map=None):
    """Return (current_value, proposed_value, diff_label) if andenacitelli's
    data disagrees with the catalog for this section, else None."""
    if section == 'annual_fee':
        current = card.get('annual_fee')
        proposed = ext['annualFee']
        if current == proposed:
            return None
        return current, proposed, f"annual_fee {current} -> {proposed}"

    if section == 'signup_bonus':
        offer = (ext.get('offers') or [None])[0]
        amounts = (offer or {}).get('amount') or []
        amount = int(amounts[0].get('amount', 0)) if amounts else 0
        if not offer or amount <= 0:
            return None  # handled separately as a non-clobbering warning
        current_full = card.get('signup_bonus')
        current_full = current_full if isinstance(current_full, dict) else {}
        proposed = {
            'bonus_amount': amount,
            'spending_requirement': offer.get('spend') or 0,
            'time_limit_months': max(1, round((offer.get('days') or 90) / 30)),
        }
        current = {k: current_full.get(k) for k in proposed}
        if current == proposed:
            return None
        return current, proposed, f"signup_bonus {current} -> {proposed}"

    if section == 'discontinued':
        current = bool(card.get('discontinued'))
        proposed = bool(ext.get('discontinued'))
        if current == proposed:
            return None
        return current, proposed, f"discontinued {current} -> {proposed}"

    if section == 'annual_fee_waived':
        current = bool((card.get('metadata') or {}).get('annual_fee_waived_first_year'))
        proposed = bool(ext.get('isAnnualFeeWaived'))
        if not proposed or current:
            return None  # one-way flip-on only, same as legacy behavior
        return current, True, 'annual_fee_waived_first_year -> True'

    if section == 'credits':
        current = card.get('credits') or []
        proposed = map_external_credits(ext.get('credits'), credit_map)
        if not proposed:
            return None

        owned_by_us = get_source(card, 'credits') == 'andenacitelli'
        if owned_by_us:
            # This section is ours to auto-fill/repair — flag any structural
            # difference, e.g. a credit_map entry now normalizes a flat
            # entry an earlier sync already wrote (same total, new shape).
            if current == proposed:
                return None
        else:
            # Manual/curated: andenacitelli's shape (description/
            # times_per_year=1) never equals our curated shape (credit_type/
            # category, times_per_year=12/4/2), so comparing lists directly
            # would flag every curated card every sync. Compare annualized
            # totals instead — only flag a real dollar change.
            current_total = sum(float(c.get('value', 0)) * c.get('times_per_year', 1) for c in current)
            proposed_total = sum(float(c.get('value', 0)) * c.get('times_per_year', 1) for c in proposed)
            if current_total == proposed_total:
                return None

        current_total = sum(float(c.get('value', 0)) * c.get('times_per_year', 1) for c in current)
        proposed_total = sum(float(c.get('value', 0)) * c.get('times_per_year', 1) for c in proposed)
        return current, proposed, f"credits total ${current_total:.0f}/yr -> ${proposed_total:.0f}/yr"

    raise ValueError(f'Unknown section: {section}')


class Command(BaseCommand):
    help = ('Refresh signup bonuses/fees/credits in data/input/cards/*.json '
            'from the andenacitelli community API, then re-import changed '
            'files. Manually-tagged sections are never overwritten; '
            'conflicts are queued for review in the Django admin.')

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
        credit_map = self.load_credit_map()
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
        pending_specs = []

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

            diffs, conflicts = self.apply_updates(entry['card'], ext, credit_map)
            if diffs:
                changed_files.add(entry['file'])
                label = f"{entry['card']['issuer']} {entry['card']['name']}"
                changes.append((label, diffs))
            for conflict in conflicts:
                pending_specs.append({
                    'file': entry['file'], 'card': entry['card'],
                    'ext_id': ext['cardId'], 'conflict': conflict,
                })

        pending_rows = self.sync_pending_updates(
            pending_specs, dry_run=options['dry_run'])

        self.report(changes, new_cards, pending_rows, dry_run=options['dry_run'])

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

    def load_credit_map(self):
        """Opt-in description -> {credit_type/category, times_per_year}
        overrides for normalizing andenacitelli's flat credits into our
        curated taxonomy shape. See external_credit_map.json's _comment."""
        if not os.path.exists(CREDIT_MAP_PATH):
            return {}
        with open(CREDIT_MAP_PATH) as f:
            return json.load(f)

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

    def apply_updates(self, card, ext, credit_map=None):
        """Mutate a catalog entry's andenacitelli-owned sections in place.

        Returns (diffs, conflicts): diffs are human-readable strings for
        sections that were applied; conflicts are manual-sourced sections
        where andenacitelli disagrees — left untouched here, queued for
        review by the caller.
        """
        diffs = []
        conflicts = []

        for section in SYNCABLE_SECTIONS:
            proposal = compute_proposal(card, ext, section, credit_map)
            if proposal is None:
                continue
            current, proposed, label = proposal

            if get_source(card, section) == 'manual':
                conflicts.append({
                    'section': section, 'current': current, 'proposed': proposed,
                })
                continue

            if section == 'annual_fee':
                card['annual_fee'] = proposed
            elif section == 'signup_bonus':
                bonus = card.get('signup_bonus')
                if not isinstance(bonus, dict):
                    bonus = {}
                    card['signup_bonus'] = bonus
                bonus.update(proposed)
            elif section == 'discontinued':
                card['discontinued'] = proposed
            elif section == 'annual_fee_waived':
                card.setdefault('metadata', {})['annual_fee_waived_first_year'] = True
            elif section == 'credits':
                card['credits'] = proposed

            set_source(card, section)
            diffs.append(label)

        # Don't clobber a curated bonus just because the API dropped the
        # offer, but do flag it — the offer may genuinely be gone. This is
        # independent of _sources: an absent offer isn't a "proposed value"
        # we could apply even if andenacitelli owned the section.
        offer = (ext.get('offers') or [None])[0]
        amounts = (offer or {}).get('amount') or []
        amount = int(amounts[0].get('amount', 0)) if amounts else 0
        if ((not offer or amount <= 0)
                and (card.get('signup_bonus') or {}).get('bonus_amount')
                and card.get('verified')):
            self.stderr.write(self.style.WARNING(
                f"{card['issuer']} {card['name']}: API shows no current "
                f"offer; catalog still has "
                f"{card['signup_bonus']['bonus_amount']} — verify manually"))

        return diffs, conflicts

    def sync_pending_updates(self, specs, dry_run):
        """Create/refresh PendingCardUpdate rows for manual-section conflicts.

        One open ("pending") row per (source_file, card_label, section).
        A pending row's proposal is refreshed in place; a rejected or
        approved row that still matches the same proposal stays suppressed
        (no re-nagging — this matters for 'credits', which approve doesn't
        write to disk, so it would otherwise recur every sync); anything
        else (no prior row, or the proposal changed since it was resolved)
        opens a fresh pending row.
        """
        report_rows = []
        for spec in specs:
            card = spec['card']
            label = f"{card['issuer']} {card['name']}"
            section = spec['conflict']['section']
            current = spec['conflict']['current']
            proposed = spec['conflict']['proposed']
            report_rows.append((label, section, current, proposed))

            if dry_run:
                continue

            existing = (PendingCardUpdate.objects
                        .filter(source_file=spec['file'], card_label=label, section=section)
                        .order_by('-created_at').first())

            if existing and existing.status == 'pending':
                if existing.proposed_value != proposed or existing.current_value != current:
                    existing.proposed_value = proposed
                    existing.current_value = current
                    existing.save(update_fields=['proposed_value', 'current_value'])
                continue

            if (existing and existing.status in ('rejected', 'approved')
                    and existing.proposed_value == proposed
                    and existing.current_value == current):
                continue  # already reviewed; don't re-nag with the same proposal

            db_card = CreditCard.objects.filter(
                issuer__name=card['issuer'], name=card['name']).first()
            PendingCardUpdate.objects.create(
                card=db_card,
                source_file=spec['file'],
                external_card_id=spec['ext_id'],
                card_label=label,
                section=section,
                current_value=current,
                proposed_value=proposed,
            )
        return report_rows

    # ------------------------------------------------------------------
    # Reporting

    def report(self, changes, new_cards, pending_rows, dry_run):
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

        if pending_rows:
            self.stdout.write(self.style.MIGRATE_HEADING(
                f'{len(pending_rows)} conflict(s) need review — Django admin '
                f'→ Pending Card Updates:'))
            for label, section, current, proposed in pending_rows:
                self.stdout.write(f'  {label} [{section}]')
                self.stdout.write(f'    yours:  {current}')
                self.stdout.write(f'    theirs: {proposed}')

        if new_cards:
            self.stdout.write(self.style.MIGRATE_HEADING(
                f'{len(new_cards)} API cards not in the catalog '
                f'(add to data/input/cards/ or map in external_card_map.json '
                f'if wanted):'))
            for n in sorted(new_cards):
                self.stdout.write(f'  {n}')
