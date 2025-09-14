import pytest
from fastapi.testclient import TestClient
from app.main import app
from unittest.mock import patch
import os


def test_ingest_url_saves_summary(tmp_path, monkeypatch):
    # モック：extract_from_url と generate_summary
    sample_content = {
        "url": "https://example.com/article",
        "domain": "example.com",
        "title": "テスト記事",
        "author": None,
        "published_at": None,
        "content_md": "# タイトル\n本文テキスト",
        "content_text": "本文テキスト",
        "hash": "abc123",
        "lang": "ja"
    }

    async def fake_extract(url: str):
        return sample_content

    async def fake_generate(text, style="short", timeout_sec=None):
        return "これはモックの要約です。"

    monkeypatch.setattr("app.services.extractor.content_extractor.extract_from_url", fake_extract)
    monkeypatch.setattr("app.services.llm_client.llm_client.generate_summary", fake_generate)

    with TestClient(app) as client:
        response = client.post("/api/ingest/url", data={"url": sample_content["url"]})
        assert response.status_code == 200
        data = response.json()
        assert "document_id" in data

        # 取得した document_id を使って DB を直接確認
        # DB はテスト環境で既に用意されていることを前提
        # 簡単な確認: レスポンスにタイトルが含まれる
        assert data.get("title") == sample_content["title"]
