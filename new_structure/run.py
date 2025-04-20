"""
Run script for starting the Flask development server.
"""

from app import create_app

app = create_app('development')

if __name__ == '__main__':
    app.run(debug=True) 