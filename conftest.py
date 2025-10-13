"""Pytest configuration for browser testing with Japanese text support."""

import pytest
import os
import subprocess
import time
from threading import Thread

# Global handles for in-process uvicorn server
server = None
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
    """Start a live FastAPI server within the same process for browser testing."""
    global server, server_thread

    import asyncio as _asyncio
    import httpx as _httpx
    import uvicorn

    # Ensure the running process and uvicorn server use the temp test DB.
    if isinstance(test_database_override, str):
        os.environ["DB_URL"] = test_database_override
        try:
            from app.core.config import settings as _settings
            _settings.db_url = test_database_override
        except Exception:
            pass

    # Build uvicorn server config bound to the already-imported FastAPI app.
    from app.main import app as fastapi_app

    config = uvicorn.Config(
        fastapi_app,
        host="127.0.0.1",
        port=8000,
        log_level="error",
        loop="asyncio",
    )

    server = uvicorn.Server(config)

    def _run_server():
        loop = _asyncio.new_event_loop()
        _asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(server.serve())
        finally:
            loop.close()

    server_thread = Thread(target=_run_server, daemon=True)
    server_thread.start()

    # Wait for the server to become responsive
    for _ in range(50):
        try:
            response = _httpx.get("http://localhost:8000/health", timeout=1)
            if response.status_code == 200:
                break
        except Exception:
            time.sleep(0.2)
    else:
        server.should_exit = True
        server_thread.join(timeout=5)
        pytest.skip("Could not start test server")

    yield "http://localhost:8000"

    # Signal server shutdown and wait for the thread to finish
    try:
        if server is not None:
            server.should_exit = True
        if server_thread is not None:
            server_thread.join(timeout=5)
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
    
    If DB_URL is already set (e.g., in CI with migrations applied), use that database
    instead of creating a new temporary one.
    """
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.core.database import Base, get_db, SessionLocal
    import os
    from pathlib import Path
    
    # Check if DB_URL is already set (e.g., by CI or pytest_configure)
    existing_db_url = os.environ.get("DB_URL")
    if existing_db_url and "test.db" in existing_db_url:
        # Use the existing database (with migrations already applied in CI)
        db_url = existing_db_url
        db_file = Path(existing_db_url.replace("sqlite:///", ""))
    else:
        # Build test DB path for local development
        db_file = tmp_path_factory.mktemp("data") / "tests.sqlite"
        db_url = f"sqlite:///{db_file}"

    engine = create_engine(db_url, connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    # Ensure the originally imported SessionLocal object points to the
    # test database engine so any modules that imported it earlier
    # (e.g. individual test modules) use the same temporary database.
    try:
        SessionLocal.configure(bind=engine)
    except Exception:
        pass

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
        # Ensure the app's SessionLocal uses the same engine. When tests have
        # already imported SessionLocal, mutating the existing sessionmaker via
        # configure keeps all references aligned with the temporary database.
        try:
            app_db.SessionLocal.configure(bind=engine)
        except Exception:
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

    # Teardown: remove DB file if exists (only for temporary databases, not test.db)
    try:
        existing_db_url = os.environ.get("DB_URL")
        # Only delete temporary test databases, not the test.db used in CI
        if db_file.exists() and "test.db" not in str(db_file):
            db_file.unlink()
    except Exception:
        pass


@pytest.fixture(autouse=True)
def _reset_database_between_tests(test_database_override):
    """Ensure each test runs against a clean SQLite database by deleting all data."""
    from sqlalchemy import create_engine, inspect, text
    from sqlalchemy.orm import sessionmaker
    from app.core.database import Base
    
    # Create a new engine for cleanup to ensure we're not using cached connections
    cleanup_engine = create_engine(
        test_database_override,
        connect_args={"check_same_thread": False},
        poolclass=None,  # Disable connection pooling for cleanup
    )
    
    # Ensure tables exist before the test runs
    Base.metadata.create_all(bind=cleanup_engine)
    
    # Clean up data BEFORE the test runs to ensure a clean slate
    try:
        SessionLocal = sessionmaker(bind=cleanup_engine)
        session = SessionLocal()
        try:
            # Get all table names
            inspector = inspect(cleanup_engine)
            table_names = inspector.get_table_names()
            
            # Disable foreign key constraints for SQLite
            if "sqlite" in test_database_override:
                session.execute(text("PRAGMA foreign_keys = OFF"))
            
            # Delete all data from each table in reverse order to handle foreign keys
            for table in reversed(Base.metadata.sorted_tables):
                if table.name in table_names:
                    session.execute(table.delete())
            
            session.commit()
            
            # Re-enable foreign key constraints for SQLite
            if "sqlite" in test_database_override:
                session.execute(text("PRAGMA foreign_keys = ON"))
                session.commit()
        except Exception:
            session.rollback()
        finally:
            session.close()
    except Exception:
        pass
    finally:
        # Always dispose the cleanup engine
        try:
            cleanup_engine.dispose()
        except Exception:
            pass
    
    yield
    
    # After test completes, dispose connections to ensure next test gets fresh state
    try:
        from app.core import database as app_db
        if hasattr(app_db, 'engine') and app_db.engine is not None:
            app_db.engine.dispose()
    except Exception:
        pass
    
    # Note: We don't clean up after the test to avoid interfering with
    # any teardown logic the test itself might have. The next test will
    # clean up before it runs.


@pytest.fixture(scope="function", autouse=True)
def seed_demo_documents(test_database_override, _reset_database_between_tests):
    """Seed a small demo document into the test DB so E2E tests have content.

    This runs once per test session after the temporary DB is created by
    `test_database_override`. It is intentionally permissive and best-effort
    so it doesn't fail the test run if seeding cannot be performed.
    """
    try:
        from app.core.database import SessionLocal, create_tables, Document, Classification
        # Ensure tables exist
        create_tables()
        session = SessionLocal()

        doc_id = "demo-seed-doc-1"
        # Remove any previous demo doc to allow repeated runs
        try:
            session.query(Classification).filter(Classification.document_id == doc_id).delete()
            session.query(Document).filter(Document.id == doc_id).delete()
            session.commit()
        except Exception:
            session.rollback()

        # Insert a small demo document used by E2E tests
        from datetime import datetime, timezone

        document = Document(
            id=doc_id,
            title="デモ記事: モバイルモーダルテスト",
            url="https://example.com/demo-mobile-modal",
            domain="example.com",
            content_md="# デモコンテンツ\n\nこれはテスト用のデモ記事です。",
            content_text="デモコンテンツ - これはテスト用のデモ記事です。",
            short_summary="モバイルモーダルのデモ記事",
            hash="demo-seed-hash-1",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            fetched_at=datetime.now(timezone.utc),
        )
        session.add(document)

        classification = Classification(
            document_id=doc_id,
            primary_category="テスト/モーダル",
            topics=["モーダル", "レスポンシブ"],
            # Include at least one extremely long tag to force overflow/truncation in mobile modal
            tags=[
                "e2e",
                "playwright",
                "this-is-a-very-long-tag-name-for-testing-overflow-behavior-please-ignore-0123456789-" * 2,
            ],
            confidence=0.95,
            method="manual",
        )
        session.add(classification)

        session.commit()
        session.close()
    except Exception:
        # Best-effort: don't fail the entire test session if seeding fails.
        pass
    yield


# Note: Do NOT apply `live_server` as a global fixture here.
# Browser tests should opt in with `@pytest.mark.usefixtures("live_server")`
# to avoid starting the test server for every test file.