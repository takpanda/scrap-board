# Tasks: SpeakerDeck Feed Support

## 概要
このタスクリストは、SpeakerDeckのRSS/Atomフィード対応とPDF自動保存機能を実装するための作業を分解したものです。各タスクは1-3ファイルの変更で完結する原子的な作業単位です。

---

## Phase 1: データベース基盤

### - [x] Task 1.1: PDF対応のためのDBマイグレーション作成
**Files**: 
- `migrations/007_add_pdf_support.sql` (新規)

**Description**:
documentsテーブルに`pdf_path`カラムを追加し、PDF保存状態を記録できるようにする。部分インデックスでPDF有無のクエリを高速化。

**Requirements**: US-3, US-5

**Dependencies**: なし

**_Prompt**:
```
Implement the task for spec speakerdeck-feed-support, first run spec-workflow-guide to get the workflow guide then implement the task:

Role: Database Engineer specializing in SQLite migrations and schema design

Task: Create migration file `migrations/007_add_pdf_support.sql` to add pdf_path column to documents table following requirement US-3. The column should store relative paths like "assets/pdfs/speakerdeck/{document_id}.pdf". Create a partial index for faster queries on documents with PDFs.

Context:
- Reference existing migrations in migrations/ directory for style and patterns
- documents table exists with columns: id (TEXT PRIMARY KEY), url, title, body_markdown, etc.
- Need to support NULL values for backward compatibility with existing documents

Restrictions:
- Must use ALTER TABLE ADD COLUMN syntax (SQLite compatible)
- Do not modify existing columns
- Index should only cover non-NULL pdf_path values (partial index)
- Follow naming convention: idx_documents_<column_name>

Leverage:
- migrations/001_create_documents.sql for table structure reference
- migrations/apply_migrations.py for execution patterns

Success Criteria:
- Migration file creates pdf_path column as TEXT NULL
- Partial index created: CREATE INDEX idx_documents_pdf_path ON documents(pdf_path) WHERE pdf_path IS NOT NULL
- File follows project migration format
- Can be executed without errors on existing database

Instructions:
1. First, update tasks.md: Change `- [ ] Task 1.1` to `- [-] Task 1.1` to mark as in-progress
2. Create the migration file with appropriate SQL statements
3. After completing the task, update tasks.md: Change `- [-] Task 1.1` to `- [x] Task 1.1` to mark as completed
```

---

## Phase 2: SpeakerDeck PDF処理コア

### - [x] Task 2.1: SpeakerDeckHandler クラスの実装
**Files**: 
- `app/services/speakerdeck_handler.py` (新規)

**Description**:
SpeakerDeck特有のPDF取得・ダウンロード処理をカプセル化するハンドラークラス。oEmbed APIとHTMLスクレイピングでPDF URLを抽出し、ストリーミングダウンロードで保存。

**Requirements**: US-3

**Dependencies**: Task 1.1

**_Prompt**:
```
Implement the task for spec speakerdeck-feed-support, first run spec-workflow-guide to get the workflow guide then implement the task:

Role: Backend Developer specializing in web scraping and API integration

Task: Create `app/services/speakerdeck_handler.py` with SpeakerDeckHandler class following requirement US-3. Implement methods to detect SpeakerDeck URLs, extract PDF URLs using oEmbed API with HTML scraping fallback, and download PDFs with streaming.

Context:
- SpeakerDeck oEmbed API: https://speakerdeck.com/oembed.json?url={presentation_url}
- PDF URLs typically at: https://speakerd.s3.amazonaws.com/presentations/{id}/{slug}.pdf
- HTML may contain PDF links in meta tags, download buttons, or data attributes
- Need to handle large PDF files (up to 100MB)

Restrictions:
- Must validate URLs are from speakerdeck.com domain only
- Set timeout to 30 seconds for all HTTP requests
- Implement file size limit (100MB)
- Clean up partial files on download failure
- Do not raise exceptions - return None on errors and log warnings

Leverage:
- httpx library for HTTP requests (already in project)
- app/services/extractor.py for HTTP patterns
- app/core/config.py for timeout configuration

Success Criteria:
- Class methods: is_speakerdeck_url(), get_pdf_url(), download_pdf()
- get_pdf_url() tries oEmbed API first, falls back to HTML scraping
- download_pdf() saves to data/assets/pdfs/speakerdeck/{document_id}.pdf
- Returns relative path on success, None on failure
- Comprehensive logging (INFO for success, WARNING for failures, ERROR for critical issues)
- Handles all exceptions gracefully

Instructions:
1. First, update tasks.md: Change `- [ ] Task 2.1` to `- [-] Task 2.1` to mark as in-progress
2. Create the speakerdeck_handler.py file with the SpeakerDeckHandler class
3. Implement all required methods with proper error handling and logging
4. After completing the task, update tasks.md: Change `- [-] Task 2.1` to `- [x] Task 2.1` to mark as completed
```

---

### - [x] Task 2.2: SpeakerDeckHandlerのユニットテスト
**Files**: 
- `tests/test_speakerdeck_handler.py` (新規)

**Description**:
SpeakerDeckHandlerの各メソッドをモックを使ってテスト。URL検証、PDF URL抽出、ダウンロード処理の成功・失敗シナリオをカバー。

**Requirements**: US-3

**Dependencies**: Task 2.1

**_Prompt**:
```
Implement the task for spec speakerdeck-feed-support, first run spec-workflow-guide to get the workflow guide then implement the task:

Role: QA Engineer specializing in Python unit testing with pytest and mocking

Task: Create comprehensive unit tests for SpeakerDeckHandler in `tests/test_speakerdeck_handler.py` covering requirement US-3. Test all methods with both success and failure scenarios using mocked HTTP responses.

Context:
- SpeakerDeckHandler has three main methods: is_speakerdeck_url(), get_pdf_url(), download_pdf()
- Need to mock httpx.Client for HTTP requests
- Need to mock file system operations for download tests
- Test data: valid SpeakerDeck URLs, invalid URLs, various HTML responses

Restrictions:
- Must not make actual HTTP requests
- Must not create actual files (mock file operations)
- Each test should be independent and isolated
- Follow pytest conventions and existing test patterns

Leverage:
- conftest.py for pytest fixtures
- tests/test_basic.py for testing patterns
- pytest-mock for mocking

Success Criteria:
- Test is_speakerdeck_url() with valid/invalid URLs
- Test get_pdf_url() with mocked oEmbed success, oEmbed failure + HTML scraping success, complete failure
- Test download_pdf() with successful download, network error, file size limit exceeded
- All tests pass independently
- Test coverage >80% for speakerdeck_handler.py
- Clear test names and docstrings

Instructions:
1. First, update tasks.md: Change `- [ ] Task 2.2` to `- [-] Task 2.2` to mark as in-progress
2. Create the test file with comprehensive test cases
3. Run tests with: pytest tests/test_speakerdeck_handler.py -v
4. After completing the task, update tasks.md: Change `- [-] Task 2.2` to `- [x] Task 2.2` to mark as completed
```

---

## Phase 3: フィード取得機能

### - [x] Task 3.1: SpeakerDeckフィード取得関数の実装
**Files**: 
- `app/services/ingest_worker.py` (変更)

**Description**:
ingest_worker.pyに`_fetch_speakerdeck_items()`関数を追加。feedparserでRSS/Atomフィードをパースし、エントリリストを返す。

**Requirements**: US-1, US-2

**Dependencies**: なし

**_Prompt**:
```
Implement the task for spec speakerdeck-feed-support, first run spec-workflow-guide to get the workflow guide then implement the task:

Role: Backend Developer specializing in RSS/Atom feed processing and integration

Task: Add `_fetch_speakerdeck_items()` function to `app/services/ingest_worker.py` following requirements US-1 and US-2. Parse SpeakerDeck RSS/Atom feeds using feedparser and return list of entries.

Context:
- SpeakerDeck feed URL format: https://speakerdeck.com/{username}.rss or .atom
- Config keys: username (generates URL), url (direct URL), per_page (max items), format (rss/atom)
- Return format: [{"link": str, "title": str, "published": str, "summary": str}, ...]
- Similar functions exist: _fetch_qiita_items(), _fetch_hatena_items(), _fetch_rss_items()

Restrictions:
- Must follow existing function patterns in ingest_worker.py
- Handle missing feedparser gracefully (ModuleNotFoundError)
- Do not raise exceptions - return empty list on errors
- Log appropriate messages (INFO for success, WARNING for errors)

Leverage:
- app/services/ingest_worker.py existing _fetch_*_items() functions for patterns
- feedparser library (already in project)
- app/core/config.py for configuration patterns

Success Criteria:
- Function signature: def _fetch_speakerdeck_items(config: Dict[str, Any]) -> List[Dict]
- Generates feed URL from username or uses direct URL
- Parses RSS and Atom formats
- Respects per_page limit (default: 20)
- Returns list with required keys: link, title, published, summary
- Comprehensive error handling and logging

Instructions:
1. First, update tasks.md: Change `- [ ] Task 3.1` to `- [-] Task 3.1` to mark as in-progress
2. Add the _fetch_speakerdeck_items() function following existing patterns
3. Ensure proper error handling and logging
4. After completing the task, update tasks.md: Change `- [-] Task 3.1` to `- [x] Task 3.1` to mark as completed
```

---

### - [x] Task 3.2: trigger_fetch_for_source へのSpeakerDeck統合
**Files**: 
- `app/services/ingest_worker.py` (変更)

**Description**:
`trigger_fetch_for_source()`関数にspeakerdeckタイプのハンドリングを追加。既存のqiita、hatena、rssと同様のパターンで統合。

**Requirements**: US-1, US-2

**Dependencies**: Task 3.1

**_Prompt**:
```
Implement the task for spec speakerdeck-feed-support, first run spec-workflow-guide to get the workflow guide then implement the task:

Role: Backend Developer specializing in system integration and workflow orchestration

Task: Modify `trigger_fetch_for_source()` in `app/services/ingest_worker.py` to integrate SpeakerDeck feed fetching following requirements US-1 and US-2. Add speakerdeck type handling alongside existing source types.

Context:
- Function already handles: qiita, hatena, rss source types
- Need to add elif branch for source_type == "speakerdeck"
- Call _fetch_speakerdeck_items(config) and process items same way as other sources
- Items are passed to _insert_document_from_url() for ingestion

Restrictions:
- Must maintain existing source type handling
- Follow exact same pattern as other source types
- Do not modify other source type logic
- Preserve error handling and logging patterns

Leverage:
- app/services/ingest_worker.py existing trigger_fetch_for_source() function
- Existing elif branches for qiita, hatena, rss as templates

Success Criteria:
- Add elif source_type == "speakerdeck": branch
- Call _fetch_speakerdeck_items(config) to get items
- Process items through same pipeline as other sources
- Logging matches existing pattern
- No regression in existing source types

Instructions:
1. First, update tasks.md: Change `- [ ] Task 3.2` to `- [-] Task 3.2` to mark as in-progress
2. Locate the if/elif chain in trigger_fetch_for_source()
3. Add speakerdeck elif branch following existing patterns
4. After completing the task, update tasks.md: Change `- [-] Task 3.2` to `- [x] Task 3.2` to mark as completed
```

---

## Phase 4: Ingestionパイプライン統合

### - [x] Task 4.1: _insert_document_from_url へのPDF処理追加
**Files**: 
- `app/services/ingest_worker.py` (変更)

**Description**:
`_insert_document_from_url()`にSpeakerDeck検出とPDF保存処理を追加。ドキュメント挿入後、URLがSpeakerDeckの場合はPDFをダウンロードしてパスを更新。

**Requirements**: US-3

**Dependencies**: Task 2.1, Task 3.2

**_Prompt**:
```
Implement the task for spec speakerdeck-feed-support, first run spec-workflow-guide to get the workflow guide then implement the task:

Role: Backend Developer specializing in data pipeline integration and transaction management

Task: Modify `_insert_document_from_url()` in `app/services/ingest_worker.py` to add SpeakerDeck PDF processing following requirement US-3. After document insertion, detect SpeakerDeck URLs and download PDFs.

Context:
- Function already handles: content extraction, document insertion, postprocessing
- Need to add PDF handling after doc_id is returned from _insert_document_if_new()
- Use SpeakerDeckHandler to detect, get PDF URL, and download
- Update documents table with pdf_path
- PDF download failure should not fail document insertion

Restrictions:
- Must add PDF handling AFTER document insertion (so doc_id exists)
- PDF errors must be logged but not re-raised
- Must commit PDF path update separately
- Do not modify existing extraction or insertion logic
- Maintain transaction integrity

Leverage:
- app/services/ingest_worker.py existing _insert_document_from_url() function
- app/services/speakerdeck_handler.py for SpeakerDeckHandler
- SQLAlchemy text() for UPDATE query

Success Criteria:
- After document insertion, check if URL is SpeakerDeck
- Call SpeakerDeckHandler.get_pdf_url() and download_pdf()
- Update documents table: UPDATE documents SET pdf_path = :pdf_path WHERE id = :id
- Commit PDF path update
- Log INFO on success, WARNING on PDF extraction failure, ERROR on download failure
- Document insertion succeeds even if PDF fails

Instructions:
1. First, update tasks.md: Change `- [ ] Task 4.1` to `- [-] Task 4.1` to mark as in-progress
2. Import SpeakerDeckHandler at top of file
3. Add PDF processing block after _insert_document_if_new() call
4. Ensure proper error handling and transaction management
5. After completing the task, update tasks.md: Change `- [-] Task 4.1` to `- [x] Task 4.1` to mark as completed
```

---

## Phase 5: API エンドポイント

### - [x] Task 5.1: PDFダウンロードAPIエンドポイントの実装
**Files**: 
- `app/api/routes/documents.py` (変更または新規)

**Description**:
`GET /api/documents/{document_id}/pdf` エンドポイントを追加。ドキュメントIDからPDFファイルを取得してFileResponseで返す。セキュリティ検証を含む。

**Requirements**: US-4

**Dependencies**: Task 1.1, Task 4.1

**_Prompt**:
```
Implement the task for spec speakerdeck-feed-support, first run spec-workflow-guide to get the workflow guide then implement the task:

Role: API Developer specializing in FastAPI endpoints and secure file serving

Task: Add PDF download endpoint to `app/api/routes/documents.py` following requirement US-4. Implement `GET /api/documents/{document_id}/pdf` with security validations and proper file response headers.

Context:
- Need to check if documents.py exists in app/api/routes/, if not create it
- Endpoint retrieves document from database, validates pdf_path exists
- Must validate file path is within data/ directory (prevent path traversal)
- Return FileResponse with appropriate Content-Type and Content-Disposition headers
- Generate safe filename from document title

Restrictions:
- Must validate document_id exists in database
- Must check pdf_path is not NULL
- Must validate file exists on disk
- Must prevent path traversal attacks (resolve paths and check prefix)
- Must sanitize filename (remove non-alphanumeric except spaces, hyphens, underscores)
- Use FastAPI HTTPException for errors (404 for not found, 403 for forbidden)

Leverage:
- app/core/database.py for get_db dependency
- FastAPI FileResponse for file serving
- pathlib.Path for path operations
- SQLAlchemy text() for queries

Success Criteria:
- Endpoint: @router.get("/{document_id}/pdf")
- Returns 404 if document not found or pdf_path is NULL
- Returns 404 if file not found on disk
- Returns 403 if path traversal detected
- Returns FileResponse with media_type="application/pdf"
- Content-Disposition header: attachment; filename="{safe_title}.pdf"
- Filename sanitized and limited to 100 characters

Instructions:
1. First, update tasks.md: Change `- [ ] Task 5.1` to `- [-] Task 5.1` to mark as in-progress
2. Check if app/api/routes/documents.py exists, create if needed with router setup
3. Implement download_pdf endpoint with all security validations
4. Test with: curl http://localhost:8000/api/documents/{valid_id}/pdf
5. After completing the task, update tasks.md: Change `- [-] Task 5.1` to `- [x] Task 5.1` to mark as completed
```

---

### - [x] Task 5.2: メインアプリケーションへのルーター登録
**Files**: 
- `app/main.py` (変更)

**Description**:
main.pyにdocumentsルーターをinclude_router()で登録。既存のrouterパターンに従う。

**Requirements**: US-4

**Dependencies**: Task 5.1

**_Prompt**:
```
Implement the task for spec speakerdeck-feed-support, first run spec-workflow-guide to get the workflow guide then implement the task:

Role: Backend Developer specializing in FastAPI application configuration

Task: Register documents router in `app/main.py` following requirement US-4. Add include_router() call for the new documents endpoints.

Context:
- main.py already includes other routers (e.g., admin routes)
- Need to import documents router from app.api.routes.documents
- Add app.include_router(documents.router) after other router registrations
- Router already has prefix="/api/documents" configured in documents.py

Restrictions:
- Must place router registration with other include_router() calls
- Do not modify existing router registrations
- Follow existing import patterns
- Maintain router order if significant

Leverage:
- app/main.py existing router registrations for patterns
- app/api/routes/documents.py for router import

Success Criteria:
- Import: from app.api.routes import documents
- Call: app.include_router(documents.router)
- Endpoint accessible at /api/documents/{id}/pdf
- No errors on application startup

Instructions:
1. First, update tasks.md: Change `- [ ] Task 5.2` to `- [-] Task 5.2` to mark as in-progress
2. Add import statement for documents router
3. Add include_router() call in appropriate location
4. Test startup: uvicorn app.main:app --reload
5. After completing the task, update tasks.md: Change `- [-] Task 5.2` to `- [x] Task 5.2` to mark as completed
```

---

## Phase 6: UIコンポーネント

### - [x] Task 6.1: 記事カードへのPDFダウンロードボタン追加
**Files**: 
- `app/templates/partials/document_card.html` (変更)

**Description**:
document_card.htmlにPDFダウンロードボタンを追加。pdf_pathがある場合のみ表示、Lucideアイコンを使用。

**Requirements**: US-4

**Dependencies**: Task 5.2

**_Prompt**:
```
Implement the task for spec speakerdeck-feed-support, first run spec-workflow-guide to get the workflow guide then implement the task:

Role: Frontend Developer specializing in HTML/Jinja2 templating and UI components

Task: Add PDF download button to `app/templates/partials/document_card.html` following requirement US-4. Add conditional display for documents with pdf_path.

Context:
- Card already has action buttons (元記事, 詳細を見る)
- Need to add PDF download button between them
- Use Jinja2 conditional: {% if document.pdf_path %}
- Use Lucide icon: file-down
- Button should link to /api/documents/{{ document.id }}/pdf
- Style: red-themed pill button to match PDF file association

Restrictions:
- Must only display if document.pdf_path exists
- Must use existing pill button classes for consistency
- Must include download attribute on anchor tag
- Do not modify existing buttons
- Follow existing Lucide icon patterns

Leverage:
- app/templates/partials/document_card.html existing button structures
- Lucide icons: https://lucide.dev/icons/file-down
- Existing pill classes: pill nowrap-tag inline-flex items-center h-6 px-2 text-xs

Success Criteria:
- Button displays only when pdf_path is not NULL
- Anchor tag: href="/api/documents/{{ document.id }}/pdf" download
- Icon: <i data-lucide="file-down" class="w-4 h-4 mr-1"></i>
- Classes: pill nowrap-tag inline-flex items-center h-6 px-2 text-xs bg-red-50 text-red-600 border border-red-200 hover:bg-red-100
- Title attribute: "PDFをダウンロード"
- Label text: "PDF"

Instructions:
1. First, update tasks.md: Change `- [ ] Task 6.1` to `- [-] Task 6.1` to mark as in-progress
2. Locate the action buttons section in document_card.html
3. Add PDF download button with conditional display
4. Test rendering with document that has pdf_path and one that doesn't
5. After completing the task, update tasks.md: Change `- [-] Task 6.1` to `- [x] Task 6.1` to mark as completed
```

---

### - [x] Task 6.2: ドキュメント詳細ページへのPDFダウンロードボタン追加
**Files**: 
- `app/templates/document_detail.html` (変更)

**Description**:
document_detail.htmlのヘッダーアクションボタン群にPDFダウンロードボタンを追加。カードよりも大きめのボタンスタイル。

**Requirements**: US-4

**Dependencies**: Task 6.1

**_Prompt**:
```
Implement the task for spec speakerdeck-feed-support, first run spec-workflow-guide to get the workflow guide then implement the task:

Role: Frontend Developer specializing in HTML/Jinja2 templating and responsive design

Task: Add PDF download button to `app/templates/document_detail.html` following requirement US-4. Add prominent button in header action section.

Context:
- Detail page has header section with action buttons (larger than card buttons)
- Need to add PDF download button alongside existing actions
- Use same conditional: {% if document.pdf_path %}
- Use Lucide icon: file-down (larger size for detail page)
- Style should be consistent with detail page button sizing (px-4 py-2)

Restrictions:
- Must only display if document.pdf_path exists
- Must use detail page button classes (not card pill classes)
- Must include download attribute
- Follow existing detail page button patterns
- Do not modify existing buttons

Leverage:
- app/templates/document_detail.html existing action button structures
- Lucide icons with larger size: w-5 h-5
- Detail page button classes

Success Criteria:
- Button displays only when pdf_path is not NULL
- Anchor tag: href="/api/documents/{{ document.id }}/pdf" download
- Icon: <i data-lucide="file-down" class="w-5 h-5 mr-2"></i>
- Classes: inline-flex items-center px-4 py-2 bg-red-50 text-red-600 border border-red-200 rounded-md hover:bg-red-100 transition-colors
- Button text: "PDFをダウンロード"
- Positioned with other action buttons in header

Instructions:
1. First, update tasks.md: Change `- [ ] Task 6.2` to `- [-] Task 6.2` to mark as in-progress
2. Locate the header action buttons section in document_detail.html
3. Add PDF download button with appropriate sizing
4. Test rendering and button interactions
5. After completing the task, update tasks.md: Change `- [-] Task 6.2` to `- [x] Task 6.2` to mark as completed
```

---

## Phase 7: テストとデプロイ準備

### - [ ] Task 7.1: 統合テストの作成
**Files**: 
- `tests/test_speakerdeck_integration.py` (新規)

**Description**:
SpeakerDeckフィード取得からPDF保存、APIダウンロードまでの全フローを統合テスト。モックを使った実際のワークフローシミュレーション。

**Requirements**: All

**Dependencies**: Task 4.1, Task 5.2

**_Prompt**:
```
Implement the task for spec speakerdeck-feed-support, first run spec-workflow-guide to get the workflow guide then implement the task:

Role: QA Engineer specializing in integration testing and end-to-end workflow validation

Task: Create comprehensive integration tests in `tests/test_speakerdeck_integration.py` covering the complete SpeakerDeck workflow. Test feed fetch → document insertion → PDF download → API serving.

Context:
- Test full workflow: feed parsing → URL ingestion → PDF processing → DB update → API download
- Use test database (test_speakerdeck.db or similar)
- Mock external HTTP calls (SpeakerDeck feed, oEmbed API, PDF download)
- Test both success and failure scenarios

Restrictions:
- Must use test database, not production database
- Must mock all external HTTP requests
- Must clean up test files and database after tests
- Follow existing integration test patterns in tests/
- Each test should be independent

Leverage:
- conftest.py for database fixtures
- tests/test_basic.py for integration test patterns
- pytest fixtures for test data
- httpx_mock or responses library for HTTP mocking

Success Criteria:
- Test: test_fetch_speakerdeck_feed() - feed parsing
- Test: test_ingest_speakerdeck_url() - document insertion with PDF
- Test: test_download_pdf_endpoint() - API endpoint returns file
- Test: test_pdf_not_found_error() - 404 when pdf_path is NULL
- Test: test_invalid_document_id() - 404 when document doesn't exist
- All tests pass independently
- Proper cleanup (database, files)
- Test coverage validates all requirements

Instructions:
1. First, update tasks.md: Change `- [ ] Task 7.1` to `- [-] Task 7.1` to mark as in-progress
2. Create integration test file with comprehensive test cases
3. Run tests with: pytest tests/test_speakerdeck_integration.py -v
4. Verify all tests pass and cleanup works correctly
5. After completing the task, update tasks.md: Change `- [-] Task 7.1` to `- [x] Task 7.1` to mark as completed
```

---

### - [ ] Task 7.2: マイグレーション実行と動作確認
**Files**: 
- (既存マイグレーションツールを使用)

**Description**:
作成したマイグレーションを実行し、PDFディレクトリを作成。開発環境でSpeakerDeckソースを登録して実際のフィードを取得し、機能が正常に動作することを確認。

**Requirements**: All

**Dependencies**: Task 7.1

**_Prompt**:
```
Implement the task for spec speakerdeck-feed-support, first run spec-workflow-guide to get the workflow guide then implement the task:

Role: DevOps Engineer specializing in deployment and operational verification

Task: Execute database migration and perform end-to-end smoke test of SpeakerDeck feature. Verify all components work together in development environment.

Context:
- Need to run migration 007_add_pdf_support.sql
- Create PDF storage directory structure
- Register test SpeakerDeck source in admin panel
- Trigger manual feed fetch to verify full workflow
- Check document card displays PDF button
- Test PDF download from UI

Restrictions:
- Use development database (data/scraps.db or test database)
- Do not use production SpeakerDeck accounts for testing
- Verify migration is idempotent (can run multiple times)
- Document any manual steps required

Leverage:
- migrations/apply_migrations.py for running migrations
- Admin panel for source registration
- Browser DevTools for debugging UI issues

Success Criteria:
- Migration 007_add_pdf_support.sql executed successfully
- Directory created: data/assets/pdfs/speakerdeck/
- Test SpeakerDeck source registered (use public SpeakerDeck feed)
- Feed fetch completes without errors
- Document inserted with pdf_path populated
- PDF file exists at specified path
- UI displays PDF download button
- PDF downloads successfully from browser
- All logs show appropriate INFO/WARNING messages

Verification Steps:
1. Run migration: python migrations/apply_migrations.py
2. Create directory: mkdir -p data/assets/pdfs/speakerdeck
3. Start app: uvicorn app.main:app --reload
4. Register source: Admin → Sources → Add SpeakerDeck source
5. Trigger fetch: Use admin panel or wait for cron
6. Check logs for PDF processing
7. Verify UI shows PDF button
8. Download PDF and verify file

Instructions:
1. First, update tasks.md: Change `- [ ] Task 7.2` to `- [-] Task 7.2` to mark as in-progress
2. Execute migration and create directories
3. Perform end-to-end smoke test following verification steps
4. Document any issues found and resolved
5. After completing the task, update tasks.md: Change `- [-] Task 7.2` to `- [x] Task 7.2` to mark as completed
```

---

### - [ ] Task 7.3: ドキュメントとREADME更新
**Files**: 
- `README.md` (変更)
- `docs/` (必要に応じて)

**Description**:
READMEにSpeakerDeck対応を追加。管理画面でのソース登録方法、PDF保存の動作、トラブルシューティングを記載。

**Requirements**: All

**Dependencies**: Task 7.2

**_Prompt**:
```
Implement the task for spec speakerdeck-feed-support, first run spec-workflow-guide to get the workflow guide then implement the task:

Role: Technical Writer specializing in developer documentation and user guides

Task: Update project documentation to reflect SpeakerDeck feed support feature. Add usage instructions, troubleshooting tips, and feature description.

Context:
- README.md has sections for features, usage, configuration
- Need to document SpeakerDeck as new content source
- Explain PDF auto-download and storage
- Document admin panel source registration
- Include troubleshooting for common issues

Restrictions:
- Must maintain existing documentation structure
- Follow project's Japanese language requirement for user-facing content
- Keep technical details concise but comprehensive
- Include examples where helpful

Leverage:
- README.md existing feature descriptions for style
- docs/ directory for detailed documentation if needed
- .github/copilot-instructions.md for context

Success Criteria:
- README.md updated with SpeakerDeck in supported sources list
- Usage section explains how to register SpeakerDeck source
- Feature description mentions PDF auto-download and storage
- Troubleshooting section includes: PDF download failures, feed parsing errors, storage path issues
- Configuration notes for SpeakerDeck username vs direct URL
- Example SpeakerDeck source config in README
- Japanese language for user-facing instructions

Documentation Sections to Update:
1. 主な機能 (Features): Add SpeakerDeck support
2. コンテンツソース (Content Sources): Add SpeakerDeck details
3. 使い方 (Usage): Add source registration instructions
4. トラブルシューティング: Add SpeakerDeck-specific issues

Instructions:
1. First, update tasks.md: Change `- [ ] Task 7.3` to `- [-] Task 7.3` to mark as in-progress
2. Review README.md structure and identify update locations
3. Add SpeakerDeck documentation following existing patterns
4. Include practical examples and troubleshooting tips
5. After completing the task, update tasks.md: Change `- [-] Task 7.3` to `- [x] Task 7.3` to mark as completed
```

---

## 完了基準

すべてのタスクが完了した時点で、以下が達成されていること:

- ✅ データベースにpdf_pathカラムが追加され、マイグレーションが適用されている
- ✅ SpeakerDeckHandlerクラスが実装され、ユニットテストが通過している
- ✅ SpeakerDeckフィード取得が動作し、trigger_fetch_for_sourceに統合されている
- ✅ ドキュメント挿入時にPDF自動ダウンロードが機能している
- ✅ PDFダウンロードAPIエンドポイントが実装され、main.pyに登録されている
- ✅ 記事カードとドキュメント詳細ページにPDFダウンロードボタンが表示される
- ✅ 統合テストが作成され、全テストが通過している
- ✅ 開発環境での動作確認が完了している
- ✅ ドキュメントが更新され、使い方が記載されている

## 注意事項

- 各タスクは独立して実行可能ですが、Dependenciesに記載されたタスクを先に完了してください
- エラーハンドリングは各コンポーネントで適切に行い、一部の失敗が全体に影響しないようにしてください
- PDF取得失敗時もドキュメント登録は成功させる設計を維持してください
- セキュリティ（パストラバーサル対策、ファイルサイズ制限）を必ず実装してください
- テストは必ずモックを使用し、実際の外部APIへのリクエストは行わないでください
