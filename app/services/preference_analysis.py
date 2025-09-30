"""ブックマーク嗜好分析サービス - ユーザーのブックマーク傾向を分析する"""

from __future__ import annotations

import json
import logging
from collections import Counter
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse

from sqlalchemy.orm import Session, joinedload

from app.core.database import Bookmark, Document, PreferenceProfile

logger = logging.getLogger(__name__)


class PreferenceAnalysisService:
    """ブックマーク記事からユーザー嗜好を分析するサービス"""

    def __init__(self, max_keywords: int = 20, max_top_articles: int = 10):
        """
        Args:
            max_keywords: 抽出する最大キーワード数
            max_top_articles: 表示する最大上位記事数
        """
        self.max_keywords = max_keywords
        self.max_top_articles = max_top_articles

    def analyze_preferences(
        self, db: Session, user_id: Optional[str] = None
    ) -> Dict[str, any]:
        """
        ユーザーのブックマーク記事を分析し、嗜好情報を返す

        Args:
            db: データベースセッション
            user_id: ユーザーID（Noneの場合はグローバル）

        Returns:
            嗜好分析結果を含む辞書:
            {
                "top_topics": [{"name": str, "count": int, "percentage": float}],
                "top_keywords": [{"keyword": str, "count": int}],
                "top_articles": [{"title": str, "domain": str, "category": str, ...}],
                "recent_bookmarks": [{"title": str, "bookmarked_at": str, ...}],
                "summary": {"total_bookmarks": int, "categories_count": int, ...}
            }
        """
        # ブックマークを取得
        bookmarks = self._load_bookmarks(db, user_id)

        if not bookmarks:
            return self._empty_result()

        # カテゴリ/トピック頻度を計算
        top_topics = self._calculate_topic_frequency(bookmarks)

        # キーワードを抽出
        top_keywords = self._extract_keywords(bookmarks)

        # 上位記事を選定
        top_articles = self._select_top_articles(bookmarks)

        # 最近のブックマークを取得
        recent_bookmarks = self._get_recent_bookmarks(bookmarks)

        # プロファイル情報を取得
        profile_info = self._get_profile_info(db, user_id)

        # サマリー情報を作成
        summary = {
            "total_bookmarks": len(bookmarks),
            "categories_count": len(top_topics),
            "unique_domains": len(set(self._get_domain(b.document) for b in bookmarks if b.document)),
            "profile_status": profile_info.get("status", "unknown"),
            "last_updated": profile_info.get("updated_at"),
        }

        result = {
            "top_topics": top_topics,
            "top_keywords": top_keywords,
            "top_articles": top_articles,
            "recent_bookmarks": recent_bookmarks,
            "summary": summary,
            "profile_weights": profile_info.get("weights", {}),
        }
        return result

    def _load_bookmarks(
        self, db: Session, user_id: Optional[str]
    ) -> List[Bookmark]:
        """ブックマークをロードする"""
        query = db.query(Bookmark).options(
            joinedload(Bookmark.document).joinedload(Document.classifications)
        )

        if user_id is None:
            query = query.filter(Bookmark.user_id.is_(None))
        else:
            query = query.filter(Bookmark.user_id == user_id)

        query = query.order_by(Bookmark.created_at.desc())
        return list(query.all())

    def _calculate_topic_frequency(
        self, bookmarks: List[Bookmark]
    ) -> List[Dict[str, any]]:
        """カテゴリ/トピック頻度を計算"""
        category_counter = Counter()

        for bookmark in bookmarks:
            doc = bookmark.document
            if not doc:
                continue

            # 分類から抽出
            if hasattr(doc, "classifications") and doc.classifications:
                for classification in doc.classifications:
                    cat = getattr(classification, "primary_category", None)
                    if cat:
                        category_counter[cat] += 1

        total = sum(category_counter.values())
        if total == 0:
            return []

        # 上位トピックを返す
        result = []
        for topic, count in category_counter.most_common(10):
            result.append({
                "name": topic,
                "count": count,
                "percentage": round((count / total) * 100, 1),
            })

        return result

    def _extract_keywords(self, bookmarks: List[Bookmark]) -> List[Dict[str, any]]:
        """キーワードを抽出"""
        keyword_counter = Counter()

        for bookmark in bookmarks:
            doc = bookmark.document
            if not doc:
                continue

            # タイトルから単語を抽出
            title = getattr(doc, "title", None)
            if title:
                # 簡易的なキーワード抽出（スペースと句読点で分割）
                words = self._extract_words_from_text(title)
                for word in words:
                    if len(word) >= 2:  # 2文字以上のみ
                        keyword_counter[word] += 1

            # 分類のタグから抽出
            if hasattr(doc, "classifications") and doc.classifications:
                for classification in doc.classifications:
                    tags = getattr(classification, "tags", None)
                    if tags:
                        if isinstance(tags, list):
                            for tag in tags:
                                if isinstance(tag, str):
                                    keyword_counter[tag] += 1

        # 上位キーワードを返す
        result = []
        for keyword, count in keyword_counter.most_common(self.max_keywords):
            result.append({"keyword": keyword, "count": count})

        return result

    def _extract_words_from_text(self, text: str) -> List[str]:
        """テキストから単語を抽出する簡易処理"""
        import re
        # 英数字と日本語文字を抽出
        words = re.findall(r'[a-zA-Z0-9]+|[ぁ-んァ-ヶー一-龠]+', text)
        return words

    def _select_top_articles(
        self, bookmarks: List[Bookmark]
    ) -> List[Dict[str, any]]:
        """上位記事を選定（最近ブックマークされた記事から）"""
        result = []

        for bookmark in bookmarks[:self.max_top_articles]:
            doc = bookmark.document
            if not doc:
                continue

            # 分類から category を取得
            category = None
            if hasattr(doc, "classifications") and doc.classifications:
                for classification in doc.classifications:
                    category = getattr(classification, "primary_category", None)
                    if category:
                        break

            article = {
                "id": doc.id,
                "title": getattr(doc, "title", "無題"),
                "domain": self._get_domain(doc),
                "category": category,
                "tags": self._get_tags_list(doc),
                "summary": getattr(doc, "short_summary", None),
                "url": getattr(doc, "url", None),
                "bookmarked_at": bookmark.created_at.isoformat() if bookmark.created_at else None,
            }
            result.append(article)

        return result

    def _get_recent_bookmarks(
        self, bookmarks: List[Bookmark]
    ) -> List[Dict[str, any]]:
        """最近のブックマーク履歴を取得"""
        result = []

        for bookmark in bookmarks[:20]:  # 最新20件
            doc = bookmark.document
            if not doc:
                continue

            # 分類から category を取得
            category = None
            if hasattr(doc, "classifications") and doc.classifications:
                for classification in doc.classifications:
                    category = getattr(classification, "primary_category", None)
                    if category:
                        break

            item = {
                "id": doc.id,
                "title": getattr(doc, "title", "無題"),
                "bookmarked_at": bookmark.created_at.isoformat() if bookmark.created_at else None,
                "category": category,
                "url": getattr(doc, "url", None),
            }
            result.append(item)

        return result

    def _get_profile_info(
        self, db: Session, user_id: Optional[str]
    ) -> Dict[str, any]:
        """プロファイル情報を取得"""
        query = db.query(PreferenceProfile)

        if user_id is None:
            query = query.filter(PreferenceProfile.user_id.is_(None))
        else:
            query = query.filter(PreferenceProfile.user_id == user_id)

        profile = query.first()

        if not profile:
            return {}

        weights = {}

        # カテゴリ重みを取得
        if profile.category_weights:
            try:
                weights["categories"] = json.loads(profile.category_weights)
            except (json.JSONDecodeError, TypeError):
                weights["categories"] = {}

        # ドメイン重みを取得
        if profile.domain_weights:
            try:
                weights["domains"] = json.loads(profile.domain_weights)
            except (json.JSONDecodeError, TypeError):
                weights["domains"] = {}

        return {
            "status": getattr(profile, "status", "unknown"),
            "updated_at": profile.updated_at.isoformat() if profile.updated_at else None,
            "bookmark_count": getattr(profile, "bookmark_count", 0),
            "weights": weights,
        }

    def _get_domain(self, doc: Document) -> str:
        """ドキュメントからドメインを取得"""
        url = getattr(doc, "url", None)
        if not url:
            return "不明"

        try:
            parsed = urlparse(url)
            domain = parsed.netloc
            # www. を除去
            if domain.startswith("www."):
                domain = domain[4:]
            return domain or "不明"
        except Exception:
            return "不明"

    def _get_tags_list(self, doc: Document) -> List[str]:
        """ドキュメントからタグリストを取得"""
        # 分類からタグを取得
        if hasattr(doc, "classifications") and doc.classifications:
            for classification in doc.classifications:
                tags = getattr(classification, "tags", None)
                if tags and isinstance(tags, list):
                    return [str(t) for t in tags if t]

        return []

    def _empty_result(self) -> Dict[str, any]:
        """空の結果を返す"""
        return {
            "top_topics": [],
            "top_keywords": [],
            "top_articles": [],
            "recent_bookmarks": [],
            "summary": {
                "total_bookmarks": 0,
                "categories_count": 0,
                "unique_domains": 0,
                "profile_status": "no_data",
                "last_updated": None,
            },
            "profile_weights": {},
        }


__all__ = ["PreferenceAnalysisService"]
