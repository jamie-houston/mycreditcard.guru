# Credit Card Roadmap

A Flask web application to help users create a roadmap for credit card applications based on their spending habits and desired rewards.

## Overview

The Credit Card Roadmap app allows users to:
- Import credit card data from NerdWallet
- Input their spending habits and desired rewards
- Get recommendations on which credit cards to apply for and when
- Visualize potential rewards over time

## Features

- Credit card data storage and management
- Web scraping from NerdWallet to get current card information
- User spending profile creation
- Recommendation engine to optimize card applications
- User-friendly web interface

## Technical Details

- Built with Python/Flask
- SQLAlchemy ORM for database access
- Beautiful Soup for web scraping
- Bootstrap for frontend styling

## Setup

1. Clone the repository
2. Install dependencies:
   ```
   pip install -r creditcard_roadmap/requirements.txt
   ```
3. Initialize the database:
   ```
   cd creditcard_roadmap
   flask db upgrade
   ```
4. Run the application:
   ```
   python run.py
   ```

## Project Structure

- `/app` - Main application code
  - `/models` - Database models
  - `/routes` - Route definitions
  - `/templates` - HTML templates
  - `/static` - CSS, JS, and other static files
  - `/utils` - Utility functions
- `/scripts` - Management scripts
- `/migrations` - Database migrations

## Importing Credit Cards

There are several ways to import credit card data:

1. **From an HTML file**:
   ```
   python extract_card_info.py path/to/nerdwallet.html
   ```

2. **From a URL**:
   ```
   python integrate_card_data.py https://www.nerdwallet.com/best/credit-cards/
   ```

3. **From a JSON file**:
   ```
   cd flask_app
   python -m scripts.import_cards --json path/to/cards.json
   ```

When importing cards, the system will automatically handle duplicates by matching on card name and issuer. If a card with the same name and issuer already exists in the database, all its fields will be overwritten with the new values, effectively updating the card information.

## Future Enhancements

- Add more data sources beyond NerdWallet
- Implement more detailed reward calculations
- Add user accounts and authentication
- Create a more sophisticated recommendation algorithm 