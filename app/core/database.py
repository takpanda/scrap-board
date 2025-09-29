from sqlalchemy import (
    create_engine,
    Column,
    String,
    Text,
    DateTime,
    Integer,
    Float,
    Boolean,
    ForeignKey,
    JSON,
    Index,
    UniqueConstraint,
    CheckConstraint,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from sqlalchemy.sql import func
from typing import Generator
import uuid

from app.core.config import settings
import os

# データベースエンジン
engine = create_engine(
    settings.db_url,
    connect_args={"check_same_thread": False} if "sqlite" in settings.db_url else {}
)

# セッションメーカー
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# ベースクラス
Base = declarative_base()

# Keep track of engines we've ensured tables for (avoid repeated create_all calls)
def get_db() -> Generator[Session, None, None]:
    """データベースセッションを取得"""
    # Ensure we operate on the sessionmaker/engine that tests may have set up.
    # If SessionLocal already has a bound engine, use that. Otherwise create
    # an engine from the active DB URL (env override preferred) and bind
    # a new SessionLocal to it.
    global SessionLocal, engine
    bound_engine = getattr(SessionLocal, "bind", None)
    # If there's no bound engine, or the bound engine uses a different
    # DB URL than the one in the environment, recreate the engine so
    # tests that set `DB_URL` at runtime are respected.
    db_url = os.environ.get("DB_URL") or settings.db_url
    current_engine_url = None
    try:
        if bound_engine is not None and hasattr(bound_engine, 'url'):
            current_engine_url = str(bound_engine.url)
    except Exception:
        current_engine_url = None

    if bound_engine is None or (db_url and current_engine_url and db_url != current_engine_url) or (bound_engine is not None and current_engine_url is None):
        # prefer env var so pytest_configure/test fixtures can control DB
        db_url = os.environ.get("DB_URL") or settings.db_url
        try:
            from sqlalchemy import create_engine as _create_engine

            new_engine = _create_engine(
                db_url,
                connect_args={"check_same_thread": False} if "sqlite" in db_url else {},
            )
            engine = new_engine
            SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=new_engine)
            bound_engine = new_engine
        except Exception:
            # fall back to existing module-level engine if creation fails
            bound_engine = globals().get("engine")

    # Ensure tables exist on the bound engine before creating sessions.
    try:
        if bound_engine is not None:
            # If the bound engine does not have the core tables (e.g. documents),
            # recreate an engine bound to the current DB URL so tests that
            # swap DBs at runtime are respected.
            try:
                # Quick check for documents table presence (SQLite specific path)
                conn = bound_engine.connect()
                try:
                    res = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='documents'")
                    has_documents = bool(res.fetchall())
                except Exception:
                    # If the inspection query fails (non-sqlite dialect), fall back
                    has_documents = True
                finally:
                    conn.close()
            except Exception:
                has_documents = False

            if not has_documents:
                # Recreate engine from env DB URL so it points to the DB with tables
                try:
                    db_url = os.environ.get("DB_URL") or settings.db_url
                    from sqlalchemy import create_engine as _create_engine

                    new_engine = _create_engine(db_url, connect_args={"check_same_thread": False} if "sqlite" in db_url else {})
                    engine = new_engine
                    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=new_engine)
                    bound_engine = new_engine
                except Exception:
                    pass

            # Ensure tables exist on the (new) bound engine before creating sessions.
            try:
                Base.metadata.create_all(bind=bound_engine)
            except Exception:
                pass
    except Exception:
        # best-effort only
        pass

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# データベースモデル定義

class Document(Base):
    """ドキュメントテーブル"""
    __tablename__ = "documents"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    url = Column(String, unique=True, nullable=True, index=True)
    domain = Column(String, nullable=True, index=True)
    title = Column(String, nullable=False)
    author = Column(String, nullable=True)
    published_at = Column(DateTime, nullable=True)
    fetched_at = Column(DateTime, default=func.now())
    lang = Column(String, nullable=True)
    content_md = Column(Text, nullable=False)
    content_text = Column(Text, nullable=False)
    short_summary = Column(Text, nullable=True)
    medium_summary = Column(Text, nullable=True)
    summary_generated_at = Column(DateTime, nullable=True)
    summary_model = Column(String, nullable=True)
    source = Column(String, nullable=True)
    original_url = Column(String, nullable=True)
    thumbnail_url = Column(String, nullable=True)
    fetched_at = Column(DateTime, nullable=True)
    hash = Column(String, nullable=False, index=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # リレーション
    classifications = relationship("Classification", back_populates="document", cascade="all, delete-orphan")
    embeddings = relationship("Embedding", back_populates="document", cascade="all, delete-orphan")
    collection_items = relationship("CollectionItem", back_populates="document", cascade="all, delete-orphan")
    feedbacks = relationship("Feedback", back_populates="document", cascade="all, delete-orphan")
    # ブックマークのリレーション
    bookmarks = relationship("Bookmark", back_populates="document", cascade="all, delete-orphan")
    personalized_scores = relationship(
        "PersonalizedScore",
        back_populates="document",
        cascade="all, delete-orphan",
    )
    preference_feedbacks = relationship(
        "PreferenceFeedback",
        back_populates="document",
        cascade="all, delete-orphan",
    )
    preference_jobs = relationship(
        "PreferenceJob",
        back_populates="document",
        passive_deletes=True,
    )


class Classification(Base):
    """分類テーブル"""
    __tablename__ = "classifications"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(String, ForeignKey("documents.id"), nullable=False)
    primary_category = Column(String, nullable=False)
    topics = Column(JSON, nullable=True)  # JSONB for topics list
    tags = Column(JSON, nullable=True)    # JSONB for tags list  
    confidence = Column(Float, nullable=False)
    method = Column(String, nullable=False)  # prompt|rules|knn
    created_at = Column(DateTime, default=func.now())
    
    # リレーション
    document = relationship("Document", back_populates="classifications")


class Embedding(Base):
    """埋め込みテーブル"""
    __tablename__ = "embeddings"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(String, ForeignKey("documents.id"), nullable=False)
    chunk_id = Column(Integer, nullable=False)
    vec = Column(Text, nullable=False)  # JSON encoded vector
    chunk_text = Column(Text, nullable=False)
    created_at = Column(DateTime, default=func.now())
    
    # リレーション
    document = relationship("Document", back_populates="embeddings")


class Collection(Base):
    """コレクションテーブル"""
    __tablename__ = "collections"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # リレーション
    items = relationship("CollectionItem", back_populates="collection", cascade="all, delete-orphan")


class CollectionItem(Base):
    """コレクションアイテムテーブル"""
    __tablename__ = "collection_items"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    collection_id = Column(String, ForeignKey("collections.id"), nullable=False)
    document_id = Column(String, ForeignKey("documents.id"), nullable=False)
    note = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.now())
    
    # リレーション
    collection = relationship("Collection", back_populates="items")
    document = relationship("Document", back_populates="collection_items")


class Feedback(Base):
    """フィードバックテーブル"""
    __tablename__ = "feedbacks"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(String, ForeignKey("documents.id"), nullable=False)
    label = Column(String, nullable=False)  # correct|incorrect
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.now())
    
    # リレーション
    document = relationship("Document", back_populates="feedbacks")


class PostprocessJob(Base):
    """ポストプロセス用ジョブテーブル

    スキーマ:
    - document_id: 対象ドキュメント
    - status: pending|in_progress|failed|done
    - attempts: 試行回数
    - max_attempts: 最大試行回数
    - last_error: 直近のエラーメッセージ
    - next_attempt_at: 次回試行予定時刻
    """
    __tablename__ = "postprocess_jobs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(String, nullable=False, index=True)
    status = Column(String, nullable=False, default="pending", index=True)
    attempts = Column(Integer, nullable=False, default=0)
    max_attempts = Column(Integer, nullable=False, default=5)
    last_error = Column(Text, nullable=True)
    next_attempt_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


def create_tables():
    """データベーステーブルを作成"""
    # Create missing tables/columns for development/testing environments.
    # Use the DB URL from the environment (if set) so pytest-configured DBs
    # are respected even if `settings` was initialized earlier.
    try:
        db_url = os.environ.get("DB_URL") or settings.db_url
        from sqlalchemy import create_engine as _create_engine

        create_engine_kwargs = {"connect_args": {"check_same_thread": False}} if "sqlite" in db_url else {}
        local_engine = _create_engine(db_url, **create_engine_kwargs)
        Base.metadata.create_all(bind=local_engine)
        # Rebind module-level engine and SessionLocal so code using
        # `SessionLocal()` picks up the test DB when tests set `DB_URL`.
        try:
            globals()["engine"] = local_engine
            globals()["SessionLocal"] = sessionmaker(autocommit=False, autoflush=False, bind=local_engine)
        except Exception:
            # if rebind fails, continue — the tables at least exist on local_engine
            pass
    except Exception:
        # best-effort fallback to module-level engine
        try:
            Base.metadata.create_all(bind=engine)
        except Exception:
            pass

    # If using SQLite, ensure new summary columns exist on prebuilt DB files.
    # Some test databases are committed to the repo and may lack the new columns.
    try:
        from urllib.parse import urlparse
        import sqlite3
        from app.core.config import settings

        if settings.db_url.startswith("sqlite"):
            # Extract path from sqlite URL like sqlite:///./test.db
            db_path = settings.db_url.replace("sqlite:///", "")
            if db_path and os.path.exists(db_path):
                conn = sqlite3.connect(db_path)
                cur = conn.cursor()
                cur.execute("PRAGMA table_info(documents);")
                existing_cols = {r[1] for r in cur.fetchall()} if cur else set()

                needed = [
                    ("short_summary", "TEXT"),
                    ("medium_summary", "TEXT"),
                    ("summary_generated_at", "TEXT"),
                    ("summary_model", "TEXT"),
                    ("source", "TEXT"),
                    ("original_url", "TEXT"),
                    ("thumbnail_url", "TEXT"),
                    ("fetched_at", "TEXT"),
                ]

                for col, coltype in needed:
                    if col not in existing_cols:
                        cur.execute(f"ALTER TABLE documents ADD COLUMN {col} {coltype};")
                conn.commit()
                conn.close()
    except Exception:
        # Best-effort only — don't fail application start if migration step cannot run.
        pass


# Bookmark model
class Bookmark(Base):
    """ブックマーク（ユーザー保存）"""
    __tablename__ = "bookmarks"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=True, index=True)
    document_id = Column(String, ForeignKey("documents.id"), nullable=False, index=True)
    note = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.now())

    # リレーション
    document = relationship("Document", back_populates="bookmarks")


class PreferenceProfile(Base):
    """ユーザー嗜好プロファイル"""

    __tablename__ = "preference_profiles"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=True, index=True)
    bookmark_count = Column(Integer, nullable=False, default=0)
    profile_embedding = Column(Text, nullable=True)
    category_weights = Column(Text, nullable=True)
    domain_weights = Column(Text, nullable=True)
    last_bookmark_id = Column(String, nullable=True)
    status = Column(String, nullable=False, default="ready", index=True)
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())

    personalized_scores = relationship(
        "PersonalizedScore",
        back_populates="profile",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index(
            "idx_preference_profiles_user",
            user_id,
            unique=True,
            sqlite_where=user_id.isnot(None),
        ),
        Index("idx_preference_profiles_updated_at", "updated_at"),
    )


class PersonalizedScore(Base):
    """パーソナライズされたスコア"""

    __tablename__ = "personalized_scores"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    profile_id = Column(
        String,
        ForeignKey("preference_profiles.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    user_id = Column(String, nullable=True, index=True)
    document_id = Column(
        String,
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    score = Column(Float, nullable=False)
    rank = Column(Integer, nullable=False)
    components = Column(Text, nullable=True)
    explanation = Column(Text, nullable=True)
    computed_at = Column(DateTime, nullable=False, default=func.now())
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())

    profile = relationship("PreferenceProfile", back_populates="personalized_scores")
    document = relationship("Document", back_populates="personalized_scores")

    __table_args__ = (
        CheckConstraint("score >= 0.0 AND score <= 1.0", name="ck_personalized_scores_score_range"),
        CheckConstraint("rank >= 1", name="ck_personalized_scores_rank_positive"),
        Index("idx_personalized_scores_user_document", "user_id", "document_id", unique=True),
        Index("idx_personalized_scores_document", "document_id"),
        Index("idx_personalized_scores_score", "score"),
    )


class PreferenceJob(Base):
    """嗜好プロファイル再計算ジョブ"""

    __tablename__ = "preference_jobs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=True, index=True)
    document_id = Column(
        String,
        ForeignKey("documents.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    job_type = Column(String, nullable=False, default="profile_rebuild", index=True)
    status = Column(String, nullable=False, default="pending", index=True)
    attempts = Column(Integer, nullable=False, default=0)
    max_attempts = Column(Integer, nullable=False, default=3)
    last_error = Column(Text, nullable=True)
    next_attempt_at = Column(DateTime, nullable=True)
    scheduled_at = Column(DateTime, nullable=True, default=func.now())
    created_at = Column(DateTime, nullable=True, default=func.now())
    updated_at = Column(DateTime, nullable=True, default=func.now(), onupdate=func.now())
    payload = Column(Text, nullable=True)

    document = relationship("Document", back_populates="preference_jobs")

    __table_args__ = (
        Index("idx_preference_jobs_status", "status"),
        Index("idx_preference_jobs_next_attempt", "next_attempt_at"),
        Index("idx_preference_jobs_job_type", "job_type"),
    )


class PreferenceFeedback(Base):
    """パーソナライズフィードバック"""

    __tablename__ = "preference_feedbacks"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=True, index=True)
    document_id = Column(
        String,
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    feedback_type = Column(String, nullable=False)
    metadata_payload = Column("metadata", Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=func.now())

    document = relationship("Document", back_populates="preference_feedbacks")

    __table_args__ = (
        Index("idx_preference_feedbacks_document", "document_id"),
        Index("idx_preference_feedbacks_user", "user_id"),
        Index("idx_preference_feedbacks_created_at", "created_at"),
        UniqueConstraint(
            "user_id",
            "document_id",
            "feedback_type",
            name="idx_preference_feedbacks_unique_submission",
        ),
    )