#!/usr/bin/env bash
# exit on error
set -o errexit

# Install poetry
curl -sSL https://install.python-poetry.org | python3 -

# Install dependencies
poetry install

# Run Django commands
poetry run python manage.py collectstatic --no-input
poetry run python manage.py migrate
