#!/bin/bash
# Script to install Playwright and run browser tests with Japanese font support

echo "Setting up Japanese fonts for screenshot testing..."
python setup_fonts.py

echo "Installing Playwright dependencies..."
pip install playwright pytest-playwright

echo "Installing Playwright browsers..."
playwright install chromium

echo "Running browser tests..."
pytest tests/test_browser.py -v --browser=chromium

echo "Running all tests..."
pytest -v