# Credit Card Roadmap

A Flask web application for tracking and comparing credit card offers.

## Project Overview

This application allows users to:
- Browse and compare credit card offers
- Import credit card data from various sources
- Track signup bonuses and reward categories
- Make informed decisions about which cards to apply for

## Project Structure

The project follows a standard Flask application structure:

```
/project-root/
├── app/                  # Main application package
│   ├── __init__.py       # Flask app factory
│   ├── models/           # Database models
│   ├── routes/           # Route handlers 
│   ├── templates/        # Jinja2 templates
│   ├── static/           # CSS, JS, and images
│   └── utils/            # Helper functions
├── migrations/           # Database migrations (Alembic)
├── tests/                # Test suite
├── scripts/              # Utility scripts
├── config.py             # Configuration settings
├── wsgi.py               # WSGI entry point for production
├── run.py                # Development server script
└── requirements.txt      # Python dependencies
```

## Setup

1. Clone the repository
2. Create a virtual environment: `python -m venv venv`
3. Activate the virtual environment:
   - Windows: `venv\Scripts\activate`
   - macOS/Linux: `source venv/bin/activate`
4. Install dependencies: `pip install -r requirements.txt`
5. Initialize the database: `python reset_db.py`
6. Run the development server: `python run.py`

## Deployment

See `PYTHONANYWHERE_DEPLOY.md` for detailed deployment instructions for PythonAnywhere.

## Features

- Credit card database with detailed information
- Web scraping to import card data from various sources
- Responsive UI built with Bootstrap
- Flask-SQLAlchemy for database management
- SQLAlchemy 2.x compatibility

## License

MIT License 