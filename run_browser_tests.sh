#!/bin/bash
# Script to install Playwright and run browser tests

echo "Installing Playwright dependencies..."
pip install playwright pytest-playwright

echo "Installing Playwright browsers..."
playwright install chromium

echo "Installing system dependencies for Japanese font support..."
# For Ubuntu/Debian systems
if command -v apt-get &> /dev/null; then
    sudo apt-get update
    sudo apt-get install -y fonts-noto-cjk fonts-liberation
fi

echo "Running browser tests..."
pytest tests/test_browser.py -v --browser=chromium

echo "Running all tests..."
pytest -v