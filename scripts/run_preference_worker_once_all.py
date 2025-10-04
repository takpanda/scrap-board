#!/usr/bin/env python3
"""Run preference worker run_once repeatedly until no pending jobs remain or a limit is reached.

Use this in development to process the preference_jobs queue in a controlled manner.
"""
import time
import logging
from sqlalchemy import text
from app.core import database as app_db
from app.services.personalization_worker import run_once

logging.basicConfig(level=logging.INFO)

MAX_ITER = 200
SLEEP = 0.1

def pending_jobs_count():
    session = app_db.SessionLocal()
    try:
        res = session.execute(text("SELECT COUNT(*) FROM preference_jobs WHERE status IN ('pending','in_progress','failed')")).fetchone()
        return int(res[0]) if res and res[0] is not None else 0
    finally:
        session.close()

if __name__ == '__main__':
    logging.info('Starting controlled run_once loop (max=%s)', MAX_ITER)
    i = 0
    while i < MAX_ITER:
        count = pending_jobs_count()
        logging.info('Pending jobs: %s (iteration %s)', count, i)
        if count <= 0:
            logging.info('No pending jobs remain, exiting')
            break
        try:
            run_once()
        except Exception:
            logging.exception('run_once raised an exception')
        i += 1
        time.sleep(SLEEP)
    logging.info('Finished after %s iterations', i)
