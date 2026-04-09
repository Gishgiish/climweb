#!/usr/bin/env bash
set -o errexit  # Exit on error

echo "=== Starting Render Build ==="

# Install Python dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Collect static files for production
echo "Collecting static files..."
python /climweb/web/src/climweb/manage.py collectstatic --noinput

# Run database migrations
echo "Running migrations..."
python /climweb/web/src/climweb/manage.py migrate --noinput

echo "=== Build Complete ==="
