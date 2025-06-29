import json
import os
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from cards.models import (
    Issuer, RewardType, SpendingCategory, CreditCard, 
    RewardCategory, CardOffer
)


class Command(BaseCommand):
    help = 'Import credit cards from JSON files'

    def add_arguments(self, parser):
        parser.add_argument(
            'file_path',
            type=str,
            help='Path to the JSON file containing credit card data'
        )

    def handle(self, *args, **options):
        file_path = options['file_path']
        
        if not os.path.exists(file_path):
            self.stdout.write(
                self.style.ERROR(f'File not found: {file_path}')
            )
            return

        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            self.stdout.write(
                self.style.ERROR(f'Invalid JSON: {e}')
            )
            return

        # Determine file type and import accordingly
        filename = os.path.basename(file_path).lower()
        if filename == 'issuers.json':
            self.import_issuers(data)
        elif filename == 'reward_types.json':
            self.import_reward_types(data)
        elif filename == 'spending_categories.json':
            self.import_spending_categories(data)
        elif filename == 'credit_cards.json':
            self.import_credit_cards(data)
        else:
            # Legacy format - assume it's the old combined format
            self.import_data(data)

    def import_data(self, data):
        """
        Expected JSON format:
        {
            "issuers": [...],
            "reward_types": [...],
            "spending_categories": [...],
            "credit_cards": [...]
        }
        """
        
        # Import issuers
        if 'issuers' in data:
            self.import_issuers(data['issuers'])
        
        # Import reward types
        if 'reward_types' in data:
            self.import_reward_types(data['reward_types'])
        
        # Import spending categories
        if 'spending_categories' in data:
            self.import_spending_categories(data['spending_categories'])
        
        # Import credit cards
        if 'credit_cards' in data:
            self.import_credit_cards(data['credit_cards'])

    def import_issuers(self, issuers):
        for issuer_data in issuers:
            issuer, created = Issuer.objects.get_or_create(
                name=issuer_data['name'],
                defaults={
                    'slug': slugify(issuer_data['name']),
                    'max_cards_per_period': issuer_data.get('max_cards_per_period', 5),
                    'period_months': issuer_data.get('period_months', 24),
                }
            )
            if created:
                self.stdout.write(f'Created issuer: {issuer.name}')

    def import_reward_types(self, reward_types):
        for reward_type_data in reward_types:
            reward_type, created = RewardType.objects.get_or_create(
                name=reward_type_data['name'],
                defaults={
                    'slug': slugify(reward_type_data['name']),
                }
            )
            if created:
                self.stdout.write(f'Created reward type: {reward_type.name}')

    def import_spending_categories(self, categories):
        for category_data in categories:
            category, created = SpendingCategory.objects.get_or_create(
                name=category_data['name'],
                defaults={
                    'slug': slugify(category_data['name']),
                }
            )
            if created:
                self.stdout.write(f'Created spending category: {category.name}')

    def import_credit_cards(self, cards):
        for card_data in cards:
            try:
                issuer = Issuer.objects.get(name=card_data['issuer'])
                # Handle both old and new data formats
                reward_type_name = card_data.get('reward_type') or card_data.get('primary_reward_type')
                primary_reward_type = RewardType.objects.get(name=reward_type_name)
                
                # Handle signup bonus structure
                signup_bonus = card_data.get('signup_bonus', {})
                if isinstance(signup_bonus, dict):
                    signup_bonus_amount = signup_bonus.get('bonus_amount')
                    signup_bonus_requirement = f"${signup_bonus.get('spending_requirement', 0)} in {signup_bonus.get('time_limit_months', 0)} months"
                else:
                    # Legacy format
                    signup_bonus_amount = card_data.get('signup_bonus_amount')
                    signup_bonus_requirement = card_data.get('signup_bonus_requirement', '')
                
                # For signup bonus type, use the card's reward type
                signup_bonus_type = primary_reward_type
                
                card, created = CreditCard.objects.get_or_create(
                    name=card_data['name'],
                    issuer=issuer,
                    defaults={
                        'annual_fee': card_data.get('annual_fee', 0),
                        'signup_bonus_amount': signup_bonus_amount,
                        'signup_bonus_type': signup_bonus_type,
                        'signup_bonus_requirement': signup_bonus_requirement,
                        'primary_reward_type': primary_reward_type,
                        'metadata': {
                            'reward_value_multiplier': card_data.get('reward_value_multiplier', 0.01),
                            **card_data.get('metadata', {})
                        },
                    }
                )
                
                if created:
                    self.stdout.write(f'Created card: {card}')
                    
                    # Import reward categories
                    if 'reward_categories' in card_data:
                        self.import_reward_categories(card, card_data['reward_categories'])
                    
                    # Import offers
                    if 'offers' in card_data:
                        self.import_card_offers(card, card_data['offers'])
                        
            except (Issuer.DoesNotExist, RewardType.DoesNotExist) as e:
                self.stdout.write(
                    self.style.ERROR(f'Skipping card {card_data["name"]}: {e}')
                )

    def import_reward_categories(self, card, reward_categories):
        for category_data in reward_categories:
            try:
                category = SpendingCategory.objects.get(name=category_data['category'])
                # Use card's reward type since we removed it from categories
                reward_type = card.primary_reward_type
                
                RewardCategory.objects.get_or_create(
                    card=card,
                    category=category,
                    start_date=category_data.get('start_date'),
                    defaults={
                        'reward_rate': category_data['reward_rate'],
                        'reward_type': reward_type,
                        'end_date': category_data.get('end_date'),
                        'max_annual_spend': category_data.get('max_annual_spend'),
                    }
                )
                
            except (SpendingCategory.DoesNotExist, RewardType.DoesNotExist) as e:
                self.stdout.write(
                    self.style.WARNING(f'Skipping reward category: {e}')
                )

    def import_card_offers(self, card, offers):
        for offer_data in offers:
            CardOffer.objects.get_or_create(
                card=card,
                title=offer_data['title'],
                defaults={
                    'description': offer_data.get('description', ''),
                    'value': offer_data.get('value', ''),
                    'start_date': offer_data.get('start_date'),
                    'end_date': offer_data.get('end_date'),
                }
            )