#!/usr/bin/env python3
"""
Admin Script for Credit Card Guru Project

This script provides common administrative tasks for the Django project.
Run with: python admin.py <task> [options]
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path

# Project root directory
PROJECT_ROOT = Path(__file__).parent

def run_command(command, description=None):
    """Run a shell command and handle errors."""
    if description:
        print(f"\n🔄 {description}")
    
    print(f"Running: {command}")
    
    try:
        result = subprocess.run(
            command,
            shell=True,
            check=True,
            cwd=PROJECT_ROOT,
            capture_output=False
        )
        print(f"✅ Success!")
        return result
    except subprocess.CalledProcessError as e:
        print(f"❌ Command failed with exit code {e.returncode}")
        sys.exit(1)

def setup_environment():
    """Set up Django environment."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'creditcard_guru.settings')
    
    # Load .env file if it exists
    env_file = PROJECT_ROOT / '.env'
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                if line.strip() and not line.startswith('#'):
                    if '=' in line:
                        key, value = line.strip().split('=', 1)
                        os.environ.setdefault(key, value)

def install_dependencies():
    """Install Python dependencies."""
    run_command("pip install -r requirements.txt", "Installing dependencies")

def setup_database():
    """Set up the database with migrations."""
    run_command("python manage.py makemigrations", "Creating migrations")
    run_command("python manage.py migrate", "Running migrations")

def setup_google_oauth():
    """Set up Google OAuth SocialApp from environment variables."""
    # Django setup
    import django
    django.setup()
    
    from allauth.socialaccount.models import SocialApp
    from django.contrib.sites.models import Site
    
    client_id = os.environ.get('GOOGLE_OAUTH_CLIENT_ID')
    client_secret = os.environ.get('GOOGLE_OAUTH_CLIENT_SECRET')
    
    if not client_id or not client_secret:
        print("⚠️  Google OAuth credentials not found in environment variables")
        print("   Set GOOGLE_OAUTH_CLIENT_ID and GOOGLE_OAUTH_CLIENT_SECRET in .env file")
        return
    
    try:
        # Get or create the default site
        site = Site.objects.get(pk=1)
        
        # Check if Google SocialApp already exists
        social_app, created = SocialApp.objects.get_or_create(
            provider='google',
            defaults={
                'name': 'Google',
                'client_id': client_id,
                'secret': client_secret,
            }
        )
        
        if created:
            social_app.sites.add(site)
            print("✅ Created Google OAuth SocialApp")
        else:
            # Update existing app with new credentials
            social_app.client_id = client_id
            social_app.secret = client_secret
            social_app.save()
            if site not in social_app.sites.all():
                social_app.sites.add(site)
            print("✅ Updated Google OAuth SocialApp with new credentials")
        
        print(f"   Client ID: {client_id}")
        print(f"   Site: {site.domain}")
        
    except Exception as e:
        print(f"❌ Failed to set up Google OAuth: {e}")
        print("   Make sure the database is migrated first")

def create_superuser():
    """Create Django superuser."""
    run_command("python manage.py createsuperuser", "Creating superuser")

def run_tests():
    """Run Django tests."""
    run_command("python manage.py test", "Running tests")

def run_server(port=8000):
    """Run Django development server."""
    run_command(f"python manage.py runserver {port}", f"Starting development server on port {port}")

def import_sample_data():
    """Interactive import of data files from data/input directory."""
    data_dir = PROJECT_ROOT / "data" / "input"
    system_dir = data_dir / "system"
    cards_dir = data_dir / "cards"
    
    # Check if directories exist
    if not data_dir.exists():
        print("❌ data/input directory not found")
        return
    
    # Get JSON files from both subdirectories
    system_files = list(system_dir.glob("*.json")) if system_dir.exists() else []
    card_files = list(cards_dir.glob("*.json")) if cards_dir.exists() else []
    
    # Also check for any JSON files in the root data/input directory (legacy)
    legacy_files = list(data_dir.glob("*.json"))
    
    all_files = system_files + card_files + legacy_files
    
    if not all_files:
        print("❌ No JSON files found in data/input directories")
        return
    
    # Track imported files to show status
    imported_files = set()
    
    while True:
        print("\n📁 Available files for import:")
        print("=" * 50)
        
        # Show options with import status, organized by category
        options = {}
        option_num = 1
        
        # Show system files first
        if system_files:
            print("\n🔧 System Files (import these first):")
            for file_path in sorted(system_files, key=lambda x: x.name):
                filename = file_path.name
                status = " ✅" if file_path in imported_files else ""
                print(f"  {option_num}. {filename}{status}")
                options[str(option_num)] = file_path
                option_num += 1
        
        # Show card files
        if card_files:
            print("\n💳 Card Files:")
            for file_path in sorted(card_files, key=lambda x: x.name):
                filename = file_path.name
                status = " ✅" if file_path in imported_files else ""
                print(f"  {option_num}. {filename}{status}")
                options[str(option_num)] = file_path
                option_num += 1
        
        # Show legacy files if any
        if legacy_files:
            print("\n📄 Legacy Files (in root):")
            for file_path in sorted(legacy_files, key=lambda x: x.name):
                filename = file_path.name
                status = " ✅" if file_path in imported_files else ""
                print(f"  {option_num}. {filename}{status}")
                options[str(option_num)] = file_path
                option_num += 1
        
        print("  a. Import all remaining files")
        print("  q. Finish/Cancel")
        
        try:
            choice = input("\nSelect file(s) to import: ").strip().lower()
            
            if choice == 'q':
                if imported_files:
                    print(f"✅ Import session completed! Imported {len(imported_files)} file(s).")
                else:
                    print("Import cancelled")
                return
            
            if choice == 'a':
                # Import all files in a logical order: system files first, then cards
                
                # System files in dependency order
                system_order = [
                    "issuers.json",
                    "reward_types.json", 
                    "spending_categories.json",
                    "spending_credits.json",
                    "credit_cards.json"
                ]
                
                print("\n🔧 Importing system files first...")
                # Import system files in preferred order
                for preferred_file in system_order:
                    for file_path in system_files:
                        if file_path.name == preferred_file and file_path not in imported_files:
                            print(f"\n📄 Importing {file_path.name}")
                            
                            # Use appropriate import command based on file type
                            if file_path.name == "spending_credits.json":
                                run_command(f"python manage.py import_spending_credits", f"Importing {file_path.name}")
                            else:
                                run_command(f"python manage.py import_cards {file_path}", f"Importing {file_path.name}")
                            imported_files.add(file_path)
                
                # Import any remaining system files
                for file_path in system_files:
                    if file_path not in imported_files:
                        print(f"\n📄 Importing {file_path.name}")
                        
                        # Use appropriate import command based on file type
                        if file_path.name == "spending_credits.json":
                            run_command(f"python manage.py import_spending_credits", f"Importing {file_path.name}")
                        else:
                            run_command(f"python manage.py import_cards {file_path}", f"Importing {file_path.name}")
                        imported_files.add(file_path)
                
                print("\n💳 Importing card files...")
                # Import all card files (alphabetically)
                for file_path in sorted(card_files, key=lambda x: x.name):
                    if file_path not in imported_files:
                        print(f"\n📄 Importing {file_path.name}")
                        run_command(f"python manage.py import_cards {file_path}", f"Importing {file_path.name}")
                        imported_files.add(file_path)
                
                # Import any legacy files
                for file_path in legacy_files:
                    if file_path not in imported_files:
                        print(f"\n📄 Importing {file_path.name}")
                        run_command(f"python manage.py import_cards {file_path}", f"Importing {file_path.name}")
                        imported_files.add(file_path)
                
                print(f"\n✅ All files imported! Total: {len(imported_files)} files.")
                return
            
            if choice in options:
                file_path = options[choice]
                if file_path in imported_files:
                    print(f"⚠️  {file_path.name} has already been imported.")
                    continue_choice = input("Import again? (y/n): ").strip().lower()
                    if continue_choice != 'y':
                        continue
                
                print(f"\n📄 Importing {file_path.name}")
                
                # Use appropriate import command based on file type
                if file_path.name == "spending_credits.json":
                    run_command(f"python manage.py import_spending_credits", f"Importing {file_path.name}")
                else:
                    run_command(f"python manage.py import_cards {file_path}", f"Importing {file_path.name}")
                imported_files.add(file_path)
                print(f"✅ {file_path.name} imported successfully!")
                # Continue to show menu again
                continue
            
            print("❌ Invalid choice. Please try again.")
            
        except KeyboardInterrupt:
            print(f"\nImport session ended. Imported {len(imported_files)} file(s).")
            return
        except EOFError:
            print(f"\nImport session ended. Imported {len(imported_files)} file(s).")
            return

def import_data(file_path):
    """Import credit card data from specified file."""
    if not Path(file_path).exists():
        print(f"❌ File not found: {file_path}")
        sys.exit(1)
    
    run_command(f"python manage.py import_cards {file_path}", f"Importing data from {file_path}")

def collect_static():
    """Collect static files."""
    run_command("python manage.py collectstatic --noinput", "Collecting static files")

def shell():
    """Open Django shell."""
    run_command("python manage.py shell", "Opening Django shell")

def flush_database():
    """Flush the database (WARNING: This will delete all data)."""
    response = input("⚠️  This will delete ALL data from the database. Are you sure? (yes/no): ")
    if response.lower() == 'yes':
        run_command("python manage.py flush --noinput", "Flushing database")
    else:
        print("Operation cancelled.")

def wipe_database():
    """Completely wipe and recreate the database (WARNING: This will delete everything)."""
    print("⚠️  This will completely wipe the database and recreate it from scratch.")
    print("   All data, tables, and migrations will be reset.")
    response = input("Are you absolutely sure? (type 'WIPE' to confirm): ")
    
    if response == 'WIPE':
        print("🗑️  Wiping database completely...")
        
        # Remove the database file (SQLite)
        db_file = PROJECT_ROOT / "db.sqlite3"
        if db_file.exists():
            db_file.unlink()
            print(f"✅ Removed database file: {db_file}")
        
        # Remove all migration files (but keep __init__.py and the migration folders)
        apps = ['cards', 'roadmaps', 'users']
        for app in apps:
            migrations_dir = PROJECT_ROOT / app / "migrations"
            if migrations_dir.exists():
                for migration_file in migrations_dir.glob("*.py"):
                    if migration_file.name != "__init__.py":
                        migration_file.unlink()
                        print(f"✅ Removed migration: {migration_file}")
        
        print("✅ Database wiped successfully!")
        print("💡 Next steps: Run 'python admin.py setup-db' to recreate the database")
    else:
        print("Operation cancelled.")

def show_urls():
    """Show all URL patterns."""
    run_command("python manage.py show_urls", "Showing URL patterns")

def check_deployment():
    """Check deployment readiness."""
    run_command("python manage.py check --deploy", "Checking deployment readiness")

def full_setup():
    """Complete project setup from scratch."""
    print("🚀 Starting full project setup...")
    
    # Ask if user wants to wipe the database first
    print("\n🗃️  Database Setup Options:")
    print("1. Keep existing database (just add missing tables)")
    print("2. Completely wipe and recreate database from scratch")
    
    while True:
        choice = input("Choose option (1 or 2): ").strip()
        if choice == '1':
            break
        elif choice == '2':
            print("\n⚠️  This will completely wipe your existing database!")
            confirm = input("Type 'WIPE' to confirm: ").strip()
            if confirm == 'WIPE':
                # Wipe the database without interactive prompts
                print("🗑️  Wiping database completely...")
                
                # Remove the database file (SQLite)
                db_file = PROJECT_ROOT / "db.sqlite3"
                if db_file.exists():
                    db_file.unlink()
                    print(f"✅ Removed database file: {db_file}")
                
                # Remove all migration files (but keep __init__.py and the migration folders)
                apps = ['cards', 'roadmaps', 'users']
                for app in apps:
                    migrations_dir = PROJECT_ROOT / app / "migrations"
                    if migrations_dir.exists():
                        for migration_file in migrations_dir.glob("*.py"):
                            if migration_file.name != "__init__.py":
                                migration_file.unlink()
                                print(f"✅ Removed migration: {migration_file}")
                
                print("✅ Database wiped successfully!")
                break
            else:
                print("❌ Database wipe cancelled. Keeping existing database.")
                break
        else:
            print("❌ Invalid choice. Please enter 1 or 2.")
    
    install_dependencies()
    setup_database()
    setup_google_oauth()
    
    # Import the 4 essential system files automatically
    print("\n📥 Importing essential system data...")
    data_dir = PROJECT_ROOT / "data" / "input" / "system"
    
    if data_dir.exists():
        essential_files = [
            "issuers.json",
            "reward_types.json", 
            "spending_categories.json",
            "spending_credits.json",
            "credit_cards.json"
        ]
        
        for filename in essential_files:
            file_path = data_dir / filename
            if file_path.exists():
                print(f"📄 Importing {filename}")
                
                # Use appropriate import command based on file type
                if filename == "spending_credits.json":
                    run_command(f"python manage.py import_spending_credits", f"Importing {filename}")
                else:
                    run_command(f"python manage.py import_cards {file_path}", f"Importing {filename}")
            else:
                print(f"⚠️  Essential file not found: {filename}")
        
        print("✅ Essential system data imported!")
    else:
        print("⚠️  System data directory not found. Skipping automatic import.")
        print("💡 You can manually import data later with 'python admin.py import-sample'")
    
    print("\n✅ Full setup complete!")
    print("💡 Next steps:")
    print("  - Run 'python admin.py server' to start the development server")
    print("  - Run 'python admin.py import-sample' to import additional card data")
    print("  - Visit http://localhost:8000 to see your application")

def show_interactive_menu():
    """Show interactive menu for task selection."""
    print("\n🎯 Credit Card Guru Admin")
    print("=" * 40)
    
    # Common workflows
    common_workflows = {
        '1': ('Full Project Setup', 'setup', 'Complete setup from scratch'),
        '2': ('Start Development Server', 'server', 'Run server on port 8000'),
        '3': ('Import Sample Data', 'import-sample', 'Import all sample JSON files'),
        '4': ('Run Tests', 'test', 'Execute Django test suite'),
        '5': ('Open Django Shell', 'shell', 'Interactive Python shell'),
        '6': ('Wipe Database', 'wipe-db', 'Completely wipe and recreate database'),
    }
    
    print("\n📋 Common Workflows:")
    for key, (name, _, desc) in common_workflows.items():
        print(f"  {key}. {name} - {desc}")
    
    print("\n⚙️  Other Options:")
    print("  a. List all available commands")
    print("  q. Quit")
    
    while True:
        try:
            choice = input("\nSelect an option: ").strip().lower()
            
            if choice == 'q':
                print("👋 Goodbye!")
                return
            
            if choice == 'a':
                show_all_commands()
                continue
            
            if choice in common_workflows:
                _, task, _ = common_workflows[choice]
                execute_task(task)
                return
            
            print("❌ Invalid choice. Please try again.")
            
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            return
        except EOFError:
            print("\n👋 Goodbye!")
            return

def show_all_commands():
    """Show all available commands."""
    print("\n📚 All Available Commands:")
    print("-" * 40)
    
    commands = {
        'setup': 'Complete project setup from scratch',
        'install': 'Install Python dependencies',
        'setup-db': 'Set up database with migrations',
        'setup-oauth': 'Set up Google OAuth from .env file',
        'createsuperuser': 'Create Django superuser account',
        'server': 'Run development server (default port 8000)',
        'test': 'Run Django test suite',
        'import-sample': 'Import sample credit card data',
        'import <file>': 'Import credit card data from specific file',
        'shell': 'Open Django interactive shell',
        'collectstatic': 'Collect static files for production',
        'flush': 'Flush database (WARNING: deletes all data)',
        'wipe-db': 'Completely wipe and recreate database (WARNING: deletes everything)',
        'urls': 'Show all URL patterns',
        'check': 'Check deployment readiness',
    }
    
    for cmd, desc in commands.items():
        print(f"  python admin.py {cmd:<20} # {desc}")
    
    print(f"\n💡 You can also run: python admin.py <command> directly")

def execute_task(task, args=None):
    """Execute a specific task."""
    task_map = {
        'install': install_dependencies,
        'setup-db': setup_database,
        'setup-oauth': setup_google_oauth,
        'createsuperuser': create_superuser,
        'test': run_tests,
        'server': lambda: run_server(8000),
        'import-sample': import_sample_data,
        'collectstatic': collect_static,
        'shell': shell,
        'flush': flush_database,
        'wipe-db': wipe_database,
        'urls': show_urls,
        'check': check_deployment,
        'setup': full_setup,
    }
    
    if task in task_map:
        task_map[task]()
    else:
        print(f"❌ Unknown task: {task}")

def main():
    """Main entry point."""
    setup_environment()
    
    # If no arguments, show interactive menu
    if len(sys.argv) == 1:
        show_interactive_menu()
        return
    
    # Otherwise, use command line arguments
    parser = argparse.ArgumentParser(description='Credit Card Guru Admin Script')
    subparsers = parser.add_subparsers(dest='task', help='Available tasks')
    
    # Define tasks
    subparsers.add_parser('install', help='Install dependencies')
    subparsers.add_parser('setup-db', help='Set up database with migrations')
    subparsers.add_parser('setup-oauth', help='Set up Google OAuth from .env file')
    subparsers.add_parser('createsuperuser', help='Create Django superuser')
    subparsers.add_parser('test', help='Run tests')
    
    server_parser = subparsers.add_parser('server', help='Run development server')
    server_parser.add_argument('--port', type=int, default=8000, help='Server port (default: 8000)')
    
    subparsers.add_parser('import-sample', help='Import sample credit card data')
    
    import_parser = subparsers.add_parser('import', help='Import credit card data from file')
    import_parser.add_argument('file', help='Path to JSON file')
    
    subparsers.add_parser('collectstatic', help='Collect static files')
    subparsers.add_parser('shell', help='Open Django shell')
    subparsers.add_parser('flush', help='Flush database (WARNING: deletes all data)')
    subparsers.add_parser('wipe-db', help='Completely wipe and recreate database (WARNING: deletes everything)')
    subparsers.add_parser('urls', help='Show URL patterns')
    subparsers.add_parser('check', help='Check deployment readiness')
    subparsers.add_parser('setup', help='Complete project setup')
    
    # Help command
    subparsers.add_parser('help', help='Show this help message')
    
    args = parser.parse_args()
    
    if not args.task or args.task == 'help':
        parser.print_help()
        print("\n💡 Run without arguments for interactive menu")
        print("\nCommon workflows:")
        print("  python admin.py setup              # Full project setup")
        print("  python admin.py server             # Start development server")
        print("  python admin.py test               # Run tests")
        print("  python admin.py import-sample      # Import sample data")
        print("  python admin.py shell              # Open Django shell")
        return
    
    # Execute the requested task
    if args.task == 'server':
        run_server(args.port if hasattr(args, 'port') else 8000)
    elif args.task == 'import':
        import_data(args.file)
    else:
        execute_task(args.task, args)

if __name__ == '__main__':
    main()