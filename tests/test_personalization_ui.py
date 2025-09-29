import json
import uuid
from datetime import datetime, timedelta

import pytest
import requests
from playwright.sync_api import Page, expect
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base, Document, PersonalizedScore
from app.services.personalization_models import ExplanationBreakdown, PersonalizedScoreDTO
from app.services.personalized_repository import PersonalizedScoreRepository

pytestmark = [
    pytest.mark.browser,
    pytest.mark.usefixtures("live_server"),
    pytest.mark.slow,
]


def _prepare_session(db_url: str):
    engine = create_engine(db_url, connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return engine, TestingSessionLocal


def _seed_personalized_documents(db_url: str):
    engine, SessionMaker = _prepare_session(db_url)
    session = SessionMaker()
    try:
        Base.metadata.create_all(bind=engine)
        now = datetime.utcnow()

        session.query(PersonalizedScore).delete()
        session.query(Document).delete()
        session.commit()

        domain = "ui-personalized.test"

        doc_recent = Document(
            id=str(uuid.uuid4()),
            title="最新ニュース",
            url="https://ui-personalized.test/recent",
            domain=domain,
            content_md="# Latest",
            content_text="Latest article content",
            hash=str(uuid.uuid4()),
            created_at=now,
            updated_at=now,
        )

        doc_rank1 = Document(
            id=str(uuid.uuid4()),
            title="おすすめ記事1",
            url="https://ui-personalized.test/personalized-1",
            domain=domain,
            content_md="# Personalized 1",
            content_text="Personalized article 1",
            hash=str(uuid.uuid4()),
            created_at=now - timedelta(days=1),
            updated_at=now - timedelta(days=1),
        )

        doc_rank2 = Document(
            id=str(uuid.uuid4()),
            title="おすすめ記事2",
            url="https://ui-personalized.test/personalized-2",
            domain=domain,
            content_md="# Personalized 2",
            content_text="Personalized article 2",
            hash=str(uuid.uuid4()),
            created_at=now - timedelta(days=2),
            updated_at=now - timedelta(days=2),
        )

        session.add_all([doc_recent, doc_rank1, doc_rank2])
        session.commit()
        assert session.query(Document).count() == 3

        repo = PersonalizedScoreRepository(session)
        explanation = "あなたの嗜好に基づいて高評価です。"
        repo.bulk_upsert(
            [
                PersonalizedScoreDTO(
                    id=str(uuid.uuid4()),
                    document_id=doc_rank1.id,
                    score=0.91,
                    rank=1,
                    components=ExplanationBreakdown(
                        similarity=0.9,
                        category=0.7,
                        domain=0.5,
                        freshness=0.6,
                    ),
                    explanation=explanation,
                    computed_at=now,
                    user_id=None,
                    cold_start=False,
                ),
                PersonalizedScoreDTO(
                    id=str(uuid.uuid4()),
                    document_id=doc_rank2.id,
                    score=0.73,
                    rank=2,
                    components=ExplanationBreakdown(
                        similarity=0.6,
                        category=0.4,
                        domain=0.3,
                        freshness=0.5,
                    ),
                    explanation="関連度は中程度です。",
                    computed_at=now,
                    user_id=None,
                    cold_start=False,
                ),
            ],
            profile_id="profile-global",
            user_id=None,
        )

        return {
            "recent_title": doc_recent.title,
            "personalized_top_title": doc_rank1.title,
            "personalized_second_title": doc_rank2.title,
            "explanation": explanation,
        }
    finally:
        session.close()
        engine.dispose()


@pytest.mark.usefixtures("test_database_override")
def test_おすすめ順トグルとフィードバック送信(
    page: Page,
    test_database_override: str,
):
    seeded = _seed_personalized_documents(test_database_override)
    api_check = requests.get(
        "http://localhost:8000/api/documents",
        params={"domain": "ui-personalized.test", "limit": 5},
        timeout=5,
    )
    assert api_check.status_code == 200
    documents_payload = api_check.json()
    assert {
        doc.get("title") for doc in documents_payload.get("documents", [])
    } == {"最新ニュース", "おすすめ記事1", "おすすめ記事2"}
    api_personalized = requests.get(
        "http://localhost:8000/api/documents",
        params={"domain": "ui-personalized.test", "limit": 5, "sort": "personalized"},
        timeout=5,
    )
    assert api_personalized.status_code == 200
    payload = api_personalized.json()
    personalized_titles = [doc.get("title") for doc in payload.get("documents", [])]
    assert personalized_titles[:3] == [
        seeded["personalized_top_title"],
        seeded["personalized_second_title"],
        seeded["recent_title"],
    ]

    page.goto("http://localhost:8000/documents?domain=ui-personalized.test")
    page.wait_for_load_state("networkidle")
    page.wait_for_selector("[data-document-id]")

    default_first_title = page.locator('article a[href^="/documents/"]').first
    initial_title_text = default_first_title.inner_text()
    expect(page.locator("article", has_text=seeded["recent_title"]).first).to_be_visible()

    # パーソナライズ順に切り替え
    page.get_by_role("button", name="おすすめ順").click()

    page.wait_for_timeout(500)
    current_sort = page.evaluate(
        "() => document.querySelector('[data-sort-controls]')?.getAttribute('data-current-sort') || ''"
    )
    assert current_sort == "personalized"
    storage_value = page.evaluate(
        "() => window.localStorage.getItem('scrapBoard:documents-sort')"
    )
    assert storage_value == "personalized"
    status_text_after_click = page.evaluate(
        "() => document.querySelector('[data-personalized-status]')?.textContent || ''"
    )
    assert "おすすめ順で表示しています" in status_text_after_click

    status = page.locator("[data-personalized-status]")
    expect(status).to_contain_text("おすすめ順で表示しています", timeout=5000)

    top_title = page.locator('article a[href^="/documents/"]').first
    article_titles_after_click = page.evaluate(
        "() => Array.from(document.querySelectorAll('[data-documents-grid] > article')).map(article => {"
        "  const link = article.querySelector('header a[href^=\"/documents/\"]');"
        "  return link ? link.textContent.trim() : '';"
        "})"
    )
    assert article_titles_after_click[:2] == [
        seeded["personalized_top_title"],
        seeded["personalized_second_title"],
    ]
    expect(top_title).to_have_text(seeded["personalized_top_title"], timeout=5000)
    assert initial_title_text != seeded["personalized_top_title"]

    top_card = page.locator("article", has_text=seeded["personalized_top_title"]).first
    expect(top_card.locator("[data-personalized-block]")).to_be_visible()
    expect(top_card.locator("[data-personalized-explanation]")).to_contain_text(
        seeded["explanation"]
    )

    # リロード後も設定が保持されることを確認
    page.reload()
    page.wait_for_load_state("networkidle")
    expect(status).to_contain_text("おすすめ順で表示しています", timeout=5000)
    storage_after_reload = page.evaluate(
        "() => window.localStorage.getItem('scrapBoard:documents-sort')"
    )
    assert storage_after_reload == "personalized"

    top_title_after_reload = page.locator('article a[href^="/documents/"]').first
    expect(top_title_after_reload).to_have_text(seeded["personalized_top_title"], timeout=5000)
    top_card_after_reload = page.locator("article", has_text=seeded["personalized_top_title"]).first

    # フィードバックボタンを押下し、完了メッセージが表示されることを確認
    feedback_container = top_card_after_reload.locator("[data-personalized-feedback-container]")
    feedback_button = feedback_container.locator("[data-personalized-feedback-button]")
    expect(feedback_button).to_be_visible()
    feedback_button.click()

    expect(feedback_container).to_contain_text("フィードバックありがとうございました", timeout=5000)
    expect(feedback_container).to_have_attribute("data-feedback-state", "submitted")
    expect(feedback_container.locator("button")).to_have_count(0)

    document_identifier = top_card_after_reload.get_attribute("data-document-id")
    submitted_raw = page.evaluate(
        "() => window.sessionStorage.getItem('scrapBoard:feedback-submitted')"
    )
    submitted_list = json.loads(submitted_raw) if submitted_raw else []
    assert document_identifier in submitted_list