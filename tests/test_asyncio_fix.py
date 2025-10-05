"""Standalone test for the asyncio fix without app dependencies."""
import asyncio
import sys
from threading import Thread
from concurrent.futures import ThreadPoolExecutor


def _run_coro_in_new_loop(coro):
    """Run an async coroutine safely in a worker thread without an event loop.
    
    This is a copy of the helper from ingest_worker.py for standalone testing.
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
    
    if loop and loop.is_running():
        result_container = {}
        
        def _runner():
            try:
                result_container["res"] = asyncio.run(coro)
            except Exception as e:
                result_container["exc"] = e
        
        t = Thread(target=_runner, daemon=True)
        t.start()
        t.join()
        if "exc" in result_container:
            raise result_container["exc"]
        return result_container.get("res")
    
    return asyncio.run(coro)


async def mock_extract_from_url(url: str):
    """Mock content extractor that simulates async HTTP request."""
    await asyncio.sleep(0.01)  # Simulate network delay
    return {"url": url, "content": f"content for {url}", "status": "ok"}


def test_in_thread():
    """Test that simulates ThreadPoolExecutor context (no event loop)."""
    print("Test 1: Running in Thread without event loop...")
    
    result_container = {}
    error_container = {}
    
    def worker():
        try:
            # This is what was failing before the fix
            # OLD CODE: asyncio.get_event_loop().run_until_complete(mock_extract_from_url("https://example.com"))
            # NEW CODE:
            result = _run_coro_in_new_loop(mock_extract_from_url("https://example.com"))
            result_container["value"] = result
        except Exception as e:
            error_container["error"] = e
    
    thread = Thread(target=worker)
    thread.start()
    thread.join()
    
    if "error" in error_container:
        print(f"  ❌ FAILED: {error_container['error']}")
        return False
    else:
        print(f"  ✅ PASSED: Got result: {result_container.get('value')}")
        return True


def test_in_threadpool():
    """Test with actual ThreadPoolExecutor (the real use case)."""
    print("\nTest 2: Running in ThreadPoolExecutor...")
    
    def worker_task(url):
        return _run_coro_in_new_loop(mock_extract_from_url(url))
    
    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            future1 = executor.submit(worker_task, "https://qiita.com/test1")
            future2 = executor.submit(worker_task, "https://hatena.ne.jp/test2")
            
            result1 = future1.result()
            result2 = future2.result()
        
        print(f"  ✅ PASSED: Got results from {result1['url']} and {result2['url']}")
        return True
    except Exception as e:
        print(f"  ❌ FAILED: {e}")
        return False


def test_exception_propagation():
    """Test that exceptions are properly propagated."""
    print("\nTest 3: Testing exception propagation...")
    
    async def failing_coro():
        await asyncio.sleep(0.01)
        raise ValueError("test_exception")
    
    try:
        _run_coro_in_new_loop(failing_coro())
        print("  ❌ FAILED: Exception was not raised")
        return False
    except ValueError as e:
        if "test_exception" in str(e):
            print(f"  ✅ PASSED: Exception properly propagated: {e}")
            return True
        else:
            print(f"  ❌ FAILED: Wrong exception: {e}")
            return False
    except Exception as e:
        print(f"  ❌ FAILED: Unexpected exception type: {e}")
        return False


async def test_with_existing_loop():
    """Test when called from context with running loop."""
    print("\nTest 4: Running with existing event loop...")
    
    try:
        result = _run_coro_in_new_loop(mock_extract_from_url("https://speakerdeck.com/test"))
        print(f"  ✅ PASSED: Got result even with existing loop: {result}")
        return True
    except Exception as e:
        print(f"  ❌ FAILED: {e}")
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("Testing asyncio ThreadPoolExecutor fix")
    print("=" * 60)
    
    results = []
    results.append(test_in_thread())
    results.append(test_in_threadpool())
    results.append(test_exception_propagation())
    
    # Test with existing loop (async context)
    results.append(asyncio.run(test_with_existing_loop()))
    
    print("\n" + "=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"Results: {passed}/{total} tests passed")
    print("=" * 60)
    
    sys.exit(0 if passed == total else 1)
