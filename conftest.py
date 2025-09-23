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
    # Ensure the thread picks up the test DB env var and updates the
    # settings object before importing the app module.
    import os as _os
    db_url = _os.environ.get("DB_URL")
    if db_url:
        try:
            from app.core.config import settings as _settings
            _settings.db_url = db_url
        except Exception:
            pass

    import uvicorn
    # Import the app after ensuring env/settings are set so module-level
    # database initialization uses the test DB.
    from app.main import app

    # Start server in a separate thread using the in-process app object
    # so it shares module state with the test process.
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="error")


@pytest.fixture(scope="session")
def live_server(test_database_override):
    """Start a live server for browser testing."""
    global server_process, server_thread
    # Start uvicorn as a subprocess with the test DB env so the server
    # process uses the same database file created by the fixture.
    import sys as _sys
    import httpx as _httpx

    uvicorn_cmd = [_sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000", "--log-level", "error"]

    env = os.environ.copy()
    # Ensure DB_URL set by test_database_override is passed through
    if isinstance(test_database_override, str):
        env["DB_URL"] = test_database_override

    server_process = subprocess.Popen(uvicorn_cmd, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # Wait for server to start
    for _ in range(30):
        try:
            response = _httpx.get("http://localhost:8000/health", timeout=1)
            if response.status_code == 200:
                break
        except Exception:
            time.sleep(0.2)
    else:
        # Could not start server
        if server_process:
            server_process.terminate()
        pytest.skip("Could not start test server")

    yield "http://localhost:8000"

    # Teardown: terminate server process
    try:
        if server_process and server_process.poll() is None:
            server_process.terminate()
            server_process.wait(timeout=5)
    except Exception:
        pass


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

    # Ensure a predictable test DB is used for collection/import-time.
    # Some test modules import the app at module scope during collection;
    # set the DB env var and create tables now so imports see the test DB.
    try:
        import os
        # Use a fixed test DB path in project root so tests and the app
        # reference the same file during collection. Force-set the env var
        # so that modules imported after this point pick up the test DB.
        test_db_path = os.path.abspath("./test.db")
        test_db_url = f"sqlite:///{test_db_path}"
        # Export immediately so other modules imported during collection
        # see the test DB URL.
        os.environ["DB_URL"] = test_db_url
        os.environ["DB_URL"] = test_db_url

        # Create the file and tables if not present
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from app.core.database import Base

        engine = create_engine(test_db_url, connect_args={"check_same_thread": False})
        Base.metadata.create_all(bind=engine)

        # If app.core.database was already imported earlier, rebind its
        # engine and SessionLocal so the app uses the same test DB.
        try:
            from app.core import database as app_db
            # Rebind the app module's engine and SessionLocal to point
            # at the test database created during collection.
            app_db.engine = engine
            app_db.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
            # Re-import app_db.get_db to ensure its closure captures the new engine
            try:
                # Ensure any schema-altering helpers run (adds missing columns)
                try:
                    app_db.create_tables()
                except Exception:
                    pass
            except Exception:
                pass
        except Exception:
            # best-effort; continue even if we can't rebind
            pass
    except Exception:
        # Best-effort only; tests will still run and surface errors if this fails.
        pass


@pytest.fixture(scope="session", autouse=True)
def test_database_override(tmp_path_factory):
    """Create a temporary SQLite DB for the test session and override app's DB dependency.

    This ensures the FastAPI app uses a test database file for all tests and that
    tables are created before tests exercise the app.
    """
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.core.database import Base, get_db, SessionLocal
    # Build test DB path
    db_file = tmp_path_factory.mktemp("data") / "tests.sqlite"
    db_url = f"sqlite:///{db_file}"

    engine = create_engine(db_url, connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    # Export the test DB URL so any subsequent imports that read the
    # environment (including app imports in the live server thread)
    # pick up the correct temporary database file.
    try:
        import os as _os
        _os.environ["DB_URL"] = db_url
        # Also try to update the runtime settings object if present so
        # code that read settings earlier can be guided to the test DB.
        try:
            from app.core.config import settings as _settings
            _settings.db_url = db_url
        except Exception:
            pass
    except Exception:
        pass

    # Ensure app.core.database.SessionLocal uses this engine for tests that
    # import the app after this fixture runs.
    try:
        from app.core import database as app_db
        # Replace the app's SessionLocal so the app uses the test engine
        # sessionmaker objects don't implement `configure`, so assign instead.
        app_db.SessionLocal = TestingSessionLocal
        # Ensure the module-level engine used by the app is the test engine
        # so that any code referencing `app.core.database.engine` uses the
        # same database as the tests.
        try:
            app_db.engine = engine
            # Reload module and ensure create_tables ran to add any missing cols
            try:
                try:
                    app_db.create_tables()
                except Exception:
                    pass
            except Exception:
                pass
        except Exception:
            # best-effort; continue even if we can't rebind engine
            pass
    except Exception:
        pass

    # Create tables
    Base.metadata.create_all(bind=engine)

    # Provide an override for tests that prefer per-test injection
    def _override_get_db():
        try:
            db = TestingSessionLocal()
            yield db
        finally:
            db.close()
    # Apply a global dependency override so the FastAPI app uses the
    # session-scoped test DB for all tests that depend on `get_db`.
    try:
        # Import the app and set dependency override for get_db
        from app.main import app as fastapi_app
        # Only apply if the test module hasn't already set its own override.
        if get_db not in getattr(fastapi_app, "dependency_overrides", {}):
            fastapi_app.dependency_overrides[get_db] = _override_get_db
    except Exception:
        # If the app isn't importable at fixture setup, skip global override.
        pass
    yield db_url

    # Teardown: remove DB file if exists
    try:
        if db_file.exists():
            db_file.unlink()
    except Exception:
        pass


# Note: Do NOT apply `live_server` as a global fixture here.
# Browser tests should opt in with `@pytest.mark.usefixtures("live_server")`
# to avoid starting the test server for every test file.