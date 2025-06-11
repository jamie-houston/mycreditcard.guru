#!/usr/bin/env python
"""
OAuth Configuration Diagnostic Tool

This script checks your OAuth configuration to help diagnose issues with Google authentication.
"""

import os
import sys
import requests
import json
from dotenv import load_dotenv

# Add the project root to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Load environment variables
load_dotenv()

def print_header(text):
    """Print a formatted header"""
    print("\n" + "=" * 80)
    print(f" {text} ".center(80, '='))
    print("=" * 80)

def check_env_vars():
    """Check if required environment variables are set"""
    print_header("Environment Variables")
    
    required_vars = [
        'GOOGLE_OAUTH_CLIENT_ID',
        'GOOGLE_OAUTH_CLIENT_SECRET',
        'SECRET_KEY',
        'FLASK_ENV',
        'OAUTHLIB_RELAX_TOKEN_SCOPE',
    ]
    
    optional_vars = [
        'PYTHONANYWHERE_DOMAIN',
        'OAUTHLIB_INSECURE_TRANSPORT',
    ]
    
    for var in required_vars:
        value = os.environ.get(var)
        if value:
            # Mask secrets partially
            if 'SECRET' in var or 'KEY' in var:
                display_value = value[:5] + '...' + value[-5:] if len(value) > 10 else '***'
            else:
                display_value = value
            print(f"✅ {var}: {display_value}")
        else:
            print(f"❌ {var}: Not set (Required)")
    
    print("\nOptional Variables:")
    for var in optional_vars:
        value = os.environ.get(var)
        if value:
            print(f"✅ {var}: {value}")
        else:
            print(f"ℹ️ {var}: Not set")

def check_domain():
    """Check domain configuration"""
    print_header("Domain Configuration")
    
    domain = os.environ.get('PYTHONANYWHERE_DOMAIN')
    if domain:
        print(f"Domain: {domain}")
        
        # Check if domain is accessible
        try:
            response = requests.get(f"https://{domain}", timeout=5)
            if response.status_code < 400:
                print(f"✅ Domain is accessible (Status code: {response.status_code})")
            else:
                print(f"❌ Domain returned error (Status code: {response.status_code})")
        except requests.exceptions.RequestException as e:
            print(f"❌ Domain not accessible: {str(e)}")
            
        # Verify redirect URI format
        redirect_uri = f"https://{domain}/login/google/authorized"
        print(f"Redirect URI: {redirect_uri}")
        
        # Generate authentication URL
        client_id = os.environ.get('GOOGLE_OAUTH_CLIENT_ID')
        if client_id:
            auth_url = (
                f"https://accounts.google.com/o/oauth2/auth"
                f"?client_id={client_id}"
                f"&redirect_uri={redirect_uri}"
                f"&scope=profile email"
                f"&response_type=code"
            )
            print(f"\nAuthentication URL (for testing):\n{auth_url}")
    else:
        print("❌ PYTHONANYWHERE_DOMAIN environment variable not set")

def check_google_creds():
    """Check Google OAuth credentials"""
    print_header("Google OAuth Credentials")
    
    client_id = os.environ.get('GOOGLE_OAUTH_CLIENT_ID')
    client_secret = os.environ.get('GOOGLE_OAUTH_CLIENT_SECRET')
    
    if not client_id or not client_secret:
        print("❌ Google OAuth credentials not fully set")
        return
    
    # Check client_id format
    if client_id.endswith('.apps.googleusercontent.com'):
        print("✅ Client ID has correct format")
    else:
        print("❌ Client ID does not have the expected format (should end with .apps.googleusercontent.com)")
    
    # Client secret is usually a mix of upper/lowercase letters and numbers
    if len(client_secret) > 20:
        print("✅ Client secret has sufficient length")
    else:
        print("❌ Client secret seems too short")
    
    print("\nVerify these credentials are set up correctly in Google Cloud Console:")
    print("https://console.cloud.google.com/apis/credentials")

def main():
    """Main function"""
    print_header("OAuth Configuration Diagnostic Tool")
    
    check_env_vars()
    check_domain()
    check_google_creds()
    
    print_header("Recommendations")
    print("""
1. Make sure your Google OAuth consent screen is configured
2. Ensure your OAuth credentials have the correct redirect URI:
   - It should be exactly: https://yourdomain.com/login/google/authorized
   - No trailing slash, no typos
3. Set PYTHONANYWHERE_DOMAIN to your custom domain
4. Update your .env file with all required variables
5. Check the PythonAnywhere web app logs for detailed errors
""")

if __name__ == '__main__':
    main() 