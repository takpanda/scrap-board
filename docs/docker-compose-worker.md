# Docker Compose で postprocess_queue / preference_worker を常駐させる

このドキュメントは `postprocess_queue.run_worker` と `scripts/run_preference_worker.py` を Docker Compose で常駐させるための最小構成と運用上の注意をまとめたものです。

## 目的

- `enqueue_job_for_document` によって作成された `postprocess_jobs` を確実に処理するために、ポーリングワーカーをコンテナ化して常時稼働させる。

## 最小構成（`docker-compose.yml` への追加例）

既存の `Dockerfile` を流用する前提で、`docker-compose.yml` に以下のサービスを追加します:

```yaml
  worker:
    build: .
    command: ["python", "-m", "app.services.postprocess_queue"]
    volumes:
      - ./data:/app/data
      - ./.env:/app/.env
    environment:
      - DB_URL=sqlite:///./data/scraps.db
      - TIMEOUT_SEC=180
    restart: unless-stopped

  preference-worker:
    build: .
    command: ["python", "scripts/run_preference_worker.py", "--interval", "2.0"]
    volumes:
      - ./data:/app/data
      - ./.env:/app/.env
    environment:
      - DB_URL=sqlite:///./data/scraps.db
      - TIMEOUT_SEC=180
    depends_on:
      - app
    restart: unless-stopped
```

- `command` はモジュール実行で `run_worker` を呼び出します。
- `volumes` で `./data` をマウントすることでホスト上の SQLite ファイルを共有します。
- `preference-worker` は嗜好プロファイル・パーソナライズ済みスコアを計算するワーカーです。`preference_jobs` テーブルをポーリングし続けるため、`app` サービスと並行で常駐させてください。

## 起動手順（開発環境）

```fish
docker compose build
docker compose up -d
# ワーカーのログを確認
docker compose logs -f worker
docker compose logs -f preference-worker
```

## 動作確認

1. API 経由で記事を取り込む（例: `/api/ingest/url`）。
2. ワーカーのログに `Picked job ...` や `Job ... completed` のログが出ることを確認する。
3. 必要に応じて `postprocess_jobs` テーブルを直接確認して `status` が `done` に移行していることを確認する。

## 注意点 / 運用上の留意点

- SQLite の共有制約:
  - SQLite を複数コンテナ（あるいは複数ホスト）で共有する場合、ファイルロックや同時書き込みで問題が発生する可能性があります。
  - 小規模な開発環境では問題にならないことが多いですが、本番では PostgreSQL 等のネットワーク DB に移行することを強く推奨します。

- Preference ワーカーのヘルス監視:
  - `preference_jobs` が溜まったままになっていないかを定期的に確認してください。
  - ジョブログに `missing-documents` が頻出する場合、取り込み済みドキュメントの削除や参照不整合が疑われます。

- スケーリング:
  - `worker` を複数インスタンスにスケールする場合、SQLite の制約により競合が起きやすくなります。スケールアウトするなら DB の変更とジョブブローカー（Redis/Celery 等）の導入を検討してください。

- ロギングと監視:
  - `docker compose logs` やログドライバでワーカーのログを収集し、ジョブの失敗や繰り返し失敗するジョブをアラートすることをおすすめします。

## 追加提案（将来的な改善）

- `docker-compose` サンプルで PostgreSQL を使う構成を用意し、SQLite 依存を外す。
- ジョブ処理のメトリクス（処理時間、成功率、再試行回数）を Prometheus などで収集する。 

---

作業済み: `docker-compose` 用ワーカーの追加案と起動手順

## マイグレーションの適用

リポジトリには簡易的なマイグレーション適用スクリプトがあり、`migrations/*.sql` を順に適用できます。開発環境で DB スキーマを更新する手順:

```fish
# DB ファイルが存在することを確認（存在しない場合は create_tables() が作成するか、新規に空ファイルを作成）
ls -l data || mkdir -p data
touch data/scraps.db

# マイグレーションを適用
python migrations/apply_migrations.py --db ./data/scraps.db
```

`apply_migrations.py` は `migrations/` 内の `.sql` を辞書順に実行します。今回追加した `migrations/003_create_postprocess_jobs.sql` により `postprocess_jobs` テーブルが作成されます。
