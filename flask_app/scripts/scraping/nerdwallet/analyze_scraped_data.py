#!/usr/bin/env python3
"""
Script to analyze the scraped NerdWallet credit card data.
Provides insights and statistics about the extracted cards.
"""

import os
import json
from collections import Counter, defaultdict
import statistics

def analyze_scraped_data():
    """Analyze the cleaned NerdWallet card data."""
    
    # Load cleaned data
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    cleaned_file = os.path.join(base_dir, 'data', 'scraped', 'cleaned_nerdwallet_cards.json')
    
    if not os.path.exists(cleaned_file):
        print("❌ Cleaned data file not found. Run the import script first.")
        return
    
    with open(cleaned_file, 'r', encoding='utf-8') as f:
        cards = json.load(f)
    
    print("🎯 NERDWALLET CREDIT CARD SCRAPING ANALYSIS")
    print("=" * 60)
    print(f"📊 Total cards extracted: {len(cards)}")
    
    # Issuer analysis
    issuers = Counter(card['issuer_name'] for card in cards)
    print(f"\n🏦 Cards by Issuer:")
    for issuer, count in issuers.most_common():
        print(f"   {issuer}: {count} cards")
    
    # Reward type analysis
    reward_types = Counter(card['reward_type'] for card in cards)
    print(f"\n💳 Cards by Reward Type:")
    for reward_type, count in reward_types.most_common():
        print(f"   {reward_type.replace('_', ' ').title()}: {count} cards")
    
    # Annual fee analysis
    annual_fees = [card['annual_fee'] for card in cards]
    no_fee_cards = len([fee for fee in annual_fees if fee == 0])
    fee_cards = len([fee for fee in annual_fees if fee > 0])
    
    print(f"\n💰 Annual Fee Analysis:")
    print(f"   No annual fee: {no_fee_cards} cards")
    print(f"   With annual fee: {fee_cards} cards")
    if fee_cards > 0:
        fee_amounts = [fee for fee in annual_fees if fee > 0]
        print(f"   Average fee (for fee cards): ${statistics.mean(fee_amounts):.0f}")
        print(f"   Fee range: ${min(fee_amounts):.0f} - ${max(fee_amounts):.0f}")
    
    # Signup bonus analysis
    cards_with_bonus = [card for card in cards if card['signup_bonus_value'] > 0]
    print(f"\n🎁 Signup Bonus Analysis:")
    print(f"   Cards with signup bonus: {len(cards_with_bonus)}")
    print(f"   Cards without signup bonus: {len(cards) - len(cards_with_bonus)}")
    
    if cards_with_bonus:
        bonus_values = [card['signup_bonus_value'] for card in cards_with_bonus]
        print(f"   Average bonus value: ${statistics.mean(bonus_values):.0f}")
        print(f"   Bonus value range: ${min(bonus_values):.0f} - ${max(bonus_values):.0f}")
        
        # Spending requirements
        spending_reqs = [card['signup_bonus_min_spend'] for card in cards_with_bonus if card['signup_bonus_min_spend'] > 0]
        if spending_reqs:
            print(f"   Average spending requirement: ${statistics.mean(spending_reqs):.0f}")
            print(f"   Spending requirement range: ${min(spending_reqs):.0f} - ${max(spending_reqs):.0f}")
    
    # Top cards by bonus value
    print(f"\n🏆 Top 10 Cards by Signup Bonus Value:")
    top_bonus_cards = sorted(cards, key=lambda x: x['signup_bonus_value'], reverse=True)[:10]
    for i, card in enumerate(top_bonus_cards, 1):
        bonus_text = f"${card['signup_bonus_value']:.0f}"
        if card['signup_bonus_points'] > 0:
            bonus_text += f" ({card['signup_bonus_points']:,} {card['reward_type']})"
        print(f"   {i:2d}. {card['name']} ({card['issuer_name']}) - {bonus_text}")
    
    # Cards by annual fee tiers
    print(f"\n📈 Cards by Annual Fee Tiers:")
    fee_tiers = defaultdict(list)
    for card in cards:
        fee = card['annual_fee']
        if fee == 0:
            tier = "No Fee ($0)"
        elif fee <= 100:
            tier = "Low Fee ($1-$100)"
        elif fee <= 300:
            tier = "Mid Fee ($101-$300)"
        else:
            tier = "High Fee ($300+)"
        fee_tiers[tier].append(card)
    
    for tier in ["No Fee ($0)", "Low Fee ($1-$100)", "Mid Fee ($101-$300)", "High Fee ($300+)"]:
        if tier in fee_tiers:
            print(f"   {tier}: {len(fee_tiers[tier])} cards")
    
    # Sample cards for each reward type
    print(f"\n🎯 Sample Cards by Reward Type:")
    for reward_type in ['cash_back', 'points', 'miles', 'hotel']:
        type_cards = [card for card in cards if card['reward_type'] == reward_type]
        if type_cards:
            sample_card = type_cards[0]
            print(f"   {reward_type.replace('_', ' ').title()}: {sample_card['name']} ({sample_card['issuer_name']})")
    
    print(f"\n✅ Analysis complete! The scraping successfully extracted detailed information")
    print(f"   about {len(cards)} credit cards from NerdWallet's bonus offers page.")
    print(f"   Data includes card names, issuers, fees, bonuses, and reward types.")


if __name__ == '__main__':
    analyze_scraped_data() 