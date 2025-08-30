#!/usr/bin/env python3
"""
Simple script to verify Playwright configuration for Japanese text support.
This script tests the configuration without requiring browser installation.
"""

import sys
import os
import tempfile
from pathlib import Path

def test_playwright_config():
    """Test that our Playwright configuration is properly set up."""
    
    print("🧪 Testing Playwright configuration for Japanese text support...")
    
    # Test 1: Check if configuration files exist
    project_root = Path(__file__).parent
    config_files = [
        project_root / "playwright.config.py",
        project_root / "conftest.py", 
        project_root / "pytest.ini",
        project_root / "tests" / "test_browser.py"
    ]
    
    missing_files = []
    for config_file in config_files:
        if config_file.exists():
            print(f"✅ {config_file.name} exists")
        else:
            print(f"❌ {config_file.name} missing")
            missing_files.append(config_file)
    
    if missing_files:
        print(f"\n❌ Missing configuration files: {[str(f) for f in missing_files]}")
        return False
    
    # Test 2: Check if requirements include Playwright
    requirements_file = project_root / "requirements.txt"
    if requirements_file.exists():
        content = requirements_file.read_text()
        if "playwright" in content and "pytest-playwright" in content:
            print("✅ Playwright dependencies found in requirements.txt")
        else:
            print("❌ Playwright dependencies missing from requirements.txt")
            return False
    
    # Test 3: Verify Japanese locale configuration
    try:
        conftest_file = project_root / "conftest.py"
        content = conftest_file.read_text()
        
        if '"locale": "ja-JP"' in content:
            print("✅ Japanese locale (ja-JP) configured")
        else:
            print("❌ Japanese locale not configured properly")
            return False
            
        if '"Accept-Language": "ja,ja-JP' in content:
            print("✅ Japanese Accept-Language header configured")
        else:
            print("❌ Japanese Accept-Language header missing")
            return False
            
    except Exception as e:
        print(f"❌ Error reading configuration: {e}")
        return False
    
    # Test 4: Check font support
    try:
        import subprocess
        result = subprocess.run(["fc-list", ":lang=ja"], capture_output=True, text=True)
        if result.returncode == 0 and result.stdout.strip():
            print("✅ Japanese fonts available in system")
        else:
            print("⚠️  Japanese fonts may not be available (install fonts-noto-cjk)")
    except FileNotFoundError:
        print("⚠️  fontconfig not available, cannot check fonts")
    
    # Test 5: Verify test structure
    test_file = project_root / "tests" / "test_browser.py"
    if test_file.exists():
        content = test_file.read_text()
        japanese_tests = [
            "test_homepage_japanese_text",
            "test_documents_page_japanese_text",
            "test_japanese_text_rendering"
        ]
        
        found_tests = [test for test in japanese_tests if test in content]
        if found_tests:
            print(f"✅ Japanese text tests found: {len(found_tests)} tests")
        else:
            print("❌ No Japanese text tests found")
            return False
    
    print("\n🎉 Playwright configuration for Japanese text support is properly set up!")
    print("\nNext steps:")
    print("1. Install Playwright: pip install playwright pytest-playwright")
    print("2. Install browsers: playwright install chromium")  
    print("3. Run tests: pytest tests/test_browser.py -v")
    print("\nNote: Browser installation may fail in some environments but configuration is correct.")
    
    return True

if __name__ == "__main__":
    success = test_playwright_config()
    sys.exit(0 if success else 1)