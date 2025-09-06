# Codebase Structure (structure.md)

## 目的
このドキュメントは `Scrap-Board` のリポジトリ構造と各ディレクトリ／主要ファイルの責務を明確にし、新規開発者が素早くプロジェクトに参画できるようにするためのガイドです。

## 高レベル構造
リポジトリはシンプルなモノリポジトリ構成を想定します。主要ディレクトリ:

- `app/` - アプリケーション本体
  - `main.py` - FastAPI のアプリエントリ
  - `core/` - 設定、DB接続、共通ユーティリティ
    - `config.py` - 環境変数読み取りと設定
    - `database.py` - SQLite 接続ラッパ
  - `services/` - ビジネスロジック、外部サービスのクライアント
    - `extractor.py` - HTML/PDF抽出ロジック
    - `llm_client.py` - LM Studio/Ollama 抽象クライアント
    - `similarity.py` - 埋め込み生成と類似度計算
  - `api/routes/` - HTTP エンドポイント（ルーティング）
    - `ingest.py`, `documents.py`, `collections.py` など
  - `templates/` - Jinja2 テンプレート
  - `static/` - CSS/JS/画像などの静的資産
- `tests/` - ユニットテスト・統合テスト（pytest 用）
- `data/` - 実行時のローカルデータ（DB、アセット）
- `.spec-workflow/` - 仕様ワークフローのドラフト (steering docs など)
- ドキュメント/設定: `README.md`, `DEVELOPMENT.md`, `requirements.txt`, `docker-compose.yml` など

## モジュール責務
- `core` はインフラ的責務のみを持ち、アプリ固有ロジックを含めない。
- `services` は副作用があり得る処理（外部API呼び出し、ファイルIO、重い計算）を担当。
- `api/routes` はリクエスト/レスポンスの整形とバリデーションに専念し、ビジネスロジックは `services` を呼ぶだけにする。
- `templates`/`static` は UI レンダリング専用。テンプレートでのロジックは最小にする。

## ファイル命名と公共API
- モジュール名は snake_case、クラスは PascalCase。
- 公開関数はドキュメンテーション文字列（docstring）を必須にする。
- 設定キーや環境変数は `UPPER_SNAKE_CASE` を使用。

## テスト構成
- 主要なユニットテストは `tests/unit/`、統合テストは `tests/integration/` に分ける。
- Playwright やブラウザ系テストは `tests/e2e/` または `tests/browser/` に配備。
- テストは CI で自動実行。ローカルでは `pytest -q` を推奨。

## CI / Linting / 型チェック
- CI ワークフローで以下を実行:
  - `pytest`（テスト）
  - `black --check`（フォーマットチェック）
  - `flake8`（静的解析）
  - `mypy`（型チェック、可能な範囲で）

## マイグレーション
- 初期は SQLite を使用。将来的な DB 変更を見据え、DB アクセスは薄い抽象層を通して行う。
- Alembic の導入を推奨。マイグレーションファイルは `alembic/` に配置。

## ドキュメントとオンボーディング
- `DEVELOPMENT.md` にローカル起動、依存インストール、LLM のセットアップ手順を必ず記載。
- 新規開発者向けチェックリストを `CONTRIBUTING.md` に置く（環境変数、シードデータ、テスト実行など）。

## デプロイ / ローカル実行
- 単一コンテナ設計を保持。`Dockerfile` と `docker-compose.yml` でローカル開発フローを支援する。
- `run.sh` または `make` タスクで頻繁に使うコマンドをラップすると親切。

## コーディング規約・コードレビュー
- 変更は PR ベース。小さなコミットと説明的な PR タイトル/説明を要求。
- レビューのチェック項目: テスト追加、型チェック、セキュリティ（外部へのデータ送信）、日本語UIの確認。

## 例: 推奨ディレクトリツリー
```
app/
├── main.py
├── core/
│   ├── config.py
│   └── database.py
├── services/
│   ├── extractor.py
│   ├── llm_client.py
│   └── similarity.py
├── api/
│   └── routes/
│       ├── ingest.py
│       └── documents.py
├── templates/
└── static/

tests/
data/
.spec-workflow/
README.md
DEVELOPMENT.md
CONTRIBUTING.md
```

## 最後に
この `structure.md` は生きたドキュメントです。設計変更が発生したときは `.spec-workflow/steering/structure.md` を更新し、必要であれば `docs/` にコピーして可視化してください。
