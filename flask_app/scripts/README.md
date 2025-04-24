# Credit Card Roadmap Scripts

This directory contains utility scripts for the Credit Card Roadmap application.

## NerdWallet Credit Card Scraper

### Overview

The NerdWallet scraper is a specialized tool for extracting credit card information from the NerdWallet website. It uses BeautifulSoup to parse the HTML content and extract details such as:

- Card name and issuer
- Annual fee
- Reward categories and rates
- Signup bonus information (points, value, minimum spend, time period)
- Special offers and perks

### Scripts

Two scripts are available for working with the NerdWallet scraper:

1. `test_nerdwallet_scraper.py` - A simple test script that runs the scraper and displays the results
2. `scrape_nerdwallet.py` - A full-featured command-line tool for scraping, saving, and importing card data

### Using the Scraper

#### Basic Testing

To test the scraper without modifying the database:

```bash
# Run the test script
./test_nerdwallet_scraper.py
```

This will:
- Scrape credit cards from NerdWallet
- Display summary information
- Save the results to a timestamped JSON file

#### Command-line Interface

The `scrape_nerdwallet.py` script provides more options:

```bash
# Display usage information
./scrape_nerdwallet.py --help

# Scrape and save to a specific JSON file
./scrape_nerdwallet.py --json cards.json

# Scrape and import directly to the database
./scrape_nerdwallet.py --import

# Display detailed information for each card
./scrape_nerdwallet.py --detail

# Scrape quietly (no output except errors)
./scrape_nerdwallet.py --quiet --json cards.json
```

#### Command-line Options

- `--json` / `-j`: Save the scraped data to a JSON file (specify filename)
- `--import` / `-i`: Import the scraped data directly into the database
- `--detail` / `-d`: Display detailed information for each card
- `--quiet` / `-q`: Suppress output except for errors

### Examples

#### Scrape and Display Cards

```bash
./scrape_nerdwallet.py
```

#### Scrape and Import to Database

```bash
./scrape_nerdwallet.py --import
```

#### Scrape and Save to JSON

```bash
./scrape_nerdwallet.py --json nerdwallet_cards.json
```

### Implementation Details

The scraper is implemented in `app/utils/nerdwallet_scraper.py`. It provides:

- `NerdWalletScraper` class: Handles the web scraping functionality
- `scrape_nerdwallet_cards()` function: Main entry point for the scraper

The scraper is designed to handle both the standard card container format and the table format on NerdWallet's website.

### Logging

The scraper uses Python's logging module to provide information about the scraping process. By default, it logs at the INFO level and includes timestamps. 

If debugging is enabled (the default setting), the HTML content will be saved to a file named `nerdwallet_debug.html` for inspection. 