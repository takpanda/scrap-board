"""
類似度計算サービス
"""
import json
import numpy as np
from typing import List, Tuple, Optional
from sqlalchemy.orm import Session
from app.core.database import Document, Embedding
import logging

logger = logging.getLogger(__name__)


def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """
    コサイン類似度を計算
    
    Args:
        vec1: 第1のベクトル
        vec2: 第2のベクトル
        
    Returns:
        0.0から1.0の間のコサイン類似度スコア
    """
    try:
        # NumPy配列に変換
        a = np.array(vec1)
        b = np.array(vec2)
        
        # コサイン類似度計算
        dot_product = np.dot(a, b)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        
        if norm_a == 0 or norm_b == 0:
            return 0.0
            
        similarity = dot_product / (norm_a * norm_b)
        
        # -1から1の範囲を0から1に正規化
        return float((similarity + 1) / 2)
        
    except Exception as e:
        logger.error(f"Error calculating cosine similarity: {e}")
        return 0.0


def calculate_document_similarity(
    document_id: str,
    other_documents: List[Document],
    db: Session
) -> List[Tuple[Document, float]]:
    """
    指定されたドキュメントと他のドキュメントとの類似度を計算
    
    Args:
        document_id: 基準となるドキュメントのID
        other_documents: 比較対象のドキュメントリスト
        db: データベースセッション
        
    Returns:
        (ドキュメント, 類似度スコア)のタプルのリスト
    """
    try:
        # 基準ドキュメントの埋め込みを取得
        base_embedding = db.query(Embedding).filter(
            Embedding.document_id == document_id
        ).first()
        
        if not base_embedding:
            logger.warning(f"No embedding found for document {document_id}")
            # 埋め込みがない場合は、すべて低い類似度で返す
            return [(doc, 0.1) for doc in other_documents]
        
        base_vec = json.loads(base_embedding.vec)
        results = []
        
        for doc in other_documents:
            # 比較対象ドキュメントの埋め込みを取得
            doc_embedding = db.query(Embedding).filter(
                Embedding.document_id == doc.id
            ).first()
            
            if doc_embedding:
                doc_vec = json.loads(doc_embedding.vec)
                similarity = cosine_similarity(base_vec, doc_vec)
            else:
                # 埋め込みがない場合は低い類似度
                similarity = 0.1
            
            results.append((doc, similarity))
        
        # 類似度で降順ソート
        results.sort(key=lambda x: x[1], reverse=True)
        return results
        
    except Exception as e:
        logger.error(f"Error calculating document similarity: {e}")
        # エラー時は全て低い類似度で返す
        return [(doc, 0.1) for doc in other_documents]