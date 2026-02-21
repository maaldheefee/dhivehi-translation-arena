#!/bin/sh
set -e

# Run database initialization
echo "Initializing database..."
python init_db.py

# Execute the CMD passed to the docker container
exec "$@"
