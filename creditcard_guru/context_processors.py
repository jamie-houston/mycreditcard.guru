"""
Context processors for creditcard_guru project.
Provides global template variables across all templates.
"""
from datetime import datetime
from django.db.models import Max
from cards.models import CreditCard


def footer_context(request):
    """
    Provides footer-related context variables to all templates.
    
    Returns:
        dict: Context variables including:
            - current_year: Current year for copyright
            - last_import_date: Last time cards were imported/updated
    """
    # Get current year for copyright
    current_year = datetime.now().year
    
    # Get the last time any credit card was updated (indicates last import)
    last_import_date = None
    try:
        # Find the most recently updated credit card
        latest_card_update = CreditCard.objects.aggregate(
            latest_update=Max('updated_at')
        )['latest_update']
        
        if latest_card_update:
            last_import_date = latest_card_update
    except Exception:
        # If there's any database error, just set to None
        # This ensures the site doesn't break if there are no cards yet
        pass
    
    return {
        'current_year': current_year,
        'last_import_date': last_import_date,
    }
