"""
Field mapping utility for converting scraped data to model fields.
"""

def map_scraped_card_to_model(scraped_data):
    """
    Maps scraped field names to model field names.
    
    Args:
        scraped_data (dict): The scraped credit card data.
        
    Returns:
        dict: A dictionary with mapped field names.
    """
    field_mappings = {
        'signup_bonus_spend_requirement': 'signup_bonus_min_spend',
        'signup_bonus_time_period': 'signup_bonus_time_limit',
        'offers': 'special_offers'
    }
    
    # Create a new dictionary with mapped field names
    mapped_data = {}
    
    for key, value in scraped_data.items():
        if key in field_mappings:
            mapped_data[field_mappings[key]] = value
        else:
            mapped_data[key] = value
    
    return mapped_data 