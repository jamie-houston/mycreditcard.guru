import logging
from cards.models import CreditCard
from ..eligibility import application_block, bonus_ineligibility

logger = logging.getLogger(__name__)

class EligibilityManager:
    """
    Manages issuer rules eligibility checks, caching, and entity lookup
    for multi-player households or session-based users.
    """

    def __init__(self, engine):
        self.engine = engine
        self.entity_eligibility_cache = {}
        self.bonus_notes = {}

    def eligible_entity_for_card(self, card: CreditCard):
        """Which household entity (if any) could apply for `card`."""
        if card.id in self.entity_eligibility_cache:
            return self.entity_eligibility_cache[card.id]

        if card.card_type == 'business':
            candidates = [e for e in self.engine.entities if e.kind == 'business'] \
                or [self.engine._primary_entity]
        else:
            candidates = [e for e in self.engine.entities if e.kind != 'business'] \
                or [self.engine._primary_entity]

        result = None
        for entity in candidates:
            history = self.engine.entity_histories.get(entity.id, [])
            already_holds = any(
                uc.card.id == card.id for uc in history if uc.closed_date is None)
            if already_holds:
                continue
            if application_block(card, history, self.engine.today) is not None:
                continue
            result = entity
            break

        self.entity_eligibility_cache[card.id] = result
        return result

    def holding_entity_for_card(self, card: CreditCard):
        """Which entity currently holds an OPEN copy of `card`, or None."""
        for entity in self.engine.entities:
            history = self.engine.entity_histories.get(entity.id, [])
            if any(uc.card.id == card.id and uc.closed_date is None
                   for uc in history):
                return entity
        return None

    def is_eligible_for_card(self, card: CreditCard) -> bool:
        """Application eligibility: can ANY household entity get approved?"""
        return self.eligible_entity_for_card(card) is not None

    def bonus_ineligibility_note(self, card: CreditCard):
        """User-facing reason this card's signup bonus is valued at $0."""
        if card.id not in self.bonus_notes:
            entity = self.eligible_entity_for_card(card) or self.engine._primary_entity
            history = self.engine.entity_histories.get(entity.id, self.engine.card_history)
            self.bonus_notes[card.id] = bonus_ineligibility(
                card, history, self.engine.today)
        return self.bonus_notes[card.id]
