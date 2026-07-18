def info_item(name, text):
    """A $0 informational breakdown line — never affects reconciliation."""
    return {
        'category_name': name, 'monthly_spend': 0, 'annual_spend': 0,
        'reward_rate': 0, 'reward_multiplier': 0, 'points_earned': 0,
        'category_rewards': 0, 'calculation': text, 'type': 'info',
    }
