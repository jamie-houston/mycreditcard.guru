from app import create_app, db
from app.models.credit_card import CreditCard

def check_cards():
    app = create_app()
    with app.app_context():
        cards = CreditCard.query.all()
        print(f"Total cards: {len(cards)}")
        
        if cards:
            # Print the attributes of the first card for debugging
            print("\nAvailable CreditCard attributes:")
            first_card = cards[0]
            for attr in dir(first_card):
                if not attr.startswith('_') and not callable(getattr(first_card, attr)):
                    print(f"  {attr}: {getattr(first_card, attr)}")
        
        for card in cards:
            print(f"\nCard ID: {card.id}")
            print(f"Name: {card.name}")
            print(f"Issuer: {card.issuer}")
            print(f"Annual Fee: ${card.annual_fee}")
            print(f"Base Reward Rate: {card.base_reward_rate}")
            
            # Try to access these attributes safely
            if hasattr(card, 'signup_bonus'):
                print(f"Sign-up Bonus: {card.signup_bonus}")
            if hasattr(card, 'signup_bonus_value'):
                print(f"Sign-up Bonus Value: ${card.signup_bonus_value}")
            if hasattr(card, 'reward_categories'):
                print(f"Reward Categories: {card.reward_categories}")
            
            # Print special reward rates if available
            if hasattr(card, 'dining_reward_rate') and card.dining_reward_rate:
                print(f"  Dining Reward Rate: {card.dining_reward_rate}")
            if hasattr(card, 'travel_reward_rate') and card.travel_reward_rate:
                print(f"  Travel Reward Rate: {card.travel_reward_rate}")
            if hasattr(card, 'gas_reward_rate') and card.gas_reward_rate:
                print(f"  Gas Reward Rate: {card.gas_reward_rate}")
            if hasattr(card, 'grocery_reward_rate') and card.grocery_reward_rate:
                print(f"  Grocery Reward Rate: {card.grocery_reward_rate}")
            if hasattr(card, 'entertainment_reward_rate') and card.entertainment_reward_rate:
                print(f"  Entertainment Reward Rate: {card.entertainment_reward_rate}")

if __name__ == "__main__":
    check_cards() 