# SpeakerDeck PDF ボタン表示問題の調査・対策

日付: 2025-10-05

目的
- SpeakerDeck 由来の記事で一覧カードや詳細ページに PDF ダウンロードボタンが表示されない事象を調査し、原因を特定、修正を行い、その手順と確認方法をドキュメント化する。

背景
- UI のカード・詳細テンプレートには `{% if document.pdf_path %}` 条件で PDF ボタンを表示する実装が既にある。
- しかし一部の SpeakerDeck コンテンツでボタンが表示されず、ユーザーから「PDF ダウンロードボタンが見えない」と報告があった。

調査結果（要点）
1. テンプレート側
   - `app/templates/partials/document_card.html` と `app/templates/document_detail.html` の両方で PDF ボタンは `{% if document.pdf_path %}` 条件で表示される実装であった。
   - 一覧ページ（`documents.html`）とブックマークページ（`bookmarks_only.html`）はともにカードテンプレートを `include` しているため、カードの条件に従う。

2. モデル・DB 側
   - 当初 `Document` モデルに `pdf_path` カラムが存在しないケースがあり、テンプレートに渡されるインスタンスに属性が無くボタンが表示されない可能性があった。
   - `app/core/database.py` に `pdf_path = Column(String, nullable=True)` を追加し、`create_tables()` の SQLite 用追加カラムリストにも `pdf_path` を含めて、新旧データベースへカラム追加を適用した。

3. 取り込み（ingest）側
   - `app/services/speakerdeck_handler.py` は SpeakerDeck の oEmbed / HTML スクレイピングで PDF URL を抽出し、`download_pdf()` でローカルに保存する実装がある（ストリーミング、100MB 上限付き）。
   - `app/services/ingest_worker.py` の取り込み後処理は `download_pdf()` を呼び出し、成功時に `documents.pdf_path` を更新する実装になっている。

修正内容（実施済み）
1. モデル変更
   - `app/core/database.py` に `pdf_path` カラムを追加。
   - `create_tables()` を再実行し、SQLite の既存 DB に `pdf_path` カラムを追加。

2. API エンドポイントの改善
   - `GET /api/documents/{id}/pdf` を修正し、`pdf_path` が外部 URL（http/https）なら `RedirectResponse` でその URL へリダイレクトするようにした。これにより大きなファイルをローカル保存せず外部参照にする運用に対応。

3. バックフィル用スクリプト追加
   - `scripts/backfill_speakerdeck_pdfs.py` を追加。
     - Dry-run: PDF URL を抽出して一覧表示
     - `--apply`: 抽出した URL をダウンロード（100MB 上限）し、成功したら `documents.pdf_path` を `assets/pdfs/speakerdeck/<id>.pdf` の相対パスで更新
   - 大きすぎる PDF はダウンロードを中止する実装のまま。該当ファイルは外部 URL を `pdf_path` に保存する方針。

4. 外部 URL を登録する簡易スクリプト
   - `scripts/set_external_pdf_paths.py` を追加して、（手動で決めた）大きな PDF の外部 URL を特定の document.id にセットする処理を用意し、実行済み。

実行ログ（要約）
- dry-run で 4 件の SpeakerDeck レコードに PDF URL を検出。
- `--apply` 実行で 2 件はローカル保存に成功し DB 更新。2 件は 100MB 上限を超えたためダウンロード失敗となり、外部 URL を `pdf_path` に登録した。
- 例: `e76e1fac-bb8a-45e4-9107-0317b453e3fe` は `assets/pdfs/speakerdeck/e76e1fac-....pdf` がローカルに存在（サイズ約3.96MB）であり、カードに PDF ボタンが表示される条件を満たす。

確認方法（手順）
1. 対象ドキュメントの `pdf_path` を確認:
   ```sh
   sqlite3 data/scraps.db "SELECT id, title, pdf_path FROM documents WHERE id = '<DOCUMENT_ID>';"
   ```
2. ローカルファイルの存在確認（ローカル保存されている場合）:
   ```sh
   ls -l data/<pdf_path>
   ```
3. サーバーでの動作確認:
   - ブラウザで `/documents`（一覧）や `/documents/<DOCUMENT_ID>`（詳細）を開き、カードに「PDF」ボタンが表示されるか確認する。
   - ボタンをクリックしてダウンロード（ローカル保存）または外部 URL へリダイレクトするか確認する。

運用上の注意・次の改善案
- 現状はローカル保存の上限を 100MB としており、大容量ファイルは外部参照扱いにする運用にしています。運用方針により下記のいずれかを検討してください:
  1. 上限引き上げ（ディスクとメモリ要件を評価）
  2. 大容量ファイルはクラウドストレージ（S3/GCS）へアップロードして `pdf_path` を外部ストレージ URL にするワークフローを作る
  3. UI で「外部PDF」ラベルを表示してユーザーに外部参照であることを明示する

補助スクリプト
- `scripts/backfill_speakerdeck_pdfs.py`
  - Dry-run: `PYTHONPATH=. python scripts/backfill_speakerdeck_pdfs.py`
  - Apply: `PYTHONPATH=. python scripts/backfill_speakerdeck_pdfs.py --apply`
- `scripts/set_external_pdf_paths.py` (手動更新用)
  - 実行: `PYTHONPATH=. python scripts/set_external_pdf_paths.py`

問い合わせ先
- 実行ログや追加のドキュメント ID があれば共有してください。該当レコードの `pdf_path` 確認やバックフィル実行を代行できます。

---

作成者: 開発チーム（自動生成ドキュメント）
