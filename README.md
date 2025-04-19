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

## Future Enhancements

- Add more data sources beyond NerdWallet
- Implement more detailed reward calculations
- Add user accounts and authentication
- Create a more sophisticated recommendation algorithm 