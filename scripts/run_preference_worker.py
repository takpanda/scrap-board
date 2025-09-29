#!/usr/bin/env python3
"""Development helper to run the preference job worker."""

import argparse
import logging

from app.services.personalization_worker import run_worker


def main() -> None:
	parser = argparse.ArgumentParser(description="Run the preference worker loop")
	parser.add_argument(
		"--interval",
		type=float,
		default=2.0,
		help="Polling interval in seconds (default: 2.0)",
	)
	parser.add_argument(
		"--log-level",
		type=str,
		default="INFO",
		help="Logging level (default: INFO)",
	)
	args = parser.parse_args()

	logging.basicConfig(level=getattr(logging, args.log_level.upper(), logging.INFO))

	run_worker(poll_interval=args.interval)


if __name__ == "__main__":
	main()
