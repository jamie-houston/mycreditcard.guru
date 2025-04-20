#!/usr/bin/env python
"""
Script to check SQLAlchemy 2.x compatibility issues in the application.

This tool identifies patterns in your code that need to be updated for SQLAlchemy 2.x.
"""

import os
import re
import sys
from pathlib import Path

GREEN = '\033[92m'
YELLOW = '\033[93m'
RED = '\033[91m'
BLUE = '\033[94m'
END = '\033[0m'
BOLD = '\033[1m'

def print_header(text):
    print(f"{BOLD}{BLUE}=== {text} ==={END}")

def print_success(text):
    print(f"{GREEN}✓ {text}{END}")

def print_warning(text):
    print(f"{YELLOW}⚠ {text}{END}")

def print_error(text):
    print(f"{RED}✗ {text}{END}")

def get_python_files(base_path='.'):
    """Get all Python files in the project, excluding venv directory."""
    all_files = []
    for root, _, files in os.walk(base_path):
        if 'venv' in root.split(os.path.sep):
            continue
        for file in files:
            if file.endswith('.py'):
                all_files.append(os.path.join(root, file))
    return all_files

def check_query_attribute(files):
    """Check for Model.query usage which needs to be updated for SQLAlchemy 2.x."""
    print_header("Checking for Model.query patterns")
    
    pattern = re.compile(r'([A-Z][A-Za-z0-9_]*)\s*\.\s*query\s*\.')
    matches = []
    
    for file_path in files:
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            
            for match in pattern.finditer(content):
                matches.append((file_path, match.group(0), match.group(1)))
        except Exception as e:
            print_error(f"Could not read {file_path}: {e}")
    
    if matches:
        print_warning(f"Found {len(matches)} instances of .query attribute usage")
        print("These should be updated for SQLAlchemy 2.x compatibility:")
        
        for file_path, match_text, model_name in matches:
            print(f"  {os.path.relpath(file_path)}: {match_text}")
            print(f"    Consider using: db.session.query({model_name}).filter(...)")
        
        print(f"\n{YELLOW}Update strategy:{END}")
        print("  Replace: Model.query.filter(...)")
        print("  With:    db.session.query(Model).filter(...)")
    else:
        print_success("No .query attribute usage found.")

def check_session_management(files):
    """Check for proper session management patterns."""
    print_header("Checking session management")
    
    # Look for session.commit without error handling
    commit_pattern = re.compile(r'db\.session\.commit\(\)')
    
    # Look for try/except blocks around session operations
    try_pattern = re.compile(r'try\s*:.*?db\.session\.(add|commit).*?except.*?db\.session\.rollback\(\)', re.DOTALL)
    
    # Look for with statement session management
    with_pattern = re.compile(r'with\s+db\.session\.(begin|no_autoflush)')
    
    for file_path in files:
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            
            commits = commit_pattern.findall(content)
            try_blocks = try_pattern.findall(content)
            with_blocks = with_pattern.findall(content)
            
            if commits and not (try_blocks or with_blocks):
                print_warning(f"{os.path.relpath(file_path)}: Found commit without proper exception handling")
                print("  Consider using:")
                print("  try:")
                print("      db.session.add(object)")
                print("      db.session.commit()")
                print("  except Exception as e:")
                print("      db.session.rollback()")
                print("      raise e")
                print("  Or with SQLAlchemy 2.x:")
                print("  with db.session.begin():")
                print("      db.session.add(object)")
        except Exception as e:
            print_error(f"Could not read {file_path}: {e}")

def check_relationship_declarations(files):
    """Check for relationship declarations that might need updating."""
    print_header("Checking relationship declarations")
    
    backref_pattern = re.compile(r'backref\s*=\s*[\'"]([^\'"]+)[\'"]')
    
    for file_path in files:
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            
            backrefs = backref_pattern.findall(content)
            
            if backrefs:
                print_warning(f"{os.path.relpath(file_path)}: Found {len(backrefs)} backref declarations")
                print("  Consider updating to back_populates for SQLAlchemy 2.x:")
                print("  Instead of:")
                print("    relationship('User', backref='profiles')")
                print("  Use:")
                print("    relationship('User', back_populates='profiles')")
                print("  And add to the User class:")
                print("    profiles = relationship('Profile', back_populates='user')")
        except Exception as e:
            print_error(f"Could not read {file_path}: {e}")

def main():
    print_header("SQLAlchemy 2.x Compatibility Check")
    
    print(f"Current directory: {os.getcwd()}")
    files = get_python_files()
    print(f"Found {len(files)} Python files to check")
    
    check_query_attribute(files)
    print()
    check_session_management(files)
    print()
    check_relationship_declarations(files)
    
    print()
    print(f"{BOLD}Recommendations for PythonAnywhere Deployment:{END}")
    print("1. For Model.query usage, use db.session.query(Model) instead")
    print("2. Ensure proper session management with try/except or with blocks")
    print("3. Use back_populates instead of backref for relationships")
    print("4. Test your application thoroughly after making these changes")
    
if __name__ == "__main__":
    main() 