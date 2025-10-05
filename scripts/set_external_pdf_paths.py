#!/usr/bin/env python3
"""
Set external PDF URLs into documents.pdf_path for specific document IDs.

This is useful when PDFs are too large to download into local storage but
we still want the UI download button to point at the external PDF URL.

Usage:
  PYTHONPATH=. python scripts/set_external_pdf_paths.py
"""
from app.core.database import SessionLocal
from sqlalchemy import text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("set_external_pdf_paths")

MAPPINGS = {
    # doc_id: external_pdf_url
    "494e35b4-0885-4ca8-aca9-dd1696beec41": "https://files.speakerdeck.com/presentations/72f28d94eef34f2babed87b2dac0cd3b/2._React_Alicante_2025.pdf",
    "9a5c12da-2b64-4063-85be-adbedf24cd05": "https://files.speakerdeck.com/presentations/a51be9844436470992fd49410535d9a1/SanJose_CarPlay.pdf",
}


def main():
    session = SessionLocal()
    try:
        for doc_id, url in MAPPINGS.items():
            logger.info(f"Setting external pdf_path for {doc_id} -> {url}")
            session.execute(text("UPDATE documents SET pdf_path = :p WHERE id = :id"), {"p": url, "id": doc_id})
        session.commit()
        logger.info("Done")
    finally:
        session.close()


if __name__ == '__main__':
    main()
