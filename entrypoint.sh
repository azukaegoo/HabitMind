#!/bin/sh
set -e

echo "Waiting for database..."

until python -c "
import os
import psycopg2
psycopg2.connect(os.environ['DATABASE_URL'])
"; do
  echo "Database not ready yet..."
  sleep 2
done

echo "Database is ready."

echo "Running migrations..."
flask db upgrade

echo "Starting app..."
python run.py
