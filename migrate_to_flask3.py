#!/usr/bin/env python
"""
Migration script to help transition from Flask 2.x to Flask 3.x
and SQLAlchemy 1.4 to 2.0 for PythonAnywhere deployment.

This script:
1. Updates requirements.txt with Flask 3.x compatible versions
2. Provides guidance on code changes needed
3. Performs basic compatibility checks
"""

import os
import sys
import re
import subprocess
from pathlib import Path

# Define color codes for terminal output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def print_heading(text):
    print(f"\n{Colors.HEADER}{Colors.BOLD}{text}{Colors.ENDC}")

def print_success(text):
    print(f"{Colors.GREEN}✓ {text}{Colors.ENDC}")

def print_warning(text):
    print(f"{Colors.WARNING}⚠ {text}{Colors.ENDC}")

def print_error(text):
    print(f"{Colors.FAIL}✗ {text}{Colors.ENDC}")

def print_info(text):
    print(f"{Colors.BLUE}ℹ {text}{Colors.ENDC}")

def update_requirements():
    """Update requirements.txt with Flask 3.x compatible versions"""
    print_heading("Updating requirements.txt")
    
    # Define the new dependencies
    new_requirements = {
        "Flask": "3.0.0",
        "Flask-SQLAlchemy": "3.1.1",
        "SQLAlchemy": "2.0.23",
        "Werkzeug": "3.0.1"
    }
    
    # Read current requirements.txt
    try:
        with open("requirements.txt", "r") as f:
            lines = f.readlines()
        
        # Update the dependencies
        new_lines = []
        updated = set()
        
        for line in lines:
            package = line.split('==')[0].strip() if '==' in line else ""
            if package in new_requirements:
                new_line = f"{package}=={new_requirements[package]}\n"
                new_lines.append(new_line)
                updated.add(package)
                print_success(f"Updated {package} to version {new_requirements[package]}")
            else:
                new_lines.append(line)
        
        # Add any missing dependencies
        for package, version in new_requirements.items():
            if package not in updated:
                new_lines.append(f"{package}=={version}\n")
                print_success(f"Added {package} version {version}")
        
        # Write the updated requirements back to the file
        with open("requirements.txt", "w") as f:
            f.writelines(new_lines)
        
        print_success("requirements.txt updated successfully")
    except Exception as e:
        print_error(f"Failed to update requirements.txt: {str(e)}")

def check_sqlalchemy_usage():
    """Check for SQLAlchemy usage that might need updates"""
    print_heading("Checking SQLAlchemy Usage")
    
    # Patterns to look for
    patterns = {
        "session": r"db\.session\.(add|delete|commit|rollback|merge|flush)",
        "query_syntax": r"\.query\.",
        "filter_by": r"\.filter_by\(",
        "session_mgmt": r"(try|with).*db\.session.*"
    }
    
    # Files to check (all Python files)
    python_files = list(Path(".").glob("**/*.py"))
    
    for pattern_name, pattern in patterns.items():
        print_info(f"Checking for {pattern_name} usage...")
        
        found = False
        for file_path in python_files:
            with open(file_path, "r") as f:
                try:
                    contents = f.read()
                    if re.search(pattern, contents):
                        if not found:
                            found = True
                            print_warning(f"{pattern_name} usage found in:")
                        print(f"  - {file_path}")
                except:
                    pass  # Skip files that can't be read
        
        if not found:
            print_success(f"No {pattern_name} issues found")

def print_migration_guide():
    """Print a guide for migrating to Flask 3.x and SQLAlchemy 2.x"""
    print_heading("Migration Guide for PythonAnywhere Deployment")
    
    print_info("When migrating to PythonAnywhere with Flask 3.x, follow these steps:")
    
    print(f"{Colors.BOLD}1. SQLAlchemy 2.x Changes:{Colors.ENDC}")
    print("   - Update query syntax: Replace Model.query with db.session.query(Model)")
    print("   - Use context managers for sessions when possible:")
    print("     ```python")
    print("     with db.session.begin():  # Auto-commits or rollbacks on exception")
    print("         db.session.add(object)")
    print("     ```")
    print("   - Or ensure sessions are properly scoped and closed:")
    print("     ```python")
    print("     try:")
    print("         db.session.add(object)")
    print("         db.session.commit()")
    print("     except Exception as e:")
    print("         db.session.rollback()")
    print("         raise e")
    print("     ```")
    print("   - Relationship declarations might need 'backref' changed to 'back_populates'")
    
    print(f"\n{Colors.BOLD}2. Blueprint Registration Changes:{Colors.ENDC}")
    print("   - Make sure all blueprints are properly registered with correct url_prefix values")
    print("   - Check for any deprecated view function arguments")
    
    print(f"\n{Colors.BOLD}3. Template Changes:{Colors.ENDC}")
    print("   - Check for any deprecated Jinja2 syntax or functions")
    
    print(f"\n{Colors.BOLD}4. PythonAnywhere Setup:{Colors.ENDC}")
    print("   - Create a virtual environment with Python 3.9+ (compatible with Flask 3.x)")
    print("   - Install dependencies from the updated requirements.txt")
    print("   - Configure the WSGI file correctly:")
    print("     ```python")
    print("     from creditcard_roadmap import app as application")
    print("     ```")
    print("   - Set up any environment variables needed in the PythonAnywhere dashboard")

def main():
    print_heading("Flask 3.x Migration Tool for PythonAnywhere")
    
    # Update requirements.txt
    update_requirements()
    
    # Check for SQLAlchemy usage patterns
    check_sqlalchemy_usage()
    
    # Print migration guide
    print_migration_guide()
    
    print_heading("Next Steps")
    print("1. Commit these changes to your version control system")
    print("2. Test your application locally with the updated dependencies")
    print("3. Deploy to PythonAnywhere following the migration guide")
    print("4. Test thoroughly after deployment")

if __name__ == "__main__":
    main() 