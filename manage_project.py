#!/usr/bin/env python3
"""
Interactive project management script for Credit Card Guru.
Provides a menu-driven interface for common development tasks.
"""

import os
import sys
import subprocess
import glob
from pathlib import Path


class Colors:
    """ANSI color codes for terminal output."""
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


def print_header(text):
    """Print a formatted header."""
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*60}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.CYAN}{text.center(60)}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'='*60}{Colors.ENDC}\n")


def print_success(text):
    """Print success message."""
    print(f"{Colors.GREEN}✓ {text}{Colors.ENDC}")


def print_error(text):
    """Print error message."""
    print(f"{Colors.RED}✗ {text}{Colors.ENDC}")


def print_info(text):
    """Print info message."""
    print(f"{Colors.BLUE}ℹ {text}{Colors.ENDC}")


def print_warning(text):
    """Print warning message."""
    print(f"{Colors.YELLOW}⚠ {text}{Colors.ENDC}")


def run_command(command, description=None, show_output=True):
    """
    Run a shell command and return success status.

    Args:
        command: Command string to execute
        description: Optional description to display
        show_output: Whether to show command output in real-time

    Returns:
        True if command succeeded, False otherwise
    """
    if description:
        print(f"\n{Colors.BOLD}{description}...{Colors.ENDC}")

    print(f"{Colors.CYAN}Running: {command}{Colors.ENDC}\n")

    try:
        if show_output:
            # Show output in real-time
            result = subprocess.run(
                command,
                shell=True,
                check=True,
                text=True
            )
        else:
            # Capture output
            result = subprocess.run(
                command,
                shell=True,
                check=True,
                capture_output=True,
                text=True
            )
            if result.stdout:
                print(result.stdout)

        print_success(f"{description or 'Command'} completed successfully\n")
        return True

    except subprocess.CalledProcessError as e:
        print_error(f"{description or 'Command'} failed")
        if hasattr(e, 'stderr') and e.stderr:
            print(f"\n{Colors.RED}{e.stderr}{Colors.ENDC}")
        return False


def check_virtual_env():
    """Check if virtual environment is activated."""
    if not os.environ.get('VIRTUAL_ENV'):
        print_warning("Virtual environment not detected!")
        print_info("Activate with: source venv/bin/activate")
        response = input("\nContinue anyway? (y/n): ").lower()
        if response != 'y':
            return False
    return True


def run_server():
    """Start the Django development server."""
    print_header("Starting Development Server")
    print_info("Server will start at http://127.0.0.1:8000/")
    print_info("Press Ctrl+C to stop the server\n")

    input("Press Enter to start the server...")
    run_command("python manage.py runserver", show_output=True)


def run_tests():
    """Run the Django test suite."""
    print_header("Running Tests")

    print("Test options:")
    print("1. Run all tests")
    print("2. Run tests for specific app (cards, roadmaps, users)")
    print("3. Run specific test file")
    print("4. Back to main menu")

    choice = input("\nSelect option (1-4): ").strip()

    if choice == '1':
        run_command("python manage.py test", "Running all tests")
    elif choice == '2':
        app_name = input("Enter app name (cards/roadmaps/users): ").strip()
        if app_name in ['cards', 'roadmaps', 'users']:
            run_command(f"python manage.py test {app_name}", f"Running {app_name} tests")
        else:
            print_error("Invalid app name")
    elif choice == '3':
        test_path = input("Enter test path (e.g., cards.tests.test_models): ").strip()
        run_command(f"python manage.py test {test_path}", f"Running {test_path}")
    elif choice == '4':
        return
    else:
        print_error("Invalid option")


def reset_database():
    """Reset the database and reload all data."""
    print_header("Reset Database")

    print_warning("This will DELETE all existing data!")
    print_info("The following will be performed:")
    print("  • Delete db.sqlite3")
    print("  • Run migrations to create fresh database")
    print("  • Load all initial data (categories, issuers, cards)")

    confirm = input("\nType 'RESET' to confirm: ").strip()

    if confirm != 'RESET':
        print_info("Database reset cancelled")
        return

    # Check if database exists
    db_path = 'db.sqlite3'
    if os.path.exists(db_path):
        print_info(f"Deleting {db_path}...")
        os.remove(db_path)
        print_success("Database deleted")

    # Run migrations
    if not run_command("python manage.py migrate", "Running migrations"):
        print_error("Migration failed. Stopping reset process.")
        return

    # Create superuser prompt
    print("\n")
    create_super = input("Create superuser now? (y/n): ").lower()
    if create_super == 'y':
        print_info("Follow the prompts to create a superuser account")
        run_command("python manage.py createsuperuser", show_output=True)

    # Setup Google OAuth app
    print_info("Setting up Google OAuth app...")
    setup_oauth_command = """python manage.py shell << 'EOF'
from allauth.socialaccount.models import SocialApp
from django.contrib.sites.models import Site
import os

site = Site.objects.get_current()
google_app = SocialApp.objects.filter(provider='google').first()

if not google_app:
    client_id = os.getenv('GOOGLE_OAUTH_CLIENT_ID', 'placeholder')
    client_secret = os.getenv('GOOGLE_OAUTH_CLIENT_SECRET', 'placeholder')

    google_app = SocialApp.objects.create(
        provider='google',
        name='Google OAuth',
        client_id=client_id,
        secret=client_secret,
    )
    google_app.sites.add(site)
    print("Created Google OAuth app")
else:
    print("Google OAuth app already exists")
EOF"""
    run_command(setup_oauth_command, "Setting up OAuth")

    # Load initial data
    load_data()

    print_success("Database reset complete!")


def migrate_database():
    """Run database migrations."""
    print_header("Database Migration")

    print("Migration options:")
    print("1. Show migration status")
    print("2. Run all pending migrations")
    print("3. Make new migrations")
    print("4. Make migrations for specific app")
    print("5. Back to main menu")

    choice = input("\nSelect option (1-5): ").strip()

    if choice == '1':
        run_command("python manage.py showmigrations", "Showing migration status")
    elif choice == '2':
        run_command("python manage.py migrate", "Running migrations")
    elif choice == '3':
        run_command("python manage.py makemigrations", "Creating migrations")
    elif choice == '4':
        app_name = input("Enter app name: ").strip()
        run_command(f"python manage.py makemigrations {app_name}", f"Creating {app_name} migrations")
    elif choice == '5':
        return
    else:
        print_error("Invalid option")


def load_data():
    """Import credit card data and system data."""
    print_header("Import Credit Card Data")

    print("Import options:")
    print("1. Import ALL data (recommended for fresh database)")
    print("2. Import system data only (categories, issuers, reward types)")
    print("3. Import credit cards only")
    print("4. Import specific issuer cards")
    print("5. Run setup_data.py script")
    print("6. Back to main menu")

    choice = input("\nSelect option (1-6): ").strip()

    if choice == '1':
        import_all_data()
    elif choice == '2':
        import_system_data()
    elif choice == '3':
        import_all_cards()
    elif choice == '4':
        import_specific_issuer()
    elif choice == '5':
        run_command("python setup_data.py", "Running setup_data.py")
    elif choice == '6':
        return
    else:
        print_error("Invalid option")


def import_system_data():
    """Import system data (categories, issuers, reward types)."""
    print_info("Importing system data...")

    system_files = [
        ('data/input/system/spending_categories.json', 'Spending Categories'),
        ('data/input/system/issuers.json', 'Issuers'),
        ('data/input/system/reward_types.json', 'Reward Types')
    ]

    success_count = 0
    for file_path, name in system_files:
        if os.path.exists(file_path):
            if run_command(f"python manage.py import_cards {file_path}", f"Loading {name}", show_output=False):
                success_count += 1
        else:
            print_warning(f"{file_path} not found, skipping...")

    print_success(f"Imported {success_count}/{len(system_files)} system data files")


def import_all_cards():
    """Import all credit card data."""
    print_info("Searching for card files...")

    card_files = glob.glob('data/input/cards/*.json')
    # Exclude personal.json template
    card_files = [f for f in card_files if not f.endswith('personal.json')]

    if not card_files:
        print_error("No card files found in data/input/cards/")
        return

    print_info(f"Found {len(card_files)} card files")

    for card_file in sorted(card_files):
        issuer_name = Path(card_file).stem.replace('_', ' ').title()
        run_command(f"python manage.py import_cards {card_file}", f"Importing {issuer_name} cards", show_output=False)

    # Import spending credits (used by card benefits)
    run_command("python manage.py import_spending_credits", "Importing spending credits", show_output=False)

    # Import credit types (benefits/offers)
    run_command("python manage.py import_credit_types", "Importing credit types", show_output=False)

    print_success("All card imports complete!")


def import_specific_issuer():
    """Import cards from a specific issuer."""
    print_info("Available card files:")

    card_files = glob.glob('data/input/cards/*.json')
    card_files = [f for f in card_files if not f.endswith('personal.json')]

    if not card_files:
        print_error("No card files found in data/input/cards/")
        return

    for i, card_file in enumerate(sorted(card_files), 1):
        issuer_name = Path(card_file).stem.replace('_', ' ').title()
        print(f"{i}. {issuer_name} ({Path(card_file).name})")

    try:
        choice = int(input("\nSelect file number: ").strip())
        if 1 <= choice <= len(card_files):
            selected_file = sorted(card_files)[choice - 1]
            issuer_name = Path(selected_file).stem.replace('_', ' ').title()
            run_command(f"python manage.py import_cards {selected_file}", f"Importing {issuer_name} cards")
        else:
            print_error("Invalid selection")
    except ValueError:
        print_error("Invalid input")


def import_all_data():
    """Import all system data and credit cards."""
    print_info("This will import all system data and credit cards")

    # Import system data first
    import_system_data()

    print()

    # Import all cards
    import_all_cards()

    print_success("All data imported successfully!")


def show_database_info():
    """Show database statistics."""
    print_header("Database Information")

    info_command = """python manage.py shell << 'EOF'
from cards.models import CreditCard, Issuer, SpendingCategory
from users.models import User
from roadmaps.models import Roadmap

print(f"Credit Cards: {CreditCard.objects.count()}")
print(f"Issuers: {Issuer.objects.count()}")
print(f"Spending Categories: {SpendingCategory.objects.count()}")
print(f"Users: {User.objects.count()}")
print(f"Roadmaps: {Roadmap.objects.count()}")
EOF"""

    run_command(info_command, "Fetching database statistics", show_output=True)


def manage_superuser():
    """Create or manage superuser accounts."""
    print_header("Superuser Management")

    print("Superuser options:")
    print("1. Create new superuser")
    print("2. Change superuser password")
    print("3. Back to main menu")

    choice = input("\nSelect option (1-3): ").strip()

    if choice == '1':
        print_info("Follow the prompts to create a superuser account")
        run_command("python manage.py createsuperuser", show_output=True)
    elif choice == '2':
        username = input("Enter username: ").strip()
        run_command(f"python manage.py changepassword {username}", show_output=True)
    elif choice == '3':
        return
    else:
        print_error("Invalid option")


def django_shell():
    """Open Django shell."""
    print_header("Django Shell")
    print_info("Opening Django shell...")
    print_info("Type 'exit()' to return to this menu\n")
    input("Press Enter to continue...")
    run_command("python manage.py shell", show_output=True)


def show_menu():
    """Display the main menu."""
    print_header("Credit Card Guru - Project Management")

    print(f"{Colors.BOLD}Main Menu:{Colors.ENDC}")
    print()
    print("  1. Run development server")
    print("  2. Run tests")
    print("  3. Reset database (delete and recreate)")
    print("  4. Migrate database (run migrations)")
    print("  5. Import credit card data")
    print("  6. Show database info")
    print("  7. Manage superuser")
    print("  8. Open Django shell")
    print("  9. Exit")
    print()


def main():
    """Main entry point."""
    # Check we're in the right directory
    if not os.path.exists('manage.py'):
        print_error("Error: manage.py not found!")
        print_info("Please run this script from the project root directory")
        sys.exit(1)

    # Check virtual environment
    if not check_virtual_env():
        sys.exit(1)

    while True:
        show_menu()

        choice = input(f"{Colors.BOLD}Select option (1-9): {Colors.ENDC}").strip()

        if choice == '1':
            run_server()
        elif choice == '2':
            run_tests()
        elif choice == '3':
            reset_database()
        elif choice == '4':
            migrate_database()
        elif choice == '5':
            load_data()
        elif choice == '6':
            show_database_info()
        elif choice == '7':
            manage_superuser()
        elif choice == '8':
            django_shell()
        elif choice == '9':
            print_success("Goodbye!")
            sys.exit(0)
        else:
            print_error("Invalid option. Please select 1-9.")

        input(f"\n{Colors.BOLD}Press Enter to continue...{Colors.ENDC}")
        print("\n" * 2)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}Interrupted by user{Colors.ENDC}")
        sys.exit(0)
