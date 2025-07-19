import json
import os
import glob
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from cards.models import CreditType


class Command(BaseCommand):
    help = 'Import distinct credit types from all card files'

    def handle(self, *args, **options):
        self.stdout.write('Importing credit types from card files...')
        
        # Find all card files
        card_files = glob.glob('data/input/cards/*.json')
        if not card_files:
            self.stdout.write(
                self.style.ERROR('No card files found in data/input/cards/')
            )
            return

        # Collect all unique credits
        all_credits = set()
        credit_descriptions = {}
        
        for file_path in card_files:
            if os.path.basename(file_path) == 'personal.json':
                continue  # Skip personal cards file
                
            try:
                with open(file_path, 'r') as f:
                    cards_data = json.load(f)
                    
                for card in cards_data:
                    credits = card.get('credits', [])
                    for credit in credits:
                        description = credit.get('description', '').strip()
                        if description:
                            # Normalize the description for categorization
                            normalized = self.normalize_credit_description(description)
                            all_credits.add(normalized)
                            if normalized not in credit_descriptions:
                                credit_descriptions[normalized] = description
                            
            except Exception as e:
                self.stdout.write(
                    self.style.WARNING(f'Error reading {file_path}: {e}')
                )

        self.stdout.write(f'Found {len(all_credits)} unique credit types')
        
        # Create credit types in database
        created_count = 0
        updated_count = 0
        
        for normalized_name in sorted(all_credits):
            original_description = credit_descriptions[normalized_name]
            category = self.categorize_credit(normalized_name)
            icon = self.get_credit_icon(category, normalized_name)
            sort_order = self.get_sort_order(category)
            
            credit_type, created = CreditType.objects.get_or_create(
                name=normalized_name,
                defaults={
                    'slug': slugify(normalized_name),
                    'description': original_description,
                    'category': category,
                    'icon': icon,
                    'sort_order': sort_order,
                }
            )
            
            if created:
                created_count += 1
                self.stdout.write(f'✅ Created: {credit_type.name} ({category})')
            else:
                # Update existing credit type if needed
                updated = False
                if not credit_type.category:
                    credit_type.category = category
                    updated = True
                if not credit_type.icon:
                    credit_type.icon = icon
                    updated = True
                if credit_type.sort_order == 100:  # Default value
                    credit_type.sort_order = sort_order
                    updated = True
                    
                if updated:
                    credit_type.save()
                    updated_count += 1
                    self.stdout.write(f'🔄 Updated: {credit_type.name}')

        self.stdout.write(
            self.style.SUCCESS(
                f'Import complete! Created: {created_count}, Updated: {updated_count}'
            )
        )

    def normalize_credit_description(self, description):
        """Normalize credit descriptions to group similar ones"""
        desc = description.lower().strip()
        
        # Group similar credits together
        if 'global entry' in desc or 'tsa precheck' in desc or 'nexus' in desc:
            return 'Global Entry / TSA PreCheck Credit'
        elif 'travel credit' in desc and ('edit' not in desc):
            return 'Travel Credit'
        elif 'hotel credit' in desc:
            return 'Hotel Credit'
        elif 'airline' in desc and 'credit' in desc:
            return 'Airline Credit'
        elif 'lounge' in desc:
            return 'Lounge Access'
        elif 'checked bag' in desc or 'free bag' in desc:
            return 'Free Checked Bag'
        elif 'uber' in desc:
            return 'Uber Credit'
        elif 'dining credit' in desc:
            return 'Dining Credit'
        elif 'streaming' in desc:
            return 'Streaming Credit'
        elif 'companion' in desc:
            return 'Companion Pass/Certificate'
        elif 'anniversary' in desc and ('bonus' in desc or 'credit' in desc):
            return 'Anniversary Bonus'
        elif 'clear' in desc:
            return 'CLEAR Credit'
        elif 'walmart' in desc:
            return 'Walmart+ Credit'
        elif 'instacart' in desc:
            return 'Instacart Credit'
        elif 'rideshare' in desc or 'lyft' in desc:
            return 'Rideshare Credit'
        elif 'doordash' in desc:
            return 'DoorDash Credit'
        elif 'disney' in desc:
            return 'Disney Bundle Credit'
        elif 'saks' in desc:
            return 'Saks Credit'
        elif 'dell' in desc:
            return 'Dell Credit'
        elif 'wireless' in desc:
            return 'Wireless Credit'
        elif 'avis' in desc or 'budget' in desc:
            return 'Car Rental Credit'
        else:
            # Keep original description for unique credits
            return description.strip()

    def categorize_credit(self, credit_name):
        """Categorize credits for better organization"""
        name_lower = credit_name.lower()
        
        if any(word in name_lower for word in ['travel', 'hotel', 'airline', 'global entry', 'tsa', 'lounge', 'checked bag']):
            return 'travel'
        elif any(word in name_lower for word in ['dining', 'uber', 'doordash', 'grubhub']):
            return 'dining'
        elif any(word in name_lower for word in ['streaming', 'disney', 'apple', 'entertainment']):
            return 'entertainment'
        elif any(word in name_lower for word in ['rideshare', 'lyft', 'car rental', 'avis']):
            return 'transportation'
        elif any(word in name_lower for word in ['walmart', 'instacart', 'groceries']):
            return 'shopping'
        elif any(word in name_lower for word in ['wireless', 'dell', 'tech']):
            return 'tech'
        else:
            return 'misc'

    def get_credit_icon(self, category, credit_name):
        """Get appropriate icon for credit type"""
        name_lower = credit_name.lower()
        
        # Specific icons for common credits
        if 'global entry' in name_lower or 'tsa' in name_lower:
            return '🛂'
        elif 'lounge' in name_lower:
            return '🏟️'
        elif 'hotel' in name_lower:
            return '🏨'
        elif 'airline' in name_lower:
            return '✈️'
        elif 'travel' in name_lower:
            return '🧳'
        elif 'dining' in name_lower:
            return '🍽️'
        elif 'uber' in name_lower:
            return '🚗'
        elif 'streaming' in name_lower:
            return '📺'
        elif 'checked bag' in name_lower:
            return '🎒'
        elif 'clear' in name_lower:
            return '🔍'
        elif 'companion' in name_lower:
            return '👥'
        elif 'anniversary' in name_lower:
            return '🎂'
        
        # Category-based icons
        category_icons = {
            'travel': '✈️',
            'dining': '🍽️',
            'entertainment': '🎬',
            'transportation': '🚗',
            'shopping': '🛍️',
            'tech': '💻',
            'misc': '💳'
        }
        
        return category_icons.get(category, '💳')

    def get_sort_order(self, category):
        """Get sort order based on category"""
        sort_orders = {
            'travel': 10,
            'dining': 20,
            'transportation': 30,
            'entertainment': 40,
            'shopping': 50,
            'tech': 60,
            'misc': 70
        }
        
        return sort_orders.get(category, 100)