"""Pytest configuration for browser testing with Japanese text support."""

import pytest
import os
import subprocess
import time
from threading import Thread

# Global variable to track server process
server_process = None
server_thread = None


def start_test_server():
    """Start the FastAPI server for testing."""
    global server_process
    import uvicorn
    from app.main import app
    
    # Start server in a separate thread
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="error")


@pytest.fixture(scope="session")
def live_server():
    """Start a live server for browser testing."""
    global server_process, server_thread
    
    # Start server in background thread
    server_thread = Thread(target=start_test_server, daemon=True)
    server_thread.start()
    
    # Wait for server to start
    time.sleep(3)
    
    # Verify server is running
    import httpx
    try:
        response = httpx.get("http://localhost:8000/health", timeout=5)
        assert response.status_code == 200
    except Exception as e:
        pytest.skip(f"Could not start test server: {e}")
    
    yield "http://localhost:8000"
    
    # Cleanup is handled by daemon thread


@pytest.fixture(scope="session")
def browser_context_args():
    """Configure browser context for Japanese text support."""
    return {
        "locale": "ja-JP",
        "timezone_id": "Asia/Tokyo",
        "viewport": {"width": 1280, "height": 720},
        "extra_http_headers": {
            "Accept-Language": "ja,ja-JP;q=0.9,en;q=0.8",
            "Accept-Charset": "UTF-8"
        },
        # Ensure proper font rendering
        "ignore_https_errors": True,
        "color_scheme": "light",
        # Enhanced font configuration for Japanese text
        "font_size": 16,
        "device_scale_factor": 1.0,
        "has_touch": False,
        "is_mobile": False,
    }


@pytest.fixture(scope="session") 
def browser_type_launch_args():
    """Configure browser launch arguments for Japanese text support."""
    return {
        "headless": True,
        "args": [
            "--font-render-hinting=none",
            "--disable-font-subpixel-positioning", 
            "--disable-gpu-sandbox",
            "--no-sandbox",
            "--lang=ja-JP",
            "--accept-lang=ja,ja-JP,en",
            "--disable-features=VizDisplayCompositor",
            "--disable-dev-shm-usage",
            "--force-device-scale-factor=1",
            # Enhanced Japanese text rendering
            "--disable-extensions",
            "--disable-background-timer-throttling",
            "--disable-backgrounding-occluded-windows",
            "--disable-renderer-backgrounding",
            # Font configuration for CJK characters
            "--font-config-file=/etc/fonts/fonts.conf",
            "--enable-font-antialiasing",
            "--disable-lcd-text",
            # Character encoding support
            "--default-encoding=utf-8",
            # Disable hardware acceleration issues
            "--disable-gpu",
            "--disable-software-rasterizer",
        ]
    }


def pytest_configure(config):
    """Configure pytest for browser testing."""
    # Install playwright browsers if not already installed
    try:
        subprocess.run(["playwright", "install", "chromium"], 
                      capture_output=True, check=False)
    except FileNotFoundError:
        pass  # playwright not in PATH, skip auto-install


# Mark all browser tests to require live server
pytestmark = pytest.mark.usefixtures("live_server")