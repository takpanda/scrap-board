# Tasks: bookmarked-articles-page

- [x] タスク 1 - ルートとコントローラ追加
  - ファイル: `app/api/routes/bookmarks_only.py` (新規)
  - 目的: GET `/bookmarks` にアクセスするとログインユーザーのブックマーク済み記事一覧をレンダリングする
  - 成功基準:
    - ページが HTTP 200 を返す
    - レスポンスは `bookmarks_only.html` をレンダリングする
    - DB クエリは現在のユーザーのブックマークのみを取得する

  - _Prompt: Implement the task for spec bookmarked-articles-page, first run spec-workflow-guide then implement the task: 
    - Role: backend developer (FastAPI + SQLAlchemy)
    - Task: Create the route and controller that queries bookmarks for the current user and renders template
    - Restrictions: Follow existing routing pattern, reuse `templates = Jinja2Templates(directory="app/templates")`
    - _Leverage: existing `app/main.py`, `app/api/routes/bookmarks.py`, `app/api/routes/documents.py`
    - _Requirements: requirements.md (ユーザーのブックマークのみ表示、ページネーション、日本語)
    - Success: route responds 200 and template rendered with bookmark items

- [x] タスク 2 - サービス/クエリ関数追加
  - ファイル: `app/services/bookmark_service.py` (新規または既存拡張)
  - 目的: DB クエリロジックを分離し再利用可能にする
  - 成功基準:
    - `get_user_bookmarked_documents(user_id, page, per_page)` を提供
    - ページネーションと ordering を正しく適用

- [x] タスク 3 - テンプレート追加
  - ファイル: `app/templates/bookmarks_only.html` (新規)
  - 目的: 記事カード、サムネイル、要約、ドメイン、ブックマーク日時、ページネーションUIを表示
  - 成功基準:
    - 空時メッセージが日本語で表示
    - 各記事行がタイトルリンクと短いプレビューを表示

- [x] タスク 4 - ルーティング登録
  - ファイル: `app/main.py` のルータ include（必要なら）または `app/api/routes/__init__.py` への追加
  - 目的: アプリで新しいルートが有効化される
  - 成功基準: `/bookmarks` にアクセス可能

- [x] タスク 5 - 単体テスト作成
  - ファイル: `tests/test_bookmarks_only_page.py`
  - 目的: サービスの DB クエリとページのレンダリングを検証
  - 成功基準:
    - ログインユーザーのブックマークのみ表示されるテストがパスする
    - 空リスト時のメッセージが表示される

- [ ] タスク 6 - Playwright/ブラウザスナップショット (任意)
  - 目的: UI が期待通り表示されるか E2E 確認

## 実施順序
1 -> 2 -> 3 -> 4 -> 5 -> 6
