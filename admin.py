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
    env_file = PROJECT_ROOT / 'django.env'
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                if line.strip() and not line.startswith('#'):
                    key, value = line.strip().split('=', 1)
                    os.environ.setdefault(key, value)

def install_dependencies():
    """Install Python dependencies."""
    run_command("pip install -r requirements.txt", "Installing dependencies")

def setup_database():
    """Set up the database with migrations."""
    run_command("python manage.py makemigrations", "Creating migrations")
    run_command("python manage.py migrate", "Running migrations")

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
    """Import sample credit card data."""
    sample_file = PROJECT_ROOT / "sample_cards.json"
    if sample_file.exists():
        run_command(f"python manage.py import_cards {sample_file}", "Importing sample data")
    else:
        print("❌ sample_cards.json not found")

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

def show_urls():
    """Show all URL patterns."""
    run_command("python manage.py show_urls", "Showing URL patterns")

def check_deployment():
    """Check deployment readiness."""
    run_command("python manage.py check --deploy", "Checking deployment readiness")

def full_setup():
    """Complete project setup from scratch."""
    print("🚀 Starting full project setup...")
    install_dependencies()
    setup_database()
    import_sample_data()
    print("✅ Full setup complete!")

def main():
    """Main entry point."""
    setup_environment()
    
    parser = argparse.ArgumentParser(description='Credit Card Guru Admin Script')
    subparsers = parser.add_subparsers(dest='task', help='Available tasks')
    
    # Define tasks
    subparsers.add_parser('install', help='Install dependencies')
    subparsers.add_parser('setup-db', help='Set up database with migrations')
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
    subparsers.add_parser('urls', help='Show URL patterns')
    subparsers.add_parser('check', help='Check deployment readiness')
    subparsers.add_parser('setup', help='Complete project setup')
    
    # Help command
    subparsers.add_parser('help', help='Show this help message')
    
    args = parser.parse_args()
    
    if not args.task or args.task == 'help':
        parser.print_help()
        print("\nCommon workflows:")
        print("  python admin.py setup              # Full project setup")
        print("  python admin.py server             # Start development server")
        print("  python admin.py test               # Run tests")
        print("  python admin.py import-sample      # Import sample data")
        print("  python admin.py shell              # Open Django shell")
        return
    
    # Execute the requested task
    task_map = {
        'install': install_dependencies,
        'setup-db': setup_database,
        'createsuperuser': create_superuser,
        'test': run_tests,
        'server': lambda: run_server(args.port if hasattr(args, 'port') else 8000),
        'import-sample': import_sample_data,
        'import': lambda: import_data(args.file),
        'collectstatic': collect_static,
        'shell': shell,
        'flush': flush_database,
        'urls': show_urls,
        'check': check_deployment,
        'setup': full_setup,
    }
    
    if args.task in task_map:
        task_map[args.task]()
    else:
        print(f"❌ Unknown task: {args.task}")
        parser.print_help()

if __name__ == '__main__':
    main()