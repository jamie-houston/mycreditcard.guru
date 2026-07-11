.PHONY: help run migrate test clean setup shell lint format install

VENV := venv/bin
PYTHON := $(VENV)/python
MANAGE := $(PYTHON) manage.py

# Default target
.DEFAULT_GOAL := help

# Colors for output
BLUE := \033[0;34m
GREEN := \033[0;32m
RED := \033[0;31m
NC := \033[0m # No Color

help:
	@echo "$(BLUE)Credit Card Guru - Makefile Commands$(NC)\n"
	@echo "$(GREEN)Setup & Installation:$(NC)"
	@echo "  make install         Install/upgrade dependencies from requirements.txt"
	@echo "  make setup           Initialize database with fresh data (one-time setup)"
	@echo "  make migrate         Run database migrations\n"
	@echo "$(GREEN)Running:$(NC)"
	@echo "  make run             Start development server at http://localhost:8000"
	@echo "  make run-shell       Run interactive Django shell\n"
	@echo "$(GREEN)Testing:$(NC)"
	@echo "  make test            Run test suite (85 tests)"
	@echo "  make test-all        Run full scenario suite (64/64 scenarios)\n"
	@echo "$(GREEN)Data:$(NC)"
	@echo "  make import-data     Import all card data"
	@echo "  make import-external Refresh card data from external API\n"
	@echo "$(GREEN)Maintenance:$(NC)"
	@echo "  make clean           Remove database and cache files"
	@echo "  make lint            Check code style (if available)"
	@echo "  make format          Format code (if available)\n"

# Install dependencies
install:
	@echo "$(BLUE)Installing dependencies...$(NC)"
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install -r requirements.txt

# Run development server
run:
	@echo "$(GREEN)Starting development server at http://localhost:8000$(NC)"
	$(MANAGE) runserver

# Run on specific port
run-port:
	@read -p "Enter port (default 8000): " port; \
	port=$${port:-8000}; \
	$(MANAGE) runserver $$port

# Setup database (fresh install)
setup:
	@echo "$(BLUE)Setting up database with fresh data...$(NC)"
	$(PYTHON) manage_project.py

# Run migrations
migrate:
	@echo "$(BLUE)Running database migrations...$(NC)"
	$(MANAGE) migrate

# Create superuser
superuser:
	@echo "$(BLUE)Creating superuser...$(NC)"
	$(MANAGE) createsuperuser

# Run tests
test:
	@echo "$(GREEN)Running test suite (85 tests)...$(NC)"
	$(MANAGE) test

# Run full scenario suite
test-all:
	@echo "$(GREEN)Running full scenario suite (64/64 scenarios)...$(NC)"
	RUN_ALL_SCENARIOS=1 $(MANAGE) test cards.test_json_scenarios

# Run acceptance test
test-acceptance:
	@echo "$(GREEN)Running acceptance test...$(NC)"
	$(MANAGE) run_scenario "Jamie Real" --explain

# Import all data
import-data:
	@echo "$(BLUE)Importing all card data...$(NC)"
	$(PYTHON) setup_data.py

# Refresh external card data (from andenacitelli API)
import-external:
	@echo "$(BLUE)Refreshing external card data...$(NC)"
	$(MANAGE) import_external_cards

# Django shell
shell:
	@echo "$(GREEN)Starting Django shell...$(NC)"
	$(MANAGE) shell

# Clean database and cache
clean:
	@echo "$(RED)Cleaning database and cache files...$(NC)"
	rm -f db.sqlite3
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name ".DS_Store" -delete
	@echo "$(GREEN)Cleaned.$(NC)"

# Show database info
db-info:
	@echo "$(BLUE)Database Information:$(NC)"
	$(MANAGE) shell -c "from cards.models import Card, CardIssuer, SpendingCategory; from users.models import User; from roadmaps.models import Roadmap; print(f'Credit Cards: {Card.objects.count()}'); print(f'Issuers: {CardIssuer.objects.count()}'); print(f'Categories: {SpendingCategory.objects.count()}'); print(f'Users: {User.objects.count()}'); print(f'Roadmaps: {Roadmap.objects.count()}')"

# Check if venv exists
venv-check:
	@if [ ! -d "venv" ]; then \
		echo "$(RED)Virtual environment not found.$(NC)"; \
		echo "Create it with: python3 -m venv venv"; \
		exit 1; \
	fi

# Full reset (warning!)
reset: clean
	@echo "$(RED)⚠️  Resetting database and reimporting data...$(NC)"
	$(PYTHON) setup_data.py
	@echo "$(GREEN)✓ Reset complete$(NC)"

# Check dependencies
check:
	@echo "$(BLUE)Checking environment...$(NC)"
	@command -v python3 >/dev/null 2>&1 && echo "$(GREEN)✓ Python 3 found$(NC)" || echo "$(RED)✗ Python 3 not found$(NC)"
	@[ -d "venv" ] && echo "$(GREEN)✓ Virtual environment exists$(NC)" || echo "$(RED)✗ Virtual environment not found$(NC)"
	@[ -f "requirements.txt" ] && echo "$(GREEN)✓ requirements.txt found$(NC)" || echo "$(RED)✗ requirements.txt not found$(NC)"
	@[ -f "manage.py" ] && echo "$(GREEN)✓ manage.py found$(NC)" || echo "$(RED)✗ manage.py not found$(NC)"
	@[ -f ".env" ] && echo "$(GREEN)✓ .env file exists$(NC)" || echo "$(BLUE)ℹ .env file not found (may need .env.example)$(NC)"

# Display version
version:
	@cat VERSION 2>/dev/null || echo "Version not found"

# Quick status
status: check
	@echo "\n$(BLUE)Quick Status:$(NC)"
	@$(MANAGE) migrate --check >/dev/null 2>&1 && echo "$(GREEN)✓ Database migrated$(NC)" || echo "$(RED)✗ Migrations pending$(NC)"
	@[ -f "db.sqlite3" ] && echo "$(GREEN)✓ Database exists$(NC)" || echo "$(RED)✗ Database not found (run: make setup)$(NC)"
