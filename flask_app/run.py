#!/usr/bin/env python3
"""
Flask Application Runner

This script starts the Flask development server with proper configuration.
Can be run directly or through the script runner system.

Usage:
    python run.py [--port PORT] [--host HOST] [--debug] [--no-debug]

Examples:
    python run.py                    # Run with default settings
    python run.py --port 5001        # Run on port 5001
    python run.py --host 0.0.0.0     # Run accessible from all interfaces
    python run.py --debug            # Force debug mode on
    python run.py --no-debug         # Force debug mode off
"""

import os
import sys
import argparse
from app import create_app

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Run the Flask development server')
    parser.add_argument('--port', '-p', type=int, default=5001, 
                       help='Port to run the server on (default: 5001)')
    parser.add_argument('--host', default='127.0.0.1',
                       help='Host to bind to (default: 127.0.0.1)')
    parser.add_argument('--debug', action='store_true',
                       help='Force debug mode on')
    parser.add_argument('--no-debug', action='store_true',
                       help='Force debug mode off')
    parser.add_argument('--config', '-c', default='development',
                       choices=['development', 'testing', 'production'],
                       help='Configuration to use (default: development)')
    
    return parser.parse_args()

def main():
    """Main function to run the Flask app."""
    args = parse_args()
    
    # Determine debug mode
    debug = None
    if args.debug:
        debug = True
    elif args.no_debug:
        debug = False
    else:
        # Use environment variable or default based on config
        debug = os.environ.get('FLASK_DEBUG', '1' if args.config == 'development' else '0') == '1'
    
    # Create the Flask app
    app = create_app(args.config)
    
    # Print startup information
    print("🚀 Credit Card Roadmap Flask Server")
    print("=" * 50)
    print(f"📁 Configuration: {args.config}")
    print(f"🌐 Host: {args.host}")
    print(f"🔌 Port: {args.port}")
    print(f"🐛 Debug: {'ON' if debug else 'OFF'}")
    print(f"🔗 URL: http://{args.host}:{args.port}")
    print("=" * 50)
    print("Press Ctrl+C to stop the server")
    print()
    
    try:
        # Run the Flask development server
        app.run(
            host=args.host,
            port=args.port,
            debug=debug,
            use_reloader=debug,  # Only use reloader in debug mode
            threaded=True
        )
    except KeyboardInterrupt:
        print("\n👋 Server stopped by user")
    except Exception as e:
        print(f"\n💥 Server error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main() 