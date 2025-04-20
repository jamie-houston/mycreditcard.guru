#!/bin/bash

# Initialize the database first to ensure it exists
echo "Initializing database..."
python init_db.py

# Start the Flask application
echo "Starting server..."
python test_server.py 