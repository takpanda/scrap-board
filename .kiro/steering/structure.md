# プロジェクト構造

## ルートディレクトリ構成

```
scrap-board/
├── app/                      # メインアプリケーションコード
├── tests/                    # テストコード
├── migrations/               # データベースマイグレーション
├── scripts/                  # ユーティリティスクリプト
├── data/                     # データベース・アップロード（Git管理外）
├── docs/                     # プロジェクトドキュメント
├── .kiro/                    # Kiro仕様駆動開発ファイル
│   └── steering/             # ステアリングドキュメント（本ファイル等）
├── .venv/                    # Python仮想環境（Git管理外）
├── requirements.txt          # Python依存関係
├── docker-compose.yml        # Docker構成
├── Dockerfile                # コンテナイメージ定義
├── .env.example              # 環境変数テンプレート
├── .env                      # 環境変数（Git管理外）
├── conftest.py               # pytest共通設定
├── playwright.config.py      # Playwright設定
├── README.md                 # プロジェクト概要
└── CLAUDE.md                 # Claude Code仕様駆動開発設定
```

## `app/` - メインアプリケーション

### 全体構成
```
app/
├── main.py                   # FastAPIアプリケーションエントリーポイント
├── core/                     # コア機能・設定
├── api/                      # HTTPエンドポイント定義
├── services/                 # ビジネスロジック・サービス層
├── templates/                # Jinja2 HTMLテンプレート
└── static/                   # 静的ファイル（CSS/JS）
```

### `app/core/` - コア機能
```
core/
├── config.py                 # 環境変数・設定管理（Pydantic Settings）
├── database.py               # データベース接続・セッション管理・テーブル定義
├── timezone.py               # 日付・タイムゾーン処理（JSTへの変換等）
└── user_utils.py             # ユーザー関連ユーティリティ（ゲストユーザー処理）
```

**責務**:
- アプリケーション全体で共有される設定・ユーティリティ
- データベースセッションライフサイクル管理
- SQLAlchemy モデル定義（`Document`, `Bookmark`, `Source`, `PostprocessJob`, `PersonalizationJob` 等）

### `app/api/` - API層
```
api/
├── __init__.py
└── routes/
    ├── documents.py          # ドキュメント一覧・詳細・検索
    ├── ingest.py             # URL/PDF取り込みエンドポイント
    ├── bookmarks.py          # ブックマーク機能
    ├── bookmarks_only.py     # ブックマーク専用ページ
    ├── preferences.py        # 嗜好プロファイル・統計
    ├── collections.py        # コレクション管理
    ├── admin.py              # 管理機能（エクスポート等）
    ├── admin_sources.py      # ソース管理（RSS等）
    └── utils.py              # API共通ユーティリティ
```

**責務**:
- HTTPリクエスト受信・レスポンス返却
- リクエストバリデーション（Pydanticモデル）
- サービス層呼び出し・ビジネスロジック委譲
- テンプレートレンダリング（HTMX対応）

### `app/services/` - サービス層
```
services/
├── extractor.py              # HTML/PDFコンテンツ抽出
├── speakerdeck_handler.py    # SpeakerDeck特化処理
├── llm_client.py             # LLM API統合（要約・埋め込み）
├── similarity.py             # 類似検索・ベクトル計算
├── postprocess.py            # ポストプロセス（要約・埋め込み生成）
├── postprocess_queue.py      # ポストプロセスワーカー
├── ingest_worker.py          # 取り込みワーカー
├── scheduler.py              # スケジューラ（RSS定期取得）
├── bookmark_service.py       # ブックマーク操作
├── preference_analysis.py    # 嗜好分析（統計・可視化）
├── preference_profile.py     # 嗜好プロファイル構築
├── personalized_ranking.py   # パーソナライズランキング
├── personalized_repository.py # パーソナライズデータリポジトリ
├── personalized_feedback.py  # フィードバック反映処理
├── personalization_models.py # パーソナライゼーションモデル
├── personalization_worker.py # パーソナライゼーションワーカー
└── personalization_queue.py  # パーソナライゼーションジョブキュー
```

**責務**:
- ビジネスロジック実装
- 外部サービス統合（LLM API、PDF抽出等）
- バックグラウンド処理（ワーカー）
- データアクセス・永続化（直接DBセッション利用）

### `app/templates/` - Jinja2テンプレート
```
templates/
├── base.html                 # ベーステンプレート（共通レイアウト）
├── index.html                # トップページ
├── documents.html            # ドキュメント一覧
├── document_detail.html      # ドキュメント詳細
├── bookmarks_only.html       # ブックマーク専用ページ
├── preferences.html          # 嗜好分析ページ
├── reader.html               # Reader Mode表示
├── admin/                    # 管理画面テンプレート
│   ├── export.html
│   ├── sources.html
│   └── admin_postprocess.html
└── partials/                 # 部分テンプレート（再利用可能コンポーネント）
    ├── document_card.html
    └── pagination.html
```

**責務**:
- HTML生成
- HTMX属性によるインタラクション定義
- Tailwind CSSクラスによるスタイリング

### `app/static/` - 静的ファイル
```
static/
├── css/
│   └── style.css             # カスタムCSS（Tailwind補完）
└── js/
    ├── htmx-minimal.js       # HTMX拡張
    ├── markdown-preview.js   # マークダウンプレビュー
    ├── personalized-sort.js  # パーソナライズソートUI
    └── icons.js              # アイコン表示ヘルパー
```

**責務**:
- フロントエンド補助スクリプト
- カスタムスタイル定義

## `tests/` - テストコード

### 構成
```
tests/
├── conftest.py               # pytest fixture定義（親ディレクトリの conftest.py を参照）
├── test_basic.py             # 基本機能テスト
├── test_postprocess.py       # ポストプロセステスト
├── test_ingest_*.py          # 取り込み機能テスト
├── test_bookmark*.py         # ブックマーク機能テスト
├── test_personalized_*.py    # パーソナライゼーション機能テスト
├── test_preference_*.py      # 嗜好分析テスト
├── test_*_ui.py              # UI/E2Eテスト（Playwright）
└── test_speakerdeck_handler.py # SpeakerDeck処理テスト
```

**テスト方針**:
- **ユニットテスト**: サービス層ロジックのモックテスト
- **統合テスト**: DB接続・API呼び出しを含むテスト
- **E2Eテスト**: Playwrightによるブラウザテスト

## `migrations/` - マイグレーション

### 構成
```
migrations/
├── apply_migrations.py       # 一括マイグレーション適用スクリプト
├── migrate_null_to_guest.py  # ゲストユーザー統一マイグレーション
├── 001_add_summaries_to_documents.sql
└── 002_add_sources_and_thumbnails.sql
```

**運用方針**:
- **開発環境**: 簡易スクリプトによる手動適用
- **本番環境**: Alembic導入を推奨（将来的な改善）
- **バックアップ必須**: 適用前に必ずDBバックアップ

## `scripts/` - ユーティリティスクリプト

### 主要スクリプト
```
scripts/
├── test_postprocess.py       # ポストプロセス手動テスト
├── run_preference_worker*.py # 嗜好プロファイルワーカー起動
├── sanitize_dates.py         # 日付データクリーンアップ
└── check_personalized_*.py   # パーソナライゼーションE2E確認
```

**用途**:
- 手動テスト・デバッグ
- データメンテナンス
- ワーカー起動ヘルパー

## `docs/` - ドキュメント

### 主要ドキュメント
```
docs/
├── tech.md                   # 技術方針（このファイルと重複、統合検討）
├── product.md                # プロダクトビジョン（このファイルと重複、統合検討）
├── structure.md              # コードベース構造（このファイルと重複、統合検討）
├── personalized-ranking.md   # パーソナライズ仕様
├── guest-user-specification.md # ゲストユーザー仕様
├── postprocessing.md         # ポストプロセス仕様
└── DEVELOPMENT.md            # 開発ガイド
```

**注意**: `.kiro/steering/` と `docs/` に類似ドキュメントが存在する場合、将来的に統合または参照関係を明確化する必要があります。

## `data/` - データ保存（Git管理外）

### 構成
```
data/
├── scraps.db                 # SQLiteデータベース
├── uploads/                  # アップロードPDFファイル
├── assets/                   # サムネイル等の静的アセット
└── backup/                   # バックアップ（手動作成）
```

**注意**:
- `.gitignore` で除外
- バックアップは定期的に手動作成を推奨

## コード組織パターン

### レイヤー分離
1. **API層** (`app/api/routes/`): HTTPエンドポイント定義のみ
2. **サービス層** (`app/services/`): ビジネスロジック実装
3. **データアクセス層** (`app/core/database.py`): SQLAlchemyモデル定義

### 依存関係ルール
- **API → サービス**: APIはサービスを呼び出す（逆は禁止）
- **サービス → コア**: サービスはコア機能を利用
- **サービス間**: 直接呼び出し可（循環依存に注意）

### 非同期処理
- **FastAPI**: 基本的に `async def` でエンドポイント定義
- **バックグラウンドジョブ**: DBキューベース（`postprocess_jobs`, `personalization_jobs`）
- **スケジューラ**: APScheduler（`app/services/scheduler.py`）

## ファイル命名規則

### Pythonモジュール
- **小文字スネークケース**: `preference_analysis.py`, `llm_client.py`
- **テストファイル**: `test_<機能名>.py` （例: `test_postprocess.py`）

### テンプレート
- **小文字スネークケース**: `document_detail.html`, `bookmarks.html`
- **コンポーネント**: `components/<コンポーネント名>.html`

### 静的ファイル
- **ハイフンケース**: `markdown-preview.js`, `personalized-sort.js`

## インポート組織

### 標準的なインポート順序
```python
# 1. 標準ライブラリ
import os
from datetime import datetime

# 2. サードパーティライブラリ
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

# 3. ローカルモジュール（app内）
from app.core.config import settings
from app.core.database import get_db, Document
from app.services.llm_client import llm_client
```

### 相対インポートの使用
- **同一パッケージ内**: 相対インポート可 (例: `from .utils import helper`)
- **異なるパッケージ**: 絶対インポート推奨 (例: `from app.services.extractor import extract_content`)

## 主要アーキテクチャ原則

### 単一責任の原則
- 各モジュールは単一の明確な責務を持つ
- 例: `extractor.py` はコンテンツ抽出のみ、`llm_client.py` はLLM API呼び出しのみ

### 依存性注入
- `get_db()` による DBセッション注入
- 設定は `app.core.config.settings` から取得

### テスタビリティ優先
- モック可能な設計（依存性注入）
- テストフィクスチャ活用（`conftest.py`）

### ドメイン駆動設計の要素
- **エンティティ**: `Document`, `Bookmark`, `Source` 等のSQLAlchemyモデル
- **サービス**: `app/services/` 配下のビジネスロジック
- **リポジトリ**: `personalized_repository.py` 等のデータアクセス抽象化

### HTMX中心のUI設計
- **サーバーサイドレンダリング**: Jinja2でHTML生成
- **部分更新**: HTMX属性（`hx-get`, `hx-post`, `hx-target`）で動的インタラクション
- **最小JavaScript**: フレームワーク依存なし、必要最小限のスクリプトのみ
