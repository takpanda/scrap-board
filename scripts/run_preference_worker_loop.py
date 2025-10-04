"""Run the personalization worker run_once in a loop until no more jobs.

Usage: PYTHONPATH=. python scripts/run_preference_worker_loop.py
"""
from __future__ import annotations

from time import sleep
from app.services.personalization_worker import run_once


def main():
    iteration = 0
    while True:
        iteration += 1
        res = run_once()
        print(f"run_once() -> {res} (iteration {iteration})")
        if not res:
            print("No more jobs to process. Exiting loop.")
            break
        sleep(0.05)


if __name__ == "__main__":
    main()
