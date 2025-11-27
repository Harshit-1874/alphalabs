#!/bin/bash
# Run database migrations
# Usage: ./run_migrations.sh

cd "$(dirname "$0")"
python migrate.py


