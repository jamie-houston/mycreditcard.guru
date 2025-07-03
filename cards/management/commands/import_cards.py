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
        elif filename in ['chase.json', 'american_express.json', 'citi.json', 'capital_one.json']:
            # Issuer-specific credit card files (array of cards)
            self.import_credit_cards(data)
        else:
            # Check if it's an array of credit cards vs legacy combined format
            if isinstance(data, list) and data and 'name' in data[0] and 'issuer' in data[0]:
                # Array of credit cards
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
            # Try to find existing category by name first, then by slug
            category = None
            try:
                category = SpendingCategory.objects.get(name=category_data['name'])
                created = False
            except SpendingCategory.DoesNotExist:
                try:
                    # Try to find by the new slug
                    category = SpendingCategory.objects.get(slug=slugify(category_data['name']))
                    created = False
                except SpendingCategory.DoesNotExist:
                    # Create new category
                    category = SpendingCategory.objects.create(
                        name=category_data['name'],
                        slug=slugify(category_data['name']),
                        display_name=category_data.get('display_name', ''),
                        description=category_data.get('description', ''),
                        icon=category_data.get('icon', ''),
                        sort_order=category_data.get('sort_order', 100),
                    )
                    created = True
            if created:
                self.stdout.write(f'Created spending category: {category.display_name or category.name}')
            else:
                # Update existing categories with new fields if they don't have them
                updated = False
                if not category.display_name and category_data.get('display_name'):
                    category.display_name = category_data['display_name']
                    updated = True
                if not category.description and category_data.get('description'):
                    category.description = category_data['description']
                    updated = True
                if not category.icon and category_data.get('icon'):
                    category.icon = category_data['icon']
                    updated = True
                if category.sort_order == 100 and category_data.get('sort_order', 100) != 100:
                    category.sort_order = category_data['sort_order']
                    updated = True
                    
                if updated:
                    category.save()
                    self.stdout.write(f'Updated spending category: {category.display_name or category.name}')

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
                
                # Find existing card by name and issuer
                try:
                    card = CreditCard.objects.get(name=card_data['name'], issuer=issuer)
                    # Update existing card with imported data
                    card.annual_fee = card_data.get('annual_fee', 0)
                    card.signup_bonus_amount = signup_bonus_amount
                    card.signup_bonus_type = signup_bonus_type
                    card.signup_bonus_requirement = signup_bonus_requirement
                    card.primary_reward_type = primary_reward_type
                    card.card_type = card_data.get('card_type', 'personal')
                    card.metadata = {
                        'reward_value_multiplier': card_data.get('reward_value_multiplier', 0.01),
                        **card_data.get('metadata', {})
                    }
                    card.save()
                    
                    # Clear existing reward categories and offers to replace with imported data
                    card.reward_categories.all().delete()
                    card.offers.all().delete()
                    
                    self.stdout.write(f'Updated card: {card}')
                    created = False
                except CreditCard.DoesNotExist:
                    # Create new card
                    card = CreditCard.objects.create(
                        name=card_data['name'],
                        issuer=issuer,
                        annual_fee=card_data.get('annual_fee', 0),
                        signup_bonus_amount=signup_bonus_amount,
                        signup_bonus_type=signup_bonus_type,
                        signup_bonus_requirement=signup_bonus_requirement,
                        primary_reward_type=primary_reward_type,
                        card_type=card_data.get('card_type', 'personal'),
                        metadata={
                            'reward_value_multiplier': card_data.get('reward_value_multiplier', 0.01),
                            **card_data.get('metadata', {})
                        }
                    )
                    self.stdout.write(f'Created card: {card}')
                    created = True
                
                # Import reward categories (for both new and updated cards)
                if 'reward_categories' in card_data:
                    self.import_reward_categories(card, card_data['reward_categories'])
                
                # Import offers (for both new and updated cards)
                if 'offers' in card_data:
                    self.import_card_offers(card, card_data['offers'])
                        
            except (Issuer.DoesNotExist, RewardType.DoesNotExist) as e:
                self.stdout.write(
                    self.style.ERROR(f'Skipping card {card_data["name"]}: {e}')
                )

    def import_reward_categories(self, card, reward_categories):
        for category_data in reward_categories:
            try:
                # Try case-sensitive match first
                try:
                    category = SpendingCategory.objects.get(name=category_data['category'])
                except SpendingCategory.DoesNotExist:
                    # Try case-insensitive match as fallback
                    category = SpendingCategory.objects.get(name__iexact=category_data['category'])
                
                # Use card's reward type since we removed it from categories
                reward_type = card.primary_reward_type
                
                # Create new reward category (existing ones were already deleted)
                RewardCategory.objects.create(
                    card=card,
                    category=category,
                    reward_rate=category_data['reward_rate'],
                    reward_type=reward_type,
                    start_date=category_data.get('start_date'),
                    end_date=category_data.get('end_date'),
                    max_annual_spend=category_data.get('max_annual_spend'),
                )
                
            except (SpendingCategory.DoesNotExist, RewardType.DoesNotExist) as e:
                self.stdout.write(
                    self.style.WARNING(f'Skipping reward category "{category_data["category"]}": {e}')
                )

    def import_card_offers(self, card, offers):
        for offer_data in offers:
            # Create new card offer (existing ones were already deleted)
            CardOffer.objects.create(
                card=card,
                title=offer_data['title'],
                description=offer_data.get('description', ''),
                value=offer_data.get('value', ''),
                start_date=offer_data.get('start_date'),
                end_date=offer_data.get('end_date'),
            )