import json
import os
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from cards.models import SpendingCredit, SpendingCategory


class Command(BaseCommand):
    help = 'Import spending credits from JSON file'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            default='data/input/system/spending_credits.json',
            help='Path to spending credits JSON file'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing spending credits before importing'
        )

    def handle(self, *args, **options):
        file_path = options['file']
        
        if not os.path.exists(file_path):
            self.stdout.write(
                self.style.ERROR(f'File not found: {file_path}')
            )
            return

        if options['clear']:
            self.stdout.write('Clearing existing spending credits...')
            SpendingCredit.objects.all().delete()

        try:
            with open(file_path, 'r') as file:
                spending_credits_data = json.load(file)
            
            created_count = 0
            updated_count = 0
            
            for credit_data in spending_credits_data:
                name = credit_data['name']
                slug = slugify(name)
                display_name = credit_data['display_name']
                description = credit_data.get('description', '')
                category_name = credit_data['category']
                
                # Find the spending category
                try:
                    category = SpendingCategory.objects.get(slug=category_name)
                except SpendingCategory.DoesNotExist:
                    self.stdout.write(
                        self.style.WARNING(f'Category not found: {category_name}. Skipping credit: {display_name}')
                    )
                    continue
                
                # Create or update spending credit
                credit, created = SpendingCredit.objects.get_or_create(
                    name=name,
                    defaults={
                        'slug': slug,
                        'display_name': display_name,
                        'description': description,
                        'category': category,
                    }
                )
                
                if not created:
                    # Update existing credit
                    credit.slug = slug
                    credit.display_name = display_name
                    credit.description = description
                    credit.category = category
                    credit.save()
                    updated_count += 1
                else:
                    created_count += 1
                
                self.stdout.write(f'{"Created" if created else "Updated"} spending credit: {display_name}')
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully processed {created_count + updated_count} spending credits '
                    f'({created_count} created, {updated_count} updated)'
                )
            )
            
        except json.JSONDecodeError as e:
            self.stdout.write(
                self.style.ERROR(f'Invalid JSON in file {file_path}: {e}')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error importing spending credits: {e}')
            ) 