#!/usr/bin/env bash
# Exit on error
set -o errexit

echo "Installing project dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo "Collecting static assets..."
python manage.py collectstatic --no-input

echo "Applying database schema migrations..."
python manage.py migrate --no-input

echo "Seeding initial campus categories if database is empty..."
python manage.py seed_data

echo "Build process completed successfully!"
