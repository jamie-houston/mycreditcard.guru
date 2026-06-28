"""
Strategy presets: a strategy is data, not code.

Each preset bundles the three knobs the engine already understands:
  - filters: card-pool filters (same dicts the quick-rec API accepts;
    same-type filters OR together, different types AND)
  - max_recommendations: default cap on NEW card applications (an explicit
    max_recommendations in the request always wins over the preset)
  - weights: selection-time scoring adjustments. These change which cards
    the optimizer picks, never the displayed dollar math — every headline
    value must still reconcile to its line items.

Weights:
  signup_bonus_weight: multiplier on signup-bonus value during portfolio
    selection. <1 = prefer steady ongoing value over bonus chasing;
    >1 = chase bonuses (the displayed bonus value is always the real one).
  per_card_penalty: flat dollars subtracted per held card during portfolio
    selection — models the effort of managing another card. A card must
    add more than this to make the cut.
"""

DEFAULT_WEIGHTS = {
    'signup_bonus_weight': 1.0,
    'per_card_penalty': 0.0,
}

STRATEGIES = {
    'simple_cash_back': {
        'key': 'simple_cash_back',
        'name': 'Simple Cash Back',
        'effort_label': 'As little as possible',
        'description': (
            'A couple of cash-back cards you can use on autopilot. '
            'No points math, no rotating calendars, no fee juggling.'
        ),
        'filters': [
            {'name': 'Strategy: cash back cards', 'filter_type': 'reward_type', 'value': 'Cashback'},
        ],
        'max_recommendations': 2,
        'weights': {
            'signup_bonus_weight': 0.5,
            'per_card_penalty': 100.0,
        },
    },
    'travel_points': {
        'key': 'travel_points',
        'name': 'Travel Points',
        'effort_label': 'Some, if it pays for travel',
        'description': (
            'Build a points/miles portfolio for travel redemptions. '
            'A few more cards and an annual fee where it pays for itself.'
        ),
        'filters': [
            {'name': 'Strategy: points cards', 'filter_type': 'reward_type', 'value': 'Points'},
            {'name': 'Strategy: miles cards', 'filter_type': 'reward_type', 'value': 'Miles'},
            {'name': 'Strategy: hotel cards', 'filter_type': 'reward_type', 'value': 'Hotel'},
        ],
        'max_recommendations': 4,
        'weights': {
            'signup_bonus_weight': 1.0,
            'per_card_penalty': 25.0,
        },
    },
    'maximizer': {
        'key': 'maximizer',
        'name': 'Maximizer',
        'effort_label': 'I have a spreadsheet',
        'description': (
            'Every reward type in play, signup bonuses weighted heavily, '
            'no card-count squeamishness. For people with spreadsheets.'
        ),
        'filters': [],
        'max_recommendations': 6,
        'weights': {
            'signup_bonus_weight': 1.5,
            'per_card_penalty': 0.0,
        },
    },
}


def ui_presets():
    """STRATEGIES as a list for UI rendering, ordered low→high effort.

    `effort_label` is the answer text for the effort-tolerance question
    (which is just a friendly skin over the presets). `pool_label` is a
    human summary of the card-pool filters so the UI never re-derives
    filter semantics.
    """
    presets = []
    for strategy in STRATEGIES.values():
        reward_types = [
            f['value'] for f in strategy['filters']
            if f['filter_type'] == 'reward_type'
        ]
        presets.append({
            'key': strategy['key'],
            'name': strategy['name'],
            'effort_label': strategy['effort_label'],
            'description': strategy['description'],
            'max_recommendations': strategy['max_recommendations'],
            'pool_label': ' / '.join(reward_types) if reward_types else 'All reward types',
        })
    return presets


def get_strategy(key):
    """Return the preset for `key`, or None for falsy/unknown keys."""
    if not key:
        return None
    return STRATEGIES.get(key)


def strategy_weights(strategy):
    """Full weights dict for a preset (or the defaults for None)."""
    weights = dict(DEFAULT_WEIGHTS)
    if strategy:
        weights.update(strategy.get('weights', {}))
    return weights


def resolve_scenario_strategy(scenario_data):
    """Strategy preset for a scenario dict's optional "strategy" key.

    Unknown keys are a loud error — a typo silently running the default
    strategy would make the scenario test the wrong thing.
    """
    key = scenario_data.get('strategy')
    if not key:
        return None
    strategy = get_strategy(key)
    if strategy is None:
        raise ValueError(
            f"Scenario strategy '{key}' unknown (choices: {', '.join(sorted(STRATEGIES))})")
    return strategy


def apply_strategy_to_roadmap(roadmap, strategy):
    """Attach a preset's card-pool filters to a roadmap.

    Filters ADD to whatever is already on the roadmap (a user's explicit
    filters narrow the preset's pool further). max_recommendations is NOT
    set here — callers decide whether the preset's default applies.
    """
    if not strategy:
        return
    from .models import RoadmapFilter
    for filter_data in strategy['filters']:
        filter_obj, _ = RoadmapFilter.objects.get_or_create(
            name=filter_data['name'],
            filter_type=filter_data['filter_type'],
            value=filter_data['value'],
        )
        roadmap.filters.add(filter_obj)
