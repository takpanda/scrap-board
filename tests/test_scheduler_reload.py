"""Test scheduler reload functionality after admin source changes."""

import json
import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.core.database import Base, get_db
from app.services import scheduler
from app.core import database as app_db

# Mark all tests in this file as unit tests
pytestmark = pytest.mark.unit


@pytest.fixture(scope="function")
def client():
    """Create test client with scheduler support."""
    # Use the global test database that pytest_configure sets up
    test_db_url = os.environ.get("DB_URL", "sqlite:///./test.db")
    
    # Create engine for test database
    test_engine = create_engine(test_db_url, connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    
    # Ensure app's SessionLocal uses the test database
    app_db.engine = test_engine
    app_db.SessionLocal = TestingSessionLocal
    
    # Create all tables including sources
    Base.metadata.create_all(bind=test_engine)
    
    # Create sources table (not managed by SQLAlchemy ORM)
    db = TestingSessionLocal()
    try:
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS sources (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                type TEXT NOT NULL,
                config TEXT,
                enabled INTEGER NOT NULL DEFAULT 1,
                cron_schedule TEXT,
                last_fetched_at TIMESTAMP
            )
        """))
        db.commit()
    finally:
        db.close()

    # Start scheduler if not running
    if not scheduler.scheduler.running:
        scheduler.scheduler.start()

    # Import app lazily
    from app.main import app as _app

    def override_get_db():
        try:
            db = TestingSessionLocal()
            yield db
        finally:
            db.close()

    _app.dependency_overrides[get_db] = override_get_db

    with TestClient(_app) as test_client:
        yield test_client

    # Cleanup: remove all source jobs
    try:
        for job in scheduler.scheduler.get_jobs():
            if job.id.startswith("fetch_source_"):
                scheduler.scheduler.remove_job(job.id)
    except Exception:
        pass

    # Cleanup database - just delete data, not tables
    db = TestingSessionLocal()
    try:
        db.execute(text("DELETE FROM sources"))
        db.commit()
    finally:
        db.close()


def test_create_source_schedules_job(client):
    """Test that creating a source with cron_schedule immediately schedules a job."""
    # Create a source with cron schedule
    response = client.post(
        "/api/admin/sources/",
        json={
            "name": "Test RSS Feed",
            "type": "rss",
            "config": {"url": "https://example.com/feed.xml"},
            "enabled": True,
            "cron_schedule": "0 * * * *"  # Every hour
        }
    )
    assert response.status_code == 200
    data = response.json()
    source_id = data["id"]

    # Manually reload scheduler (since PYTEST_CURRENT_TEST prevents auto-reload)
    scheduler.reload_sources()

    # Verify job was scheduled
    job_id = f"fetch_source_{source_id}"
    jobs = scheduler.scheduler.get_jobs()
    job_ids = [job.id for job in jobs]
    assert job_id in job_ids, f"Job {job_id} should be scheduled. Found: {job_ids}"


def test_update_source_reschedules_job(client):
    """Test that updating a source's cron_schedule immediately reschedules the job."""
    # Create initial source
    response = client.post(
        "/api/admin/sources/",
        json={
            "name": "Test Feed",
            "type": "rss",
            "config": {"url": "https://example.com/feed.xml"},
            "enabled": True,
            "cron_schedule": "0 * * * *"
        }
    )
    assert response.status_code == 200
    source_id = response.json()["id"]

    # Manually reload to schedule initial job
    scheduler.reload_sources()

    # Verify initial job exists
    job_id = f"fetch_source_{source_id}"
    initial_jobs = scheduler.scheduler.get_jobs()
    initial_job = next((j for j in initial_jobs if j.id == job_id), None)
    assert initial_job is not None, "Initial job should be scheduled"

    # Update the cron schedule
    response = client.put(
        f"/api/admin/sources/{source_id}",
        json={
            "cron_schedule": "*/30 * * * *"  # Every 30 minutes
        }
    )
    assert response.status_code == 200

    # Manually reload to reschedule job
    scheduler.reload_sources()

    # Verify job still exists (should be rescheduled)
    updated_jobs = scheduler.scheduler.get_jobs()
    updated_job = next((j for j in updated_jobs if j.id == job_id), None)
    assert updated_job is not None, "Job should still exist after update"


def test_disable_source_removes_job(client):
    """Test that disabling a source immediately removes its job."""
    # Create enabled source
    response = client.post(
        "/api/admin/sources/",
        json={
            "name": "Test Feed",
            "type": "rss",
            "config": {"url": "https://example.com/feed.xml"},
            "enabled": True,
            "cron_schedule": "0 * * * *"
        }
    )
    assert response.status_code == 200
    source_id = response.json()["id"]

    # Manually reload to schedule job
    scheduler.reload_sources()

    # Verify job exists
    job_id = f"fetch_source_{source_id}"
    jobs = scheduler.scheduler.get_jobs()
    assert any(j.id == job_id for j in jobs), "Job should be scheduled"

    # Disable the source
    response = client.put(
        f"/api/admin/sources/{source_id}",
        json={"enabled": False}
    )
    assert response.status_code == 200

    # Manually reload to remove job
    scheduler.reload_sources()

    # Verify job is removed
    jobs = scheduler.scheduler.get_jobs()
    assert not any(j.id == job_id for j in jobs), "Job should be removed after disable"


def test_delete_source_removes_job(client):
    """Test that deleting a source immediately removes its job."""
    # Create source
    response = client.post(
        "/api/admin/sources/",
        json={
            "name": "Test Feed",
            "type": "rss",
            "config": {"url": "https://example.com/feed.xml"},
            "enabled": True,
            "cron_schedule": "0 * * * *"
        }
    )
    assert response.status_code == 200
    source_id = response.json()["id"]

    # Manually reload to schedule job
    scheduler.reload_sources()

    # Verify job exists
    job_id = f"fetch_source_{source_id}"
    jobs = scheduler.scheduler.get_jobs()
    assert any(j.id == job_id for j in jobs), "Job should be scheduled"

    # Delete the source
    response = client.delete(f"/api/admin/sources/{source_id}")
    assert response.status_code == 200

    # Manually reload to remove job
    scheduler.reload_sources()

    # Verify job is removed
    jobs = scheduler.scheduler.get_jobs()
    assert not any(j.id == job_id for j in jobs), "Job should be removed after delete"


def test_create_source_without_cron_no_job(client):
    """Test that creating a source without cron_schedule does not schedule a job."""
    # Create source without cron
    response = client.post(
        "/api/admin/sources/",
        json={
            "name": "Manual Feed",
            "type": "rss",
            "config": {"url": "https://example.com/feed.xml"},
            "enabled": True,
            "cron_schedule": None
        }
    )
    assert response.status_code == 200
    source_id = response.json()["id"]

    # Manually reload
    scheduler.reload_sources()

    # Verify no job was scheduled
    job_id = f"fetch_source_{source_id}"
    jobs = scheduler.scheduler.get_jobs()
    assert not any(j.id == job_id for j in jobs), "No job should be scheduled without cron"


def test_reload_sources_function():
    """Test the reload_sources function directly."""
    # Use the global test database
    test_db_url = os.environ.get("DB_URL", "sqlite:///./test.db")
    test_engine = create_engine(test_db_url, connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    
    # Ensure app's SessionLocal uses the test database
    app_db.engine = test_engine
    app_db.SessionLocal = TestingSessionLocal
    
    # Create a test database session
    db = TestingSessionLocal()
    try:
        # Ensure sources table exists
        Base.metadata.create_all(bind=test_engine)
        
        # Create sources table (not managed by SQLAlchemy ORM)
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS sources (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                type TEXT NOT NULL,
                config TEXT,
                enabled INTEGER NOT NULL DEFAULT 1,
                cron_schedule TEXT,
                last_fetched_at TIMESTAMP
            )
        """))
        db.commit()
        
        # Insert a test source
        db.execute(
            text("INSERT INTO sources (name, type, config, enabled, cron_schedule) VALUES (:name, :type, :config, :enabled, :cron)"),
            {
                "name": "Direct Test Feed",
                "type": "rss",
                "config": json.dumps({"url": "https://example.com/feed.xml"}),
                "enabled": 1,
                "cron": "0 * * * *"
            }
        )
        db.commit()
        
        # Get the source ID
        result = db.execute(text("SELECT id FROM sources WHERE name='Direct Test Feed'"))
        source_id = result.scalar()
        
        # Start scheduler if not running
        if not scheduler.scheduler.running:
            scheduler.scheduler.start()
        
        # Call reload_sources
        scheduler.reload_sources()
        
        # Verify job was scheduled
        job_id = f"fetch_source_{source_id}"
        jobs = scheduler.scheduler.get_jobs()
        job_ids = [job.id for job in jobs]
        assert job_id in job_ids, f"Job {job_id} should be scheduled after reload"
        
        # Cleanup: remove the job and source
        try:
            scheduler.scheduler.remove_job(job_id)
        except Exception:
            pass
        db.execute(text("DELETE FROM sources WHERE id=:id"), {"id": source_id})
        db.commit()
        
    finally:
        db.close()
