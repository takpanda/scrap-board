# ER Diagram

以下は現在のデータベーススキーマに基づくER図です。

```mermaid
erDiagram
    DOCUMENTS {
        VARCHAR id PK
        VARCHAR url
        VARCHAR domain
        VARCHAR title
        VARCHAR author
        DATETIME published_at
        DATETIME fetched_at
        VARCHAR lang
        TEXT content_md
        TEXT content_text
        VARCHAR hash
        DATETIME created_at
        DATETIME updated_at
        TEXT short_summary
        TEXT medium_summary
        DATETIME summary_generated_at
        VARCHAR summary_model
        VARCHAR source
        VARCHAR original_url
        VARCHAR thumbnail_url
    }

    CLASSIFICATIONS {
        VARCHAR id PK
        VARCHAR document_id FK
        VARCHAR primary_category
        JSON topics
        JSON tags
        FLOAT confidence
        VARCHAR method
        DATETIME created_at
    }

    EMBEDDINGS {
        VARCHAR id PK
        VARCHAR document_id FK
        INTEGER chunk_id
        TEXT vec
        TEXT chunk_text
        DATETIME created_at
    }

    COLLECTIONS {
        VARCHAR id PK
        VARCHAR name
        TEXT description
        DATETIME created_at
        DATETIME updated_at
    }

    COLLECTION_ITEMS {
        VARCHAR id PK
        VARCHAR collection_id FK
        VARCHAR document_id FK
        TEXT note
        DATETIME created_at
    }

    FEEDBACKS {
        VARCHAR id PK
        VARCHAR document_id FK
        VARCHAR label
        TEXT comment
        DATETIME created_at
    }

    SOURCES {
        INTEGER id PK
        VARCHAR name
        VARCHAR type
        TEXT config
        INTEGER enabled
        VARCHAR cron_schedule
        DATETIME last_fetched_at
    }

    POSTPROCESS_JOBS {
        VARCHAR id PK
        VARCHAR document_id
        VARCHAR status
        INTEGER attempts
        INTEGER max_attempts
        TEXT last_error
        DATETIME next_attempt_at
        DATETIME created_at
        DATETIME updated_at
    }

    BOOKMARKS {
        VARCHAR id PK
        VARCHAR user_id
        VARCHAR document_id FK
        TEXT note
        DATETIME created_at
    }

    PREFERENCE_PROFILES {
        VARCHAR id PK
        VARCHAR user_id
        INTEGER bookmark_count
        TEXT profile_embedding
        TEXT category_weights
        TEXT domain_weights
        VARCHAR last_bookmark_id
        VARCHAR status
        DATETIME created_at
        DATETIME updated_at
    }

    PERSONALIZED_SCORES {
        VARCHAR id PK
        VARCHAR profile_id FK
        VARCHAR user_id
        VARCHAR document_id FK
        FLOAT score
        INTEGER rank
        TEXT components
        TEXT explanation
        DATETIME computed_at
        DATETIME created_at
        DATETIME updated_at
    }

    PREFERENCE_JOBS {
        VARCHAR id PK
        VARCHAR user_id
        VARCHAR document_id FK
        VARCHAR job_type
        VARCHAR status
        INTEGER attempts
        INTEGER max_attempts
        TEXT last_error
        DATETIME next_attempt_at
        DATETIME scheduled_at
        DATETIME created_at
        DATETIME updated_at
        TEXT payload
    }

    PREFERENCE_FEEDBACKS {
        VARCHAR id PK
        VARCHAR user_id
        VARCHAR document_id FK
        VARCHAR feedback_type
        TEXT metadata
        DATETIME created_at
    }

    DOCUMENTS ||--o{ CLASSIFICATIONS : "has"
    DOCUMENTS ||--o{ EMBEDDINGS : "has"
    DOCUMENTS ||--o{ COLLECTION_ITEMS : "referenced_by"
    DOCUMENTS ||--o{ FEEDBACKS : "has"
    DOCUMENTS ||--o{ BOOKMARKS : "has"
    DOCUMENTS ||--o{ PERSONALIZED_SCORES : "has"
    DOCUMENTS ||--o{ PREFERENCE_JOBS : "has"
    DOCUMENTS ||--o{ PREFERENCE_FEEDBACKS : "has"
    COLLECTIONS ||--o{ COLLECTION_ITEMS : "contains"
    PREFERENCE_PROFILES ||--o{ PERSONALIZED_SCORES : "has"
    CLASSIFICATIONS }o--|| DOCUMENTS : "belongs_to"
    EMBEDDINGS }o--|| DOCUMENTS : "belongs_to"
    COLLECTION_ITEMS }o--|| COLLECTIONS : "belongs_to"
    COLLECTION_ITEMS }o--|| DOCUMENTS : "belongs_to"
    FEEDBACKS }o--|| DOCUMENTS : "belongs_to"
    BOOKMARKS }o--|| DOCUMENTS : "belongs_to"
    PERSONALIZED_SCORES }o--|| DOCUMENTS : "belongs_to"
    PERSONALIZED_SCORES }o--|| PREFERENCE_PROFILES : "belongs_to"
    PREFERENCE_JOBS }o--|| DOCUMENTS : "belongs_to"
    PREFERENCE_FEEDBACKS }o--|| DOCUMENTS : "belongs_to"

``` 

## 注記

### データ型について
- `tags` と `topics` はJSON型で保存されます（Postgresでは配列型/JSONBの想定）。
- `vec` は埋め込みベクトルをJSON形式でエンコードして保存します。
- `profile_embedding`, `category_weights`, `domain_weights`, `components`, `explanation`, `metadata` はJSON文字列として保存されます。

### マイグレーション履歴
- **マイグレーション 003**: `sources` テーブルと `documents` テーブルへの `source`, `original_url`, `thumbnail_url`, `fetched_at` カラムの追加
- **マイグレーション 004**: `postprocess_jobs` テーブルの作成（ポストプロセスジョブ管理）
- **マイグレーション 005**: `bookmarks` テーブルの作成（ユーザーブックマーク機能）
- **マイグレーション 006**: パーソナライゼーション関連テーブルの作成
  - `preference_profiles`: ユーザー嗜好プロファイル
  - `personalized_scores`: パーソナライズされたドキュメントスコア
  - `preference_jobs`: 嗜好プロファイル再計算ジョブ
  - `preference_feedbacks`: パーソナライズフィードバック

### テーブル説明

#### コアテーブル
- **documents**: 収集したウェブコンテンツやPDFの本文・メタデータを保存
- **classifications**: ドキュメントの分類情報（カテゴリ、トピック、タグ）
- **embeddings**: ドキュメントの埋め込みベクトル（検索・類似度計算用）
- **sources**: RSS フィードや外部APIなどのコンテンツソース定義

#### コレクション管理
- **collections**: ユーザーが作成するドキュメントのグループ
- **collection_items**: コレクションとドキュメントの中間テーブル
- **feedbacks**: 分類結果に対するユーザーフィードバック

#### ジョブ管理
- **postprocess_jobs**: バックグラウンドでの要約生成や分類処理のジョブキュー

#### パーソナライゼーション機能
- **bookmarks**: ユーザーがブックマークしたドキュメント
- **preference_profiles**: ユーザーごとの嗜好プロファイル（ブックマーク履歴から生成）
- **personalized_scores**: ドキュメントのパーソナライズスコア（推薦順位付け用）
- **preference_jobs**: 嗜好プロファイルの再計算ジョブ
- **preference_feedbacks**: パーソナライズ結果に対するユーザーフィードバック

