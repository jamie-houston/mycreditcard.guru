import json

def map_scraped_card_to_model(scraped_data):
    """
    Maps field names from scraped data to match the CreditCard model fields.
    Also processes reward categories using the Category aliases system.
    
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
    
    # Process reward categories using Category aliases system
    if 'reward_categories' in mapped_data:
        processed_categories = process_reward_categories_with_aliases(mapped_data['reward_categories'])
        mapped_data['reward_categories'] = processed_categories
    
    # Convert list or dict fields to JSON strings if necessary
    for field in ['reward_categories', 'special_offers']:
        if field in mapped_data and (isinstance(mapped_data[field], list) or isinstance(mapped_data[field], dict)):
            mapped_data[field] = json.dumps(mapped_data[field])
    
    return mapped_data

def process_reward_categories_with_aliases(reward_categories_data):
    """
    Process reward categories using the Category model's aliases system.
    
    Args:
        reward_categories_data: Can be dict, list, or JSON string
        
    Returns:
        list: Processed reward categories with mapped category names
    """
    from app.models.category import Category
    
    # Handle different input formats
    if isinstance(reward_categories_data, str):
        try:
            reward_categories_data = json.loads(reward_categories_data)
        except (json.JSONDecodeError, TypeError):
            return []
    
    if not reward_categories_data:
        return []
    
    processed_categories = []
    unmapped_categories = []
    
    # Handle dict format (category_name: rate)
    if isinstance(reward_categories_data, dict):
        for category_name, rate in reward_categories_data.items():
            category = Category.get_by_name_or_alias(category_name.strip())
            if category:
                processed_categories.append({
                    'category': category.name,
                    'percentage': float(rate) if rate else 1.0
                })
            else:
                # Keep unmapped categories as-is for now
                processed_categories.append({
                    'category': category_name.strip(),
                    'percentage': float(rate) if rate else 1.0
                })
                unmapped_categories.append(category_name.strip())
    
    # Handle list format
    elif isinstance(reward_categories_data, list):
        for item in reward_categories_data:
            if isinstance(item, dict):
                category_name = item.get('category', '')
                rate = item.get('percentage', item.get('rate', 1.0))
                
                if category_name:
                    category = Category.get_by_name_or_alias(category_name.strip())
                    if category:
                        processed_categories.append({
                            'category': category.name,
                            'percentage': float(rate) if rate else 1.0
                        })
                    else:
                        # Keep unmapped categories as-is for now
                        processed_categories.append({
                            'category': category_name.strip(),
                            'percentage': float(rate) if rate else 1.0
                        })
                        unmapped_categories.append(category_name.strip())
    
    # Log unmapped categories for debugging
    if unmapped_categories:
        print(f"Warning: Unmapped reward categories: {unmapped_categories}")
    
    return processed_categories 