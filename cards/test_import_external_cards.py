"""Tests for the provenance-aware andenacitelli sync
(cards/management/commands/import_external_cards.py):

- get_source / set_source / map_external_credits / compute_proposal: the
  pure per-section helpers.
- Command.apply_updates: mutates andenacitelli-owned sections in a catalog
  card dict, leaves manual-owned sections untouched and reports them as
  conflicts instead.
- Command.sync_pending_updates: creates/refreshes/suppresses
  PendingCardUpdate rows per the dedupe rules.
- The Django admin approve/reject actions: write JSON + re-import on
  approve, mark-only on reject.
"""

import json
import os
import tempfile
from io import StringIO

from django.contrib.messages.storage.fallback import FallbackStorage
from django.core.management.base import OutputWrapper
from django.test import RequestFactory, TestCase, override_settings

from cards.admin import _approve_pending_updates, _reject_pending_updates
from cards.management.commands.import_external_cards import (
    Command, compute_proposal, get_source, map_external_credits, set_source,
)
from cards.models import (
    CreditCard, Issuer, PendingCardUpdate, RewardType, SpendingCategory,
)


def make_command():
    """A Command instance with stdout/stderr captured to StringIO buffers
    (accessible as cmd.stdout_buf / cmd.stderr_buf) instead of the console."""
    cmd = Command()
    stdout_buf, stderr_buf = StringIO(), StringIO()
    cmd.stdout = OutputWrapper(stdout_buf)
    cmd.stderr = OutputWrapper(stderr_buf)
    cmd.stdout_buf = stdout_buf
    cmd.stderr_buf = stderr_buf
    return cmd


class SourceTaggingTests(TestCase):
    """get_source / set_source default and override behavior."""

    def test_untagged_scalar_section_defaults_to_andenacitelli(self):
        card = {}
        self.assertEqual(get_source(card, 'annual_fee'), 'andenacitelli')

    def test_untagged_empty_credits_defaults_to_andenacitelli(self):
        card = {'credits': []}
        self.assertEqual(get_source(card, 'credits'), 'andenacitelli')

    def test_untagged_nonempty_credits_defaults_to_manual(self):
        card = {'credits': [{'description': 'Lounge access', 'value': 100}]}
        self.assertEqual(get_source(card, 'credits'), 'manual')

    def test_explicit_tag_wins_over_heuristic(self):
        card = {'credits': [], '_sources': {'credits': 'manual'}}
        self.assertEqual(get_source(card, 'credits'), 'manual')

    def test_set_source_persists_tag(self):
        card = {}
        set_source(card, 'annual_fee')
        self.assertEqual(card['_sources']['annual_fee'], 'andenacitelli')

    def test_set_source_prevents_future_flip_to_manual(self):
        # A previously-empty, andenacitelli-owned credits list gets filled;
        # without persisting the tag, the next run's heuristic would flip
        # it to 'manual' just because it's no longer empty.
        card = {'credits': []}
        set_source(card, 'credits')
        card['credits'] = [{'description': 'Uber Cash', 'value': 120}]
        self.assertEqual(get_source(card, 'credits'), 'andenacitelli')


class MapExternalCreditsTests(TestCase):
    def test_maps_fields_and_forces_times_per_year_one(self):
        ext_credits = [{'description': '$15/mo Uber Cash', 'value': 200, 'weight': 0.5}]
        mapped = map_external_credits(ext_credits)
        self.assertEqual(mapped, [{
            'description': '$15/mo Uber Cash', 'value': 200,
            'times_per_year': 1, 'weight': 0.5,
        }])

    def test_non_usd_currency_is_kept(self):
        ext_credits = [{'description': 'Hilton credit', 'value': 240, 'weight': 0.5, 'currency': 'HILTON'}]
        mapped = map_external_credits(ext_credits)
        self.assertEqual(mapped[0]['currency'], 'HILTON')

    def test_usd_currency_is_omitted(self):
        ext_credits = [{'description': 'Bag credit', 'value': 50, 'weight': 0.5, 'currency': 'USD'}]
        mapped = map_external_credits(ext_credits)
        self.assertNotIn('currency', mapped[0])

    def test_missing_weight_defaults_to_one(self):
        mapped = map_external_credits([{'description': 'x', 'value': 10}])
        self.assertEqual(mapped[0]['weight'], 1.0)

    def test_none_input_returns_empty_list(self):
        self.assertEqual(map_external_credits(None), [])

    def test_override_normalizes_into_credit_type_and_derives_per_period_value(self):
        """The Disney case: andenacitelli reports the $7/mo Disney Bundle
        Credit as an $84 annual total with no cadence or credit_type. A
        credit_map override supplies both, and the per-period value is
        derived by dividing the annual total back out (84 / 12 = 7)."""
        ext_credits = [{'description': '$7/mo Disney Bundle Credit', 'value': 84, 'weight': 0.25}]
        credit_map = {'credits': {
            '$7/mo Disney Bundle Credit': {'credit_type': 'disney_plus', 'times_per_year': 12},
        }}
        mapped = map_external_credits(ext_credits, credit_map)
        self.assertEqual(mapped, [{
            'description': '$7/mo Disney Bundle Credit',
            'credit_type': 'disney_plus', 'value': 7,
            'times_per_year': 12, 'weight': 0.25,
        }])

    def test_override_rounds_non_whole_per_period_value(self):
        ext_credits = [{'description': 'x', 'value': 100, 'weight': 1.0}]
        credit_map = {'credits': {'x': {'credit_type': 'y', 'times_per_year': 3}}}
        mapped = map_external_credits(ext_credits, credit_map)
        self.assertEqual(mapped[0]['value'], round(100 / 3, 2))

    def test_no_matching_override_falls_back_to_flat_shape(self):
        ext_credits = [{'description': 'Unmapped credit', 'value': 50, 'weight': 0.5}]
        credit_map = {'credits': {'$7/mo Disney Bundle Credit': {'credit_type': 'disney_plus', 'times_per_year': 12}}}
        mapped = map_external_credits(ext_credits, credit_map)
        self.assertEqual(mapped, [{
            'description': 'Unmapped credit', 'value': 50,
            'times_per_year': 1, 'weight': 0.5,
        }])

    def test_override_can_set_category_instead_of_credit_type(self):
        ext_credits = [{'description': 'x', 'value': 60, 'weight': 1.0}]
        credit_map = {'credits': {'x': {'category': 'dining', 'times_per_year': 12}}}
        mapped = map_external_credits(ext_credits, credit_map)
        self.assertEqual(mapped[0]['category'], 'dining')
        self.assertNotIn('credit_type', mapped[0])


class ComputeProposalTests(TestCase):
    def test_annual_fee_no_change_returns_none(self):
        card = {'annual_fee': 95}
        ext = {'annualFee': 95}
        self.assertIsNone(compute_proposal(card, ext, 'annual_fee'))

    def test_annual_fee_change_detected(self):
        card = {'annual_fee': 95}
        ext = {'annualFee': 150}
        current, proposed, label = compute_proposal(card, ext, 'annual_fee')
        self.assertEqual((current, proposed), (95, 150))
        self.assertIn('95 -> 150', label)

    def test_signup_bonus_with_no_offer_returns_none(self):
        card = {'signup_bonus': {'bonus_amount': 60000}}
        ext = {'offers': []}
        self.assertIsNone(compute_proposal(card, ext, 'signup_bonus'))

    def test_signup_bonus_change_detected(self):
        card = {'signup_bonus': {'bonus_amount': 60000, 'spending_requirement': 4000, 'time_limit_months': 3}}
        ext = {'offers': [{'amount': [{'amount': 75000}], 'spend': 5000, 'days': 90}]}
        current, proposed, _ = compute_proposal(card, ext, 'signup_bonus')
        self.assertEqual(proposed, {
            'bonus_amount': 75000, 'spending_requirement': 5000, 'time_limit_months': 3,
        })
        self.assertEqual(current, {
            'bonus_amount': 60000, 'spending_requirement': 4000, 'time_limit_months': 3,
        })

    def test_discontinued_change_detected(self):
        card = {'discontinued': False}
        ext = {'discontinued': True}
        current, proposed, _ = compute_proposal(card, ext, 'discontinued')
        self.assertEqual((current, proposed), (False, True))

    def test_annual_fee_waived_only_flips_on(self):
        card = {'metadata': {'annual_fee_waived_first_year': True}}
        ext = {'isAnnualFeeWaived': False}
        # Already-true stays true regardless of API; never flips off.
        self.assertIsNone(compute_proposal(card, ext, 'annual_fee_waived'))

    def test_annual_fee_waived_flips_on_from_false(self):
        card = {'metadata': {}}
        ext = {'isAnnualFeeWaived': True}
        current, proposed, _ = compute_proposal(card, ext, 'annual_fee_waived')
        self.assertEqual((current, proposed), (False, True))

    def test_credits_change_detected(self):
        card = {'credits': []}
        ext = {'credits': [{'description': 'Lounge', 'value': 100, 'weight': 0.5}]}
        current, proposed, _ = compute_proposal(card, ext, 'credits')
        self.assertEqual(current, [])
        self.assertEqual(proposed, [{
            'description': 'Lounge', 'value': 100, 'times_per_year': 1, 'weight': 0.5,
        }])

    def test_credits_no_api_data_returns_none(self):
        card = {'credits': [{'description': 'Existing', 'value': 50}]}
        ext = {'credits': []}
        self.assertIsNone(compute_proposal(card, ext, 'credits'))

    def test_credits_same_total_different_shape_is_not_a_conflict(self):
        """Curated credits (credit_type/times_per_year) never equal
        andenacitelli's flattened shape (description/times_per_year=1) —
        comparing totals instead of raw lists avoids flagging every curated
        card every sync just because the shape differs."""
        card = {'credits': [{'category': 'resy', 'value': 50, 'times_per_year': 2}]}
        ext = {'credits': [{'description': 'Semi-annual $50 Resy credit', 'value': 100, 'weight': 0.5}]}
        self.assertIsNone(compute_proposal(card, ext, 'credits'))

    def test_credits_real_value_increase_is_detected(self):
        """A curated $100-twice-a-year credit that becomes $200 twice a
        year shows up as andenacitelli's annualized 400 vs our 200 —
        the total actually changed, so this should still be flagged."""
        card = {'credits': [{'category': 'resy', 'value': 100, 'times_per_year': 2}]}
        ext = {'credits': [{'description': 'Semi-annual $200 Resy credit', 'value': 400, 'weight': 0.5}]}
        current, proposed, label = compute_proposal(card, ext, 'credits')
        self.assertEqual(current, card['credits'])
        self.assertIn('$200/yr -> $400/yr', label)

    def test_andenacitelli_owned_credits_rewritten_when_override_normalizes_shape(self):
        """The Disney bug: a prior sync already wrote the flat shape for a
        credit that had no curated entries (so it's andenacitelli-owned).
        Once a credit_map override exists for it, the total-only compare
        used for manual cards would wrongly call this 'no change' — but
        since we own this section, an exact-shape rewrite should still be
        proposed so it converges to the credit_type-linked shape."""
        flat = {'description': '$7/mo Disney Bundle Credit', 'value': 84, 'times_per_year': 1, 'weight': 0.25}
        card = {
            'credits': [flat],
            # set_source tags a section explicitly once filled, so the
            # 'nonempty credits defaults to manual' heuristic never applies
            # to andenacitelli's own auto-fills.
            '_sources': {'credits': 'andenacitelli'},
        }
        ext = {'credits': [{'description': '$7/mo Disney Bundle Credit', 'value': 84, 'weight': 0.25}]}
        credit_map = {'credits': {
            '$7/mo Disney Bundle Credit': {'credit_type': 'disney_plus', 'times_per_year': 12},
        }}
        current, proposed, label = compute_proposal(card, ext, 'credits', credit_map)
        self.assertEqual(current, [flat])
        self.assertEqual(proposed, [{
            'description': '$7/mo Disney Bundle Credit',
            'credit_type': 'disney_plus', 'value': 7,
            'times_per_year': 12, 'weight': 0.25,
        }])
        self.assertIn('$84/yr -> $84/yr', label)

    def test_andenacitelli_owned_credits_identical_shape_returns_none(self):
        card = {'credits': [], '_sources': {'credits': 'andenacitelli'}}
        ext = {'credits': [{'description': 'Lounge', 'value': 100, 'weight': 0.5}]}
        # First sync fills it in...
        _, proposed, _ = compute_proposal(card, ext, 'credits')
        card['credits'] = proposed
        # ...a re-run against the same API data proposes nothing further.
        self.assertIsNone(compute_proposal(card, ext, 'credits'))


class ApplyUpdatesTests(TestCase):
    """Command.apply_updates mutates andenacitelli-owned sections, leaves
    manual-owned sections untouched, and reports the latter as conflicts."""

    def setUp(self):
        self.cmd = make_command()

    def test_untagged_fee_and_bonus_auto_apply(self):
        card = {
            'issuer': 'Chase', 'name': 'Sapphire Preferred', 'annual_fee': 95,
            'signup_bonus': {'bonus_amount': 60000, 'spending_requirement': 4000, 'time_limit_months': 3},
        }
        ext = {
            'annualFee': 150,
            'offers': [{'amount': [{'amount': 75000}], 'spend': 5000, 'days': 90}],
        }
        diffs, conflicts = self.cmd.apply_updates(card, ext)
        self.assertEqual(card['annual_fee'], 150)
        self.assertEqual(card['signup_bonus']['bonus_amount'], 75000)
        self.assertEqual(card['_sources']['annual_fee'], 'andenacitelli')
        self.assertEqual(card['_sources']['signup_bonus'], 'andenacitelli')
        self.assertEqual(len(diffs), 2)
        self.assertEqual(conflicts, [])

    def test_manual_credits_produce_conflict_not_overwrite(self):
        card = {
            'issuer': 'Chase', 'name': 'Sapphire Reserve', 'annual_fee': 550,
            'credits': [
                {'category': 'travel', 'value': 150, 'times_per_year': 2},
                {'credit_type': 'airport_lounge', 'value': 469, 'times_per_year': 1},
            ],
        }
        ext = {
            'annualFee': 550,
            'credits': [{'description': '$300 travel credit', 'value': 300, 'weight': 0.9}],
        }
        diffs, conflicts = self.cmd.apply_updates(card, ext)
        self.assertEqual(diffs, [])
        self.assertEqual(len(conflicts), 1)
        self.assertEqual(conflicts[0]['section'], 'credits')
        # Untouched — the curated credits are still exactly what they were.
        self.assertEqual(len(card['credits']), 2)
        self.assertEqual(card['credits'][0]['category'], 'travel')

    def test_explicitly_tagged_manual_fee_produces_conflict(self):
        card = {
            'issuer': 'Amex', 'name': 'Gold', 'annual_fee': 250,
            '_sources': {'annual_fee': 'manual'},
        }
        ext = {'annualFee': 325}
        diffs, conflicts = self.cmd.apply_updates(card, ext)
        self.assertEqual(diffs, [])
        self.assertEqual(card['annual_fee'], 250)  # untouched
        self.assertEqual(len(conflicts), 1)
        self.assertEqual(conflicts[0], {'section': 'annual_fee', 'current': 250, 'proposed': 325})

    def test_verified_card_dropped_offer_warns_without_clobbering(self):
        card = {
            'issuer': 'Chase', 'name': 'Ink Business Preferred', 'annual_fee': 95,
            'signup_bonus': {'bonus_amount': 100000, 'spending_requirement': 8000, 'time_limit_months': 3},
            'verified': True,
        }
        ext = {'annualFee': 95, 'offers': []}
        diffs, conflicts = self.cmd.apply_updates(card, ext)
        self.assertEqual(card['signup_bonus']['bonus_amount'], 100000)  # untouched
        self.assertEqual(conflicts, [])
        self.assertIn('verify manually', self.cmd.stderr_buf.getvalue())

    def test_empty_untagged_credits_get_filled_and_tagged(self):
        card = {'issuer': 'Chase', 'name': 'Freedom', 'annual_fee': 0, 'credits': []}
        ext = {'annualFee': 0, 'credits': [{'description': 'Cell phone protection', 'value': 60, 'weight': 0.5}]}
        diffs, conflicts = self.cmd.apply_updates(card, ext)
        self.assertEqual(conflicts, [])
        self.assertEqual(card['credits'], [{
            'description': 'Cell phone protection', 'value': 60,
            'times_per_year': 1, 'weight': 0.5,
        }])
        self.assertEqual(card['_sources']['credits'], 'andenacitelli')


class SyncPendingUpdatesTests(TestCase):
    """Command.sync_pending_updates dedupe rules."""

    def setUp(self):
        self.cmd = make_command()

    def make_spec(self, section='credits', proposed=None, current=None):
        return {
            'file': 'chase.json',
            'card': {'issuer': 'Chase', 'name': 'Sapphire Reserve'},
            'ext_id': 'chase-csr',
            'conflict': {
                'section': section,
                'current': current if current is not None else [],
                'proposed': proposed if proposed is not None else [{'description': 'New', 'value': 1}],
            },
        }

    def test_creates_pending_row(self):
        rows = self.cmd.sync_pending_updates([self.make_spec()], dry_run=False)
        self.assertEqual(len(rows), 1)
        self.assertEqual(PendingCardUpdate.objects.filter(status='pending').count(), 1)

    def test_dry_run_creates_no_db_rows(self):
        self.cmd.sync_pending_updates([self.make_spec()], dry_run=True)
        self.assertEqual(PendingCardUpdate.objects.count(), 0)

    def test_rerun_refreshes_existing_pending_row_in_place(self):
        spec1 = self.make_spec(proposed=[{'description': 'A', 'value': 1}])
        self.cmd.sync_pending_updates([spec1], dry_run=False)
        self.assertEqual(PendingCardUpdate.objects.count(), 1)

        spec2 = self.make_spec(proposed=[{'description': 'B', 'value': 2}])
        self.cmd.sync_pending_updates([spec2], dry_run=False)
        self.assertEqual(PendingCardUpdate.objects.count(), 1)  # no duplicate
        row = PendingCardUpdate.objects.get()
        self.assertEqual(row.proposed_value, [{'description': 'B', 'value': 2}])

    def test_rejected_row_suppresses_identical_future_proposal(self):
        spec = self.make_spec(proposed=[{'description': 'A', 'value': 1}])
        self.cmd.sync_pending_updates([spec], dry_run=False)
        PendingCardUpdate.objects.update(status='rejected')

        self.cmd.sync_pending_updates([spec], dry_run=False)
        self.assertEqual(PendingCardUpdate.objects.count(), 1)
        self.assertEqual(PendingCardUpdate.objects.get().status, 'rejected')

    def test_rejected_row_reopens_when_proposal_changes(self):
        spec1 = self.make_spec(proposed=[{'description': 'A', 'value': 1}])
        self.cmd.sync_pending_updates([spec1], dry_run=False)
        PendingCardUpdate.objects.update(status='rejected')

        spec2 = self.make_spec(proposed=[{'description': 'C', 'value': 3}])
        self.cmd.sync_pending_updates([spec2], dry_run=False)
        self.assertEqual(PendingCardUpdate.objects.count(), 2)
        self.assertEqual(PendingCardUpdate.objects.filter(status='pending').count(), 1)

    def test_approved_row_suppresses_identical_future_proposal(self):
        """Credits approvals don't write JSON, so 'current' never converges
        to 'proposed' on its own — without this, the same acknowledged
        proposal would re-open every sync."""
        spec = self.make_spec(proposed=[{'description': 'A', 'value': 1}])
        self.cmd.sync_pending_updates([spec], dry_run=False)
        PendingCardUpdate.objects.update(status='approved')

        self.cmd.sync_pending_updates([spec], dry_run=False)
        self.assertEqual(PendingCardUpdate.objects.count(), 1)
        self.assertEqual(PendingCardUpdate.objects.get().status, 'approved')

    def test_approved_row_reopens_when_proposal_changes(self):
        spec1 = self.make_spec(proposed=[{'description': 'A', 'value': 1}])
        self.cmd.sync_pending_updates([spec1], dry_run=False)
        PendingCardUpdate.objects.update(status='approved')

        spec2 = self.make_spec(proposed=[{'description': 'C', 'value': 3}])
        self.cmd.sync_pending_updates([spec2], dry_run=False)
        self.assertEqual(PendingCardUpdate.objects.count(), 2)
        self.assertEqual(PendingCardUpdate.objects.filter(status='pending').count(), 1)


class ApproveRejectAdminActionTests(TestCase):
    """The Django admin approve/reject actions on PendingCardUpdate."""

    def setUp(self):
        self.issuer = Issuer.objects.create(name='Chase', slug='chase')
        self.reward_type = RewardType.objects.create(name='Points', slug='points')
        SpendingCategory.objects.create(name='travel', slug='travel', display_name='Travel')

        self.tmpdir = tempfile.mkdtemp()
        self.cards_dir = os.path.join(self.tmpdir, 'data', 'input', 'cards')
        os.makedirs(self.cards_dir)
        self.card_json = [{
            'name': 'Sapphire Reserve', 'issuer': 'Chase', 'verified': True,
            'annual_fee': 550, 'primary_reward_type': 'Points',
            'signup_bonus': {'bonus_amount': 60000, 'spending_requirement': 4000, 'time_limit_months': 3},
            'credits': [{'description': 'Old travel credit', 'value': 150}],
            '_sources': {'annual_fee': 'manual', 'credits': 'manual'},
        }]
        self.path = os.path.join(self.cards_dir, 'chase.json')
        with open(self.path, 'w') as f:
            json.dump(self.card_json, f)

        self.fee_update = PendingCardUpdate.objects.create(
            source_file='chase.json', external_card_id='chase-csr',
            card_label='Chase Sapphire Reserve', section='annual_fee',
            current_value=550, proposed_value=595,
        )
        self.credit_update = PendingCardUpdate.objects.create(
            source_file='chase.json', external_card_id='chase-csr',
            card_label='Chase Sapphire Reserve', section='credits',
            current_value=[{'description': 'Old travel credit', 'value': 150}],
            proposed_value=[{'description': 'New travel credit', 'value': 300, 'times_per_year': 1, 'weight': 0.9}],
        )

        self.factory = RequestFactory()

    def _request(self):
        request = self.factory.post('/admin/')
        request.session = {}
        request._messages = FallbackStorage(request)
        return request

    def test_approve_writes_json_tags_manual_and_reimports(self):
        with override_settings(BASE_DIR=self.tmpdir):
            _approve_pending_updates(make_stub_modeladmin(), self._request(),
                                      PendingCardUpdate.objects.filter(pk=self.fee_update.pk))

        self.fee_update.refresh_from_db()
        self.assertEqual(self.fee_update.status, 'approved')
        self.assertIsNotNone(self.fee_update.resolved_at)

        with open(self.path) as f:
            written = json.load(f)
        self.assertEqual(written[0]['annual_fee'], 595)
        self.assertEqual(written[0]['_sources']['annual_fee'], 'manual')

        card = CreditCard.objects.get(name='Sapphire Reserve', issuer=self.issuer)
        self.assertEqual(card.annual_fee, 595)

    def test_approve_credits_acknowledges_without_writing(self):
        """Credits can't be reconciled 1:1 against andenacitelli's flattened
        shape, so approving one only marks it resolved — it never touches
        the JSON file."""
        with override_settings(BASE_DIR=self.tmpdir):
            _approve_pending_updates(make_stub_modeladmin(), self._request(),
                                      PendingCardUpdate.objects.filter(pk=self.credit_update.pk))

        self.credit_update.refresh_from_db()
        self.assertEqual(self.credit_update.status, 'approved')
        self.assertIsNotNone(self.credit_update.resolved_at)

        with open(self.path) as f:
            unchanged = json.load(f)
        self.assertEqual(unchanged[0]['credits'], [{'description': 'Old travel credit', 'value': 150}])

    def test_reject_marks_resolved_without_touching_json(self):
        _reject_pending_updates(make_stub_modeladmin(), self._request(),
                                 PendingCardUpdate.objects.filter(pk=self.credit_update.pk))

        self.credit_update.refresh_from_db()
        self.assertEqual(self.credit_update.status, 'rejected')
        self.assertIsNotNone(self.credit_update.resolved_at)

        with open(self.path) as f:
            unchanged = json.load(f)
        self.assertEqual(unchanged[0]['credits'], [{'description': 'Old travel credit', 'value': 150}])


class _StubModelAdmin:
    def message_user(self, request, message, level='info'):
        pass


def make_stub_modeladmin():
    """A minimal stand-in for admin.ModelAdmin — the action functions only
    call .message_user() on it."""
    return _StubModelAdmin()
