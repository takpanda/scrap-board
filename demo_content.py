#!/usr/bin/env python3
"""
Scrap-Board コンテンツ取り込みデモンストレーション

このスクリプトは、外部LLMサービスなしでローカルのコンテンツ処理を実演します。
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.database import create_tables, SessionLocal, Document, Classification
from app.core.config import settings
import hashlib
from datetime import datetime

async def demo_content_ingestion():
    """サンプルコンテンツでデータベース取り込みをデモ"""
    
    print("🚀 Scrap-Board コンテンツ取り込みデモ")
    print("=" * 50)
    
    # データベース初期化
    print("📋 データベースを初期化中...")
    create_tables()
    
    # サンプルドキュメントデータ
    sample_documents = [
        {
            "title": "FastAPIによるWeb API開発の基礎",
            "content_md": """# FastAPIによるWeb API開発の基礎

FastAPIは、Pythonで高速なWeb APIを構築するためのモダンなフレームワークです。

## 主な特徴

- **高速**: Starlette と Pydantic をベースとした高パフォーマンス
- **型安全**: Python 3.6+ の型ヒントを活用
- **自動ドキュメント**: OpenAPI / JSON Schema 自動生成
- **標準準拠**: OpenAPI、JSON Schema標準に完全対応

## 基本的な使用例

```python
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
async def read_root():
    return {"Hello": "World"}
```

FastAPIを使用することで、開発者は効率的にAPIを構築できます。""",
            "domain": "python-docs.example",
            "category": "ソフトウェア開発",
            "tags": ["Python", "FastAPI", "Web API", "フレームワーク"]
        },
        {
            "title": "AI時代のコンテンツ管理システム設計",
            "content_md": """# AI時代のコンテンツ管理システム設計

現代のコンテンツ管理システムでは、AI技術の活用が重要になっています。

## AI活用のポイント

### 1. 自動分類
- 機械学習による文書カテゴリ分類
- 自然言語処理を活用したタグ付け
- ユーザーフィードバックによる精度向上

### 2. 検索の最適化  
- セマンティック検索の実装
- 埋め込みベクトルによる類似度計算
- ハイブリッド検索（全文検索 + ベクトル検索）

### 3. 要約生成
- 大規模言語モデル（LLM）による自動要約
- 複数の要約レベル（短/中/長）
- 重要箇所の自動抽出

## 実装アプローチ

AIを活用したCMSでは、従来の検索機能を大幅に改善できます。""",
            "domain": "tech-insights.example",
            "category": "テック/AI",
            "tags": ["AI", "CMS", "自然言語処理", "検索", "機械学習"]
        },
        {
            "title": "サイバーセキュリティの最新動向2024",
            "content_md": """# サイバーセキュリティの最新動向2024

2024年のサイバーセキュリティ業界では、新しい脅威と対策技術が登場しています。

## 主要な脅威トレンド

### ランサムウェアの進化
- ダブル恐喝攻撃の増加
- AIを活用した攻撃手法
- クラウドインフラを標的とした攻撃

### ゼロデイ攻撃
- 既知の脆弱性に対する迅速な悪用
- サプライチェーン攻撃の複雑化

## 対策技術

### ゼロトラストアーキテクチャ
- 境界防御から内部セキュリティへの転換
- 継続的な認証と認可
- マイクロセグメンテーション

### AI駆動セキュリティ
- 異常検知の精度向上
- 自動的な脅威対応
- 予測的セキュリティ分析

組織は包括的なセキュリティ戦略の構築が不可欠です。""",
            "domain": "security-today.example", 
            "category": "セキュリティ",
            "tags": ["サイバーセキュリティ", "ランサムウェア", "ゼロトラスト", "AI", "脅威"]
        }
    ]
    
    db = SessionLocal()
    try:
        print(f"📝 {len(sample_documents)} 件のサンプルドキュメントを追加中...")
        
        for i, doc_data in enumerate(sample_documents, 1):
            # ドキュメント作成
            content_text = doc_data["content_md"].replace("#", "").replace("*", "").replace("`", "")
            content_hash = hashlib.sha256(content_text.encode()).hexdigest()
            
            document = Document(
                title=doc_data["title"],
                domain=doc_data["domain"],
                content_md=doc_data["content_md"],
                content_text=content_text,
                hash=content_hash,
                lang="ja"
            )
            
            db.add(document)
            db.flush()  # IDを取得するため
            
            # 分類情報を追加
            classification = Classification(
                document_id=document.id,
                primary_category=doc_data["category"],
                tags=doc_data["tags"],
                confidence=0.9,
                method="demo"
            )
            
            db.add(classification)
            
            print(f"  ✅ {i}. {doc_data['title']} ({doc_data['category']})")
        
        db.commit()
        
        # 統計表示
        print("\n📊 データベース統計:")
        total_docs = db.query(Document).count()
        total_classifications = db.query(Classification).count()
        
        print(f"  📄 ドキュメント数: {total_docs}")
        print(f"  🏷️  分類数: {total_classifications}")
        
        # カテゴリ別統計
        print("\n📈 カテゴリ別統計:")
        from sqlalchemy import func
        category_stats = db.query(
            Classification.primary_category,
            func.count(Classification.id).label('count')
        ).group_by(Classification.primary_category).all()
        
        for category, count in category_stats:
            print(f"  • {category}: {count}件")
        
        print(f"\n🎉 デモデータの作成が完了しました！")
        print(f"🌐 アプリケーションを起動して http://localhost:8000 で確認してください")
        
    except Exception as e:
        db.rollback()
        print(f"❌ エラーが発生しました: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(demo_content_ingestion())