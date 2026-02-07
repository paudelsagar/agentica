#!/bin/bash
set -e

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# Run pytest with coverage
echo "Running tests with coverage report..."
python3 -m pytest --cov=src --cov-report=term-missing tests/
