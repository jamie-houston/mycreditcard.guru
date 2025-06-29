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
    """Interactive import of data files from data/input directory."""
    data_dir = PROJECT_ROOT / "data" / "input"
    
    # Check if data directory exists
    if not data_dir.exists():
        print("❌ data/input directory not found")
        return
    
    # Get all JSON files in the directory
    json_files = list(data_dir.glob("*.json"))
    
    if not json_files:
        print("❌ No JSON files found in data/input directory")
        return
    
    print("\n📁 Available files in data/input:")
    print("=" * 40)
    
    # Show options
    options = {}
    for i, file_path in enumerate(json_files, 1):
        filename = file_path.name
        print(f"  {i}. {filename}")
        options[str(i)] = file_path
    
    print("  a. Import all files")
    print("  q. Cancel")
    
    while True:
        try:
            choice = input("\nSelect file(s) to import: ").strip().lower()
            
            if choice == 'q':
                print("Import cancelled")
                return
            
            if choice == 'a':
                # Import all files in a logical order
                preferred_order = [
                    "issuers.json",
                    "reward_types.json", 
                    "spending_categories.json",
                    "credit_cards.json",
                    "chase.json"
                ]
                
                # First import files in preferred order
                imported_files = set()
                for preferred_file in preferred_order:
                    for file_path in json_files:
                        if file_path.name == preferred_file and file_path not in imported_files:
                            print(f"\n📄 Importing {file_path.name}")
                            run_command(f"python manage.py import_cards {file_path}", f"Importing {file_path.name}")
                            imported_files.add(file_path)
                
                # Then import any remaining files
                for file_path in json_files:
                    if file_path not in imported_files:
                        print(f"\n📄 Importing {file_path.name}")
                        run_command(f"python manage.py import_cards {file_path}", f"Importing {file_path.name}")
                
                print("\n✅ All files imported!")
                return
            
            if choice in options:
                file_path = options[choice]
                print(f"\n📄 Importing {file_path.name}")
                run_command(f"python manage.py import_cards {file_path}", f"Importing {file_path.name}")
                return
            
            print("❌ Invalid choice. Please try again.")
            
        except KeyboardInterrupt:
            print("\nImport cancelled")
            return
        except EOFError:
            print("\nImport cancelled")
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
        'createsuperuser': 'Create Django superuser account',
        'server': 'Run development server (default port 8000)',
        'test': 'Run Django test suite',
        'import-sample': 'Import sample credit card data',
        'import <file>': 'Import credit card data from specific file',
        'shell': 'Open Django interactive shell',
        'collectstatic': 'Collect static files for production',
        'flush': 'Flush database (WARNING: deletes all data)',
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
        'createsuperuser': create_superuser,
        'test': run_tests,
        'server': lambda: run_server(8000),
        'import-sample': import_sample_data,
        'collectstatic': collect_static,
        'shell': shell,
        'flush': flush_database,
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