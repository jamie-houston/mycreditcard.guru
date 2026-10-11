import logging
from cards.models import CreditCard
from ..eligibility import application_block, bonus_ineligibility

logger = logging.getLogger(__name__)

class EligibilityManager:
    """
    Manages issuer rules eligibility checks, caching, and entity lookup
    for multi-player households or session-based users.

    Eligibility is a function of `(card, the plan so far)`, not of `card`
    alone: a roadmap that applies for several cards must be legal against
    its own earlier applications, not just against the portfolio the user
    walked in with. Callers building a multi-card plan pass the applies
    already committed to as `planned_cards`; single-card paths (the expense
    recommender's alternatives, the high-spender fallback) can't conflict
    with themselves and pass nothing.
    """

    def __init__(self, engine):
        self.engine = engine
        self.entity_eligibility_cache = {}
        self.bonus_notes = {}

    def _provisional_user_card(self, card: CreditCard):
        """A card the plan commits to applying for, shaped like a UserCard.

        `opened_date = today` is the honest reading: an application made
        inside the 12-month plan horizon is a card opened now as far as the
        window rules are concerned. It is slightly conservative for a
        month-10 apply against a 24-month window, and conservative is the
        established direction here (see eligibility.py on unknown dates).
        """
        return type('ProvisionalUserCard', (), {
            'card': card,
            'opened_date': self.engine.today,
            'closed_date': None,
            'bonus_earned_date': None,
            'bonus_override': None,
            'owner_id': None,
        })()

    def _histories_with(self, planned_cards):
        """Per-entity history extended with the plan's own earlier applies.

        Resolved in order: which entity a provisional would be applied as
        itself depends on the provisionals before it, so this can't be a
        single pass over the list.
        """
        if not planned_cards:
            return self.engine.entity_histories

        histories = {entity_id: list(history)
                     for entity_id, history in self.engine.entity_histories.items()}
        for planned in planned_cards:
            entity = self._entity_for_card(planned, histories)
            if entity is None:
                continue
            histories.setdefault(entity.id, []).append(
                self._provisional_user_card(planned))
        return histories

    def _entity_for_card(self, card: CreditCard, histories):
        """Which entity could apply for `card` given these histories.

        Among the entities that can legally apply, prefer one that can also
        earn the signup bonus — a tiebreak over who applies, never over
        which cards are recommended. With none, the first legal one.
        """
        if card.card_type == 'business':
            candidates = [e for e in self.engine.entities if e.kind == 'business'] \
                or [self.engine._primary_entity]
        else:
            candidates = [e for e in self.engine.entities if e.kind != 'business'] \
                or [self.engine._primary_entity]

        legal = []
        for entity in candidates:
            history = histories.get(entity.id, [])
            already_holds = any(
                uc.card.id == card.id for uc in history if uc.closed_date is None)
            if already_holds:
                continue
            if application_block(card, history, self.engine.today) is not None:
                continue
            legal.append(entity)

        for entity in legal:
            if bonus_ineligibility(
                    card, histories.get(entity.id, []), self.engine.today) is None:
                return entity
        return legal[0] if legal else None

    def eligible_entity_for_card(self, card: CreditCard, planned_cards=()):
        """Which household entity (if any) could apply for `card`, given a
        plan that already commits to applying for `planned_cards`."""
        cache_key = (card.id, tuple(c.id for c in planned_cards))
        if cache_key in self.entity_eligibility_cache:
            return self.entity_eligibility_cache[cache_key]

        result = self._entity_for_card(card, self._histories_with(planned_cards))
        self.entity_eligibility_cache[cache_key] = result
        return result

    def holding_entity_for_card(self, card: CreditCard):
        """Which entity currently holds an OPEN copy of `card`, or None."""
        for entity in self.engine.entities:
            history = self.engine.entity_histories.get(entity.id, [])
            if any(uc.card.id == card.id and uc.closed_date is None
                   for uc in history):
                return entity
        return None

    def is_eligible_for_card(self, card: CreditCard, planned_cards=()) -> bool:
        """Application eligibility: can ANY household entity get approved?"""
        return self.eligible_entity_for_card(card, planned_cards) is not None

    def bonus_ineligibility_note(self, card: CreditCard):
        """User-facing reason this card's signup bonus is valued at $0.

        Answered for the entity the household would apply as, so the note
        and `apply_as` agree. In a multi-member household the note names
        that member — "you've had this card before" is ambiguous there.
        """
        entity = self.eligible_entity_for_card(card) or self.engine._primary_entity
        key = (card.id, entity.id)
        if key not in self.bonus_notes:
            history = self.engine.entity_histories.get(entity.id, self.engine.card_history)
            note = bonus_ineligibility(card, history, self.engine.today)
            if note and len(self.engine.entities) > 1:
                note = f"{entity.name}: {note}"
            self.bonus_notes[key] = note
        return self.bonus_notes[key]
