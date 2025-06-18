#!/usr/bin/env python3
"""
Flask Script Runner

This script allows you to run Flask app scripts from the project root directory.
It handles the Python path and directory changes automatically.

Usage:
    python scripts/run_flask_script.py [script_number]
    python scripts/run_flask_script.py <category/script_name> [args...]

Examples:
    python scripts/run_flask_script.py                    # Show menu
    python scripts/run_flask_script.py 1                  # Run script #1
    python scripts/run_flask_script.py data/seed_db.py    # Run specific script
"""

import sys
import os
import subprocess
from pathlib import Path
import re


# Script descriptions and categories
SCRIPT_INFO = {
    # Root level scripts
    "run.py": "Start the Flask development server with configurable options",
    "run_tests.py": "Run all tests with coverage reporting and detailed output",
    "guided_scraping.py": "Step-by-step guided workflow for scraping and importing credit card data",
    
    # Admin scripts
    "admin/generate_recommendation.py": "Generate credit card recommendations for a specific user profile",
    
    # Data scripts
    "data/fix_card_rewards.py": "Fix existing cards that have JSON reward data but missing relationship records",
    "data/import_cards.py": "Import credit cards from NerdWallet or JSON file with reward category mapping",
    "data/init_db.py": "Initialize database tables based on current SQLAlchemy models",
    "data/manage_cards.py": "Interactive tool to manage credit cards in the database",
    "data/reset_db.py": "Reset and initialize the database, bypassing migrations",
    "data/seed_categories.py": "Seed database with default categories for credit card rewards",
    "data/seed_db.py": "Seed database with sample credit cards for development and testing",
    "data/seed_credit_cards.py": "Import credit cards from scraped data files or seed sample cards",
    "data/update_cards.py": "Update existing credit cards with new data from scraping",
    "data/update_db.py": "Update database schema and migrate data",
    
    # Scraping scripts
    "scraping/scrape_nerdwallet.py": "Scrape credit card data from NerdWallet HTML files with timestamped output",
    "scraping/scrape_nerdwallet_table_detailed.py": "Detailed NerdWallet table scraper with reward category parsing",
    
    # Test scripts
    "test/create_test_data.py": "Create comprehensive test data including users, profiles, and recommendations",
    "test/create_test_profile.py": "Create a test user profile with realistic spending patterns",
    "test/create_test_user.py": "Create a test user account for development purposes",
}


def extract_description_from_file(script_path):
    """Extract description from script's docstring."""
    try:
        with open(script_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Look for docstring patterns
        patterns = [
            r'"""([^"]+?)"""',  # Triple quotes
            r"'''([^']+?)'''",  # Triple single quotes
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content, re.DOTALL)
            if match:
                docstring = match.group(1).strip()
                # Get the first meaningful line (skip title lines)
                lines = [line.strip() for line in docstring.split('\n') if line.strip()]
                if len(lines) > 1:
                    # Skip the title, get the description
                    for line in lines[1:]:
                        if line and not line.startswith('This script'):
                            return line
                        elif line.startswith('This script'):
                            return line
                elif lines:
                    return lines[0]
                    
    except Exception:
        pass
    
    return "No description available"


def get_available_scripts():
    """Get all available Flask scripts organized by category."""
    flask_app_dir = Path("flask_app")
    flask_scripts_dir = Path("flask_app/scripts")
    
    if not flask_app_dir.exists():
        return {}
    
    scripts_by_category = {}
    
    # Define allowed root scripts
    allowed_root_scripts = [
        "run.py",
        "run_tests.py", 
        "guided_scraping.py",
        "seed_db.py"
    ]
    
    # Add scripts from scripts/data directory
    allowed_scripts_data = [
        "scripts/data/reset_db.py"
    ]
    
    # First, scan for root-level scripts in flask_app directory
    root_scripts = []
    for script_name in allowed_root_scripts:
        script_path = flask_app_dir / script_name
        if script_path.exists():
            # Get description from SCRIPT_INFO or extract from file
            description = SCRIPT_INFO.get(script_name)
            if not description:
                description = extract_description_from_file(script_path)
            
            root_scripts.append({
                'name': script_name,
                'path': script_name,
                'full_path': script_path,
                'description': description
            })
    
    # Add selected scripts from scripts/data directory
    for script_path_str in allowed_scripts_data:
        script_path = flask_app_dir / script_path_str
        if script_path.exists():
            script_name = script_path.name
            # Use just the filename for display but keep the relative path
            description = SCRIPT_INFO.get(f"data/{script_name}")
            if not description:
                description = extract_description_from_file(script_path)
            
            root_scripts.append({
                'name': script_name,
                'path': script_path_str,
                'full_path': script_path,
                'description': description
            })
    
    if root_scripts:
        scripts_by_category['root'] = sorted(root_scripts, key=lambda x: x['name'])
    
    return scripts_by_category


def show_menu(show_all=False):
    """Display the script menu with numbered options."""
    scripts_by_category = get_available_scripts()
    
    if not scripts_by_category:
        print("No scripts found in flask_app/")
        return None
    
    print("🚀 Flask Script Runner")
    print("=" * 80)
    
    script_list = []
    counter = 1
    
    # Show available scripts
    if 'root' in scripts_by_category:
        scripts = scripts_by_category['root']
        print(f"\n📁 AVAILABLE SCRIPTS")
        print("-" * 40)
        
        for script in scripts:
            print(f"{counter:2d}. {script['name']}")
            print(f"    {script['description']}")
            script_list.append(script)
            counter += 1
    
    print(f"\n{'=' * 80}")
    print("Usage:")
    print("  Enter a number (1-{}) to run that script".format(len(script_list)))
    print("  Or use: python scripts/run_flask_script.py <script_name> [args...]")
    print("  Press Ctrl+C to exit")
    
    return script_list


def get_user_choice(script_list):
    """Get user's script choice."""
    try:
        prompt = f"\nSelect script (1-{len(script_list)}): "
        choice = input(prompt).strip()
        
        if choice.isdigit():
            choice_num = int(choice)
            if 1 <= choice_num <= len(script_list):
                return script_list[choice_num - 1]
            else:
                print(f"❌ Invalid choice. Please enter a number between 1 and {len(script_list)}")
                return None
        elif not choice:
            # Empty input means exit
            return None
        else:
            print("❌ Please enter a valid number")
            return None
            
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
        return None
    except EOFError:
        return None


def run_script(script_info, args=None):
    """Run the selected script."""
    if args is None:
        args = []
        
    script_path = script_info['path']
    script_name = script_info['name']
    
    # Get the project root directory
    project_root = Path(__file__).parent.parent
    flask_app_dir = project_root / "flask_app"
    
    # Change to flask_app directory and run the script with proper PYTHONPATH
    print(f"\n🚀 Running Flask script: {script_path}")
    print(f"📝 Description: {script_info['description']}")
    print(f"📁 Working directory: {flask_app_dir}")
    
    if args:
        print(f"⚙️  Arguments: {' '.join(args)}")
    
    try:
        # Build the command - handle root scripts vs scripts in subdirectories
        if script_path.startswith('scripts/'):
            # Script in subdirectory (already has scripts/ prefix)
            cmd = [sys.executable, script_path] + args
        else:
            # Root-level script
            cmd = [sys.executable, script_path] + args
        
        # Set up environment
        env = os.environ.copy()
        env['PYTHONPATH'] = str(flask_app_dir)
        
        # Run the script
        result = subprocess.run(
            cmd,
            cwd=flask_app_dir,
            env=env,
            check=True
        )
        
        print(f"\n✅ Script completed successfully!")
        
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Script failed with exit code: {e.returncode}")
        sys.exit(e.returncode)
    except KeyboardInterrupt:
        print(f"\n⚠️  Script interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        sys.exit(1)


def main():
    """Main function."""
    if len(sys.argv) == 1:
        # Interactive mode
        script_list = show_menu()
        if not script_list:
            sys.exit(1)
            
        while True:
            choice = get_user_choice(script_list)
            
            if choice is None:
                sys.exit(0)
            
            # Run the selected script
            run_script(choice)
            
            # After running a script, ask for next action
            print(f"\n{'='*60}")
            print("🔄 What would you like to do next?")
            print("   • Enter a script number (1-{}) to run another script".format(len(script_list)))
            print("   • Press Enter to exit")
            print("   • Type 'menu' to show the menu again")
            
            try:
                next_action = input(f"\nNext action: ").strip()
                
                if not next_action:
                    # Empty input - exit
                    print("👋 Goodbye!")
                    break
                elif next_action.lower() == 'menu':
                    # Show menu again
                    script_list = show_menu()
                    if not script_list:
                        sys.exit(1)
                    continue
                elif next_action.isdigit():
                    # Direct script number selection
                    choice_num = int(next_action)
                    if 1 <= choice_num <= len(script_list):
                        run_script(script_list[choice_num - 1])
                        continue
                    else:
                        print(f"❌ Invalid script number. Please choose between 1 and {len(script_list)}")
                        continue
                else:
                    # Invalid input - exit
                    print("👋 Goodbye!")
                    break
                    
            except (KeyboardInterrupt, EOFError):
                print("\n👋 Goodbye!")
                break
    
    elif len(sys.argv) >= 2:
        # Direct script execution
        script_arg = sys.argv[1]
        script_args = sys.argv[2:]
        
        # Check if it's a number (menu selection)
        if script_arg.isdigit():
            script_list = show_menu()
            if not script_list:
                sys.exit(1)
                
            choice_num = int(script_arg)
            if 1 <= choice_num <= len(script_list):
                run_script(script_list[choice_num - 1], script_args)
            else:
                print(f"❌ Invalid script number. Please choose between 1 and {len(script_list)}")
                sys.exit(1)
        else:
            # Direct script path
            script_name = script_arg
            
            # Ensure script name ends with .py
            if not script_name.endswith('.py'):
                script_name += '.py'
            
            # Check if script exists (try root first, then scripts subdirectories)
            script_path = Path(f"flask_app/{script_name}")
            if not script_path.exists():
                script_path = Path(f"flask_app/scripts/{script_name}")
                if not script_path.exists():
                    print(f"❌ Script '{script_name}' not found in flask_app/ or flask_app/scripts/")
                    
                    # Show available scripts
                    print("\nAvailable scripts:")
                    show_menu()
                    sys.exit(1)
            
            # Create script info
            script_info = {
                'name': script_path.name,
                'path': script_name,
                'description': SCRIPT_INFO.get(script_name, extract_description_from_file(script_path))
            }
            
            run_script(script_info, script_args)


if __name__ == "__main__":
    main() 