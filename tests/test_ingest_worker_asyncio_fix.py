"""Test for ThreadPoolExecutor asyncio fix in ingest_worker.py

This test verifies that _run_coro_in_new_loop can safely execute
coroutines in worker threads without event loops.
"""
import asyncio
import pytest
from threading import Thread
from concurrent.futures import ThreadPoolExecutor


def test_run_coro_in_new_loop_import():
    """Test that _run_coro_in_new_loop can be imported."""
    from app.services.ingest_worker import _run_coro_in_new_loop
    assert callable(_run_coro_in_new_loop)


def test_run_coro_in_new_loop_basic():
    """Test _run_coro_in_new_loop with a simple coroutine."""
    from app.services.ingest_worker import _run_coro_in_new_loop
    
    async def simple_coro():
        await asyncio.sleep(0.01)
        return "test_result"
    
    # Call from main thread (no event loop)
    result = _run_coro_in_new_loop(simple_coro())
    assert result == "test_result"


def test_run_coro_in_new_loop_in_thread():
    """Test _run_coro_in_new_loop from a worker thread (simulating ThreadPoolExecutor)."""
    from app.services.ingest_worker import _run_coro_in_new_loop
    
    async def async_task():
        await asyncio.sleep(0.01)
        return "worker_result"
    
    result_container = {}
    error_container = {}
    
    def worker():
        """Worker function that runs in a thread without an event loop."""
        try:
            # This should NOT raise "There is no current event loop in thread" error
            result = _run_coro_in_new_loop(async_task())
            result_container["value"] = result
        except Exception as e:
            error_container["error"] = e
    
    # Run in a thread (simulating ThreadPoolExecutor context)
    thread = Thread(target=worker)
    thread.start()
    thread.join()
    
    # Verify no error occurred
    assert "error" not in error_container, f"Unexpected error: {error_container.get('error')}"
    assert result_container.get("value") == "worker_result"


def test_run_coro_in_new_loop_with_threadpoolexecutor():
    """Test _run_coro_in_new_loop with actual ThreadPoolExecutor."""
    from app.services.ingest_worker import _run_coro_in_new_loop
    
    async def async_fetch():
        await asyncio.sleep(0.01)
        return "threadpool_result"
    
    def worker_task():
        """This simulates what trigger_fetch_for_source does."""
        return _run_coro_in_new_loop(async_fetch())
    
    # Execute in ThreadPoolExecutor (this is the actual use case)
    with ThreadPoolExecutor(max_workers=2) as executor:
        future1 = executor.submit(worker_task)
        future2 = executor.submit(worker_task)
        
        result1 = future1.result()
        result2 = future2.result()
    
    assert result1 == "threadpool_result"
    assert result2 == "threadpool_result"


def test_run_coro_in_new_loop_exception_propagation():
    """Test that exceptions in the coroutine are properly propagated."""
    from app.services.ingest_worker import _run_coro_in_new_loop
    
    async def failing_coro():
        await asyncio.sleep(0.01)
        raise ValueError("test_exception")
    
    with pytest.raises(ValueError, match="test_exception"):
        _run_coro_in_new_loop(failing_coro())


@pytest.mark.asyncio
async def test_run_coro_in_new_loop_with_existing_loop():
    """Test _run_coro_in_new_loop when called from a context with a running loop."""
    from app.services.ingest_worker import _run_coro_in_new_loop
    
    async def nested_coro():
        await asyncio.sleep(0.01)
        return "nested_result"
    
    # This is called from within an async test, so there's a running loop
    # The helper should handle this by executing in a separate thread
    result = _run_coro_in_new_loop(nested_coro())
    assert result == "nested_result"
