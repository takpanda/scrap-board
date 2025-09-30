"""嗜好分析機能のテスト"""

import json
import uuid
from datetime import datetime, timedelta
from typing import List

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.database import Bookmark, Classification, Document, PreferenceProfile, SessionLocal
from app.services.preference_analysis import PreferenceAnalysisService
from app.main import app


@pytest.fixture
def client():
    """TestClientを返す"""
    return TestClient(app)


def _create_document(
    db: Session,
    title: str,
    category: str = None,
    domain: str = "example.com",
    tags: List[str] = None,
    **kwargs
) -> Document:
    """テスト用のドキュメントを作成"""
    doc = Document(
        id=str(uuid.uuid4()),
        url=f"https://{domain}/article-{uuid.uuid4()}",
        title=title,
        domain=domain,
        content_md=f"# {title}\nContent",
        content_text=f"Content for {title}",
        hash=str(uuid.uuid4()),
        created_at=kwargs.get("created_at", datetime.utcnow()),
        **{k: v for k, v in kwargs.items() if k not in ["created_at", "category", "tags"]}
    )
    db.add(doc)
    db.flush()

    # カテゴリが指定されている場合は Classification を作成
    if category or tags:
        classification = Classification(
            id=str(uuid.uuid4()),
            document_id=doc.id,
            primary_category=category or "その他",
            topics=[],
            tags=tags or [],
            confidence=0.9,
            method="test",
            created_at=datetime.utcnow(),
        )
        db.add(classification)

    db.commit()
    db.refresh(doc)
    return doc


def _create_bookmark(
    db: Session,
    document: Document,
    user_id: str = None,
    created_at: datetime = None,
    note: str = None
) -> Bookmark:
    """テスト用のブックマークを作成"""
    bookmark = Bookmark(
        id=str(uuid.uuid4()),
        document_id=document.id,
        user_id=user_id,
        created_at=created_at or datetime.utcnow(),
        note=note,
    )
    db.add(bookmark)
    db.commit()
    db.refresh(bookmark)
    return bookmark


def _create_preference_profile(
    db: Session,
    user_id: str = None,
    category_weights: dict = None,
    domain_weights: dict = None,
    status: str = "active",
    bookmark_count: int = 0
) -> PreferenceProfile:
    """テスト用の嗜好プロファイルを作成"""
    profile = PreferenceProfile(
        id=str(uuid.uuid4()),
        user_id=user_id,
        bookmark_count=bookmark_count,
        category_weights=json.dumps(category_weights) if category_weights else "{}",
        domain_weights=json.dumps(domain_weights) if domain_weights else "{}",
        status=status,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


def test_analyze_preferences_empty_bookmarks():
    """ブックマークがない場合の分析テスト"""
    with SessionLocal() as db:
        service = PreferenceAnalysisService()
        result = service.analyze_preferences(db, user_id=None)

        assert result["summary"]["total_bookmarks"] == 0
        assert len(result["top_topics"]) == 0
        assert len(result["top_keywords"]) == 0
        assert len(result["top_articles"]) == 0
        assert len(result["recent_bookmarks"]) == 0


def test_analyze_preferences_with_bookmarks():
    """ブックマークがある場合の分析テスト"""
    with SessionLocal() as db:
        # テストデータ作成
        doc1 = _create_document(
            db,
            title="AI技術の最新動向",
            category="テック/AI",
            domain="tech.example.com",
            tags=["AI", "機械学習", "深層学習"]
        )
        doc2 = _create_document(
            db,
            title="Python開発のベストプラクティス",
            category="ソフトウェア開発",
            domain="dev.example.com",
            tags=["Python", "プログラミング"]
        )
        doc3 = _create_document(
            db,
            title="AIで変わるビジネス",
            category="テック/AI",
            domain="biz.example.com",
            tags=["AI", "ビジネス"]
        )

        _create_bookmark(db, doc1, created_at=datetime.utcnow() - timedelta(days=1))
        _create_bookmark(db, doc2, created_at=datetime.utcnow() - timedelta(days=2))
        _create_bookmark(db, doc3, created_at=datetime.utcnow() - timedelta(hours=1))

        # 分析実行
        service = PreferenceAnalysisService()
        result = service.analyze_preferences(db, user_id=None)

        # サマリー検証
        assert result["summary"]["total_bookmarks"] == 3
        assert result["summary"]["categories_count"] == 2
        assert result["summary"]["unique_domains"] == 3

        # トピック検証
        assert len(result["top_topics"]) == 2
        ai_topic = next((t for t in result["top_topics"] if t["name"] == "テック/AI"), None)
        assert ai_topic is not None
        assert ai_topic["count"] == 2
        assert ai_topic["percentage"] == pytest.approx(66.7, abs=0.1)

        # キーワード検証
        assert len(result["top_keywords"]) > 0
        ai_keyword = next((k for k in result["top_keywords"] if k["keyword"] == "AI"), None)
        assert ai_keyword is not None
        assert ai_keyword["count"] == 3

        # 上位記事検証
        assert len(result["top_articles"]) == 3
        assert result["top_articles"][0]["title"] == "AIで変わるビジネス"  # 最新

        # 最近のブックマーク検証
        assert len(result["recent_bookmarks"]) == 3


def test_analyze_preferences_with_profile():
    """プロファイル情報を含む分析テスト"""
    with SessionLocal() as db:
        # テストデータ作成
        doc1 = _create_document(db, title="Test Article", category="テック/AI")
        _create_bookmark(db, doc1)

        # プロファイル作成
        _create_preference_profile(
            db,
            user_id=None,
            category_weights={"テック/AI": 0.8, "ビジネス": 0.2},
            domain_weights={"example.com": 0.5},
            status="active",
            bookmark_count=1
        )

        # 分析実行
        service = PreferenceAnalysisService()
        result = service.analyze_preferences(db, user_id=None)

        # プロファイル情報の検証
        assert result["summary"]["profile_status"] == "active"
        assert "weights" in result["profile_weights"]
        assert "categories" in result["profile_weights"]["weights"]
        assert result["profile_weights"]["weights"]["categories"]["テック/AI"] == 0.8


def test_api_endpoint_preferences_analysis(client):
    """APIエンドポイントのテスト"""
    with SessionLocal() as db:
        # テストデータ作成
        doc = _create_document(
            db,
            title="Test Document",
            category="テック/AI",
            tags=["test", "api"]
        )
        _create_bookmark(db, doc)

    # APIリクエスト
    response = client.get("/api/preferences/analysis")

    assert response.status_code == 200
    data = response.json()

    # レスポンス構造の検証
    assert "top_topics" in data
    assert "top_keywords" in data
    assert "top_articles" in data
    assert "recent_bookmarks" in data
    assert "summary" in data

    # データの検証
    assert data["summary"]["total_bookmarks"] == 1
    assert len(data["top_topics"]) > 0
    assert data["top_topics"][0]["name"] == "テック/AI"


def test_preferences_page_rendering(client):
    """嗜好分析ページの表示テスト"""
    with SessionLocal() as db:
        # テストデータ作成
        doc = _create_document(
            db,
            title="Test Article for Page",
            category="テック/AI"
        )
        _create_bookmark(db, doc)

    # ページリクエスト
    response = client.get("/preferences")

    assert response.status_code == 200
    assert "ブックマーク嗜好分析" in response.text
    assert "Test Article for Page" in response.text


def test_keyword_extraction():
    """キーワード抽出機能のテスト"""
    with SessionLocal() as db:
        # 日本語と英語混在のタイトル
        doc1 = _create_document(
            db,
            title="機械学習とDeep Learningの実践ガイド",
            tags=["機械学習", "AI", "Python"]
        )
        doc2 = _create_document(
            db,
            title="APIデザインのベストプラクティス",
            tags=["API", "設計"]
        )

        _create_bookmark(db, doc1)
        _create_bookmark(db, doc2)

        service = PreferenceAnalysisService()
        result = service.analyze_preferences(db, user_id=None)

        # キーワードが抽出されていることを確認
        keywords = [k["keyword"] for k in result["top_keywords"]]
        assert "機械学習" in keywords or "AI" in keywords or "API" in keywords


def test_top_articles_limit():
    """上位記事のリミットテスト"""
    with SessionLocal() as db:
        # 15件のドキュメントを作成
        for i in range(15):
            doc = _create_document(
                db,
                title=f"Article {i}",
                created_at=datetime.utcnow() - timedelta(days=i)
            )
            _create_bookmark(
                db,
                doc,
                created_at=datetime.utcnow() - timedelta(days=i)
            )

        service = PreferenceAnalysisService(max_top_articles=10)
        result = service.analyze_preferences(db, user_id=None)

        # 上位記事が10件に制限されていることを確認
        assert len(result["top_articles"]) == 10
        assert result["summary"]["total_bookmarks"] == 15


def test_user_specific_analysis():
    """ユーザー別の分析テスト"""
    with SessionLocal() as db:
        # ユーザーAのブックマーク
        doc_a = _create_document(db, title="User A Article", category="テック/AI")
        _create_bookmark(db, doc_a, user_id="user-a")

        # ユーザーBのブックマーク
        doc_b = _create_document(db, title="User B Article", category="ビジネス")
        _create_bookmark(db, doc_b, user_id="user-b")

        # グローバルブックマーク
        doc_global = _create_document(db, title="Global Article", category="研究")
        _create_bookmark(db, doc_global, user_id=None)

        service = PreferenceAnalysisService()

        # ユーザーAの分析
        result_a = service.analyze_preferences(db, user_id="user-a")
        assert result_a["summary"]["total_bookmarks"] == 1
        assert result_a["top_topics"][0]["name"] == "テック/AI"

        # ユーザーBの分析
        result_b = service.analyze_preferences(db, user_id="user-b")
        assert result_b["summary"]["total_bookmarks"] == 1
        assert result_b["top_topics"][0]["name"] == "ビジネス"

        # グローバルの分析
        result_global = service.analyze_preferences(db, user_id=None)
        assert result_global["summary"]["total_bookmarks"] == 1
        assert result_global["top_topics"][0]["name"] == "研究"
