# Project Structure

This document outlines the organized structure of the Credit Card Roadmap project.

## Directory Organization

### Root Level
```
creditcard-roadmap/
├── flask_app/           # Main Flask application
├── scripts/             # Utility scripts and data processing tools
├── tests/               # Test files for scripts and utilities
├── data/                # Data files, JSON exports, and debug HTML files
├── requirements.txt     # Python dependencies
├── README.md           # Main project documentation
└── Project Design.md   # Design documentation
```

### Flask Application (`flask_app/`)
```
flask_app/
├── app/                 # Main application package
│   ├── auth/           # Authentication blueprints
│   ├── blueprints/     # Feature blueprints (recommendations, etc.)
│   ├── controllers/    # Request handlers
│   ├── engine/         # Recommendation engine
│   ├── models/         # Database models
│   ├── routes/         # Route definitions
│   ├── services/       # Business logic services
│   ├── static/         # CSS, JS, images
│   ├── templates/      # Jinja2 templates
│   └── utils/          # Utility functions
├── scripts/            # Flask app specific scripts
├── tests/              # Flask app tests
├── migrations/         # Database migrations
├── config.py           # Configuration
├── wsgi.py            # WSGI entry point
└── run.py             # Development server
```

### Scripts Directory (`scripts/`)
- `extract_card_info.py` - Web scraping and card data extraction
- `integrate_card_data.py` - Data integration and preparation
- `debug_parsing.py` - Debugging tools for parsing functions
- `migrate_to_flask3.py` - Flask 3.x migration utilities

### Tests Directory (`tests/`)
- `test_category_bonuses.py` - Tests for category bonus parsing
- `test_extraction.py` - Tests for data extraction functions

### Data Directory (`data/`)
- `*.json` files - Extracted card data
- `*.html` files - Debug HTML files from web scraping
- `cookies.txt` - Web scraping session data

## Running the Application

### Flask App
```bash
cd flask_app
python run.py
```

### Running Tests
```bash
# Root level tests
`python ./scripts/run_tests.py -y` to run all of the tests.

### Running Scripts
```bash
# From root directory
python scripts/run_python_scripts.py
```

## Import Path Notes

- Scripts in `scripts/` can import from each other directly
- Scripts importing from `flask_app/` need to add the parent directory to `sys.path`
- Tests in `tests/` have been updated to import from `scripts/` correctly
- Flask app internal imports remain unchanged
