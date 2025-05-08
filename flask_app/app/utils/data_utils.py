import json

def map_scraped_card_to_model(scraped_data):
    """
    Maps field names from scraped data to match the CreditCard model fields.
    
    Args:
        scraped_data (dict): Card data from scraper
        
    Returns:
        dict: Mapped data ready for the CreditCard model
    """
    # Define field mappings from scraper to model
    field_mappings = {
        'signup_bonus_spend_requirement': 'signup_bonus_min_spend',
        'signup_bonus_time_period': 'signup_bonus_time_limit',
        'offers': 'special_offers',
        'category': None  # Field to be removed
    }
    
    # Create a new dictionary with mapped field names
    mapped_data = {}
    
    for key, value in scraped_data.items():
        if key in field_mappings:
            # Skip keys that map to None (fields to be removed)
            if field_mappings[key] is not None:
                mapped_data[field_mappings[key]] = value
        else:
            mapped_data[key] = value
    
    # Convert list or dict fields to JSON strings if necessary
    for field in ['reward_categories', 'special_offers']:
        if field in mapped_data and (isinstance(mapped_data[field], list) or isinstance(mapped_data[field], dict)):
            mapped_data[field] = json.dumps(mapped_data[field])
    
    return mapped_data 