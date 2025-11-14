#!/usr/bin/env bash
set -euo pipefail

# Install dependencies and collect static assets
pip install -r requirements.txt
python manage.py collectstatic --no-input
