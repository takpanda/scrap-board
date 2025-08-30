from sqlalchemy import create_engine, Column, String, Text, DateTime, Integer, Float, Boolean, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from sqlalchemy.sql import func
from typing import Generator
import uuid

from app.core.config import settings

# データベースエンジン
engine = create_engine(
    settings.db_url,
    connect_args={"check_same_thread": False} if "sqlite" in settings.db_url else {}
)

# セッションメーカー
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# ベースクラス
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """データベースセッションを取得"""
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
    hash = Column(String, nullable=False, index=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # リレーション
    classifications = relationship("Classification", back_populates="document", cascade="all, delete-orphan")
    embeddings = relationship("Embedding", back_populates="document", cascade="all, delete-orphan")
    collection_items = relationship("CollectionItem", back_populates="document", cascade="all, delete-orphan")
    feedbacks = relationship("Feedback", back_populates="document", cascade="all, delete-orphan")


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


def create_tables():
    """データベーステーブルを作成"""
    Base.metadata.create_all(bind=engine)