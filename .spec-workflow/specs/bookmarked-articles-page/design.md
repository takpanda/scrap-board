# Design: bookmarked-articles-page

## 概要
この設計では、ユーザーがブックマークした記事のみを一覧表示する専用ページを実装する方法を記述します。実装は FastAPI と Jinja2 テンプレートを使い、既存のデータモデルと認証を再利用します。

## コンポーネント
- ルート: `GET /bookmarks` （または `/bookmarks/only`）
- テンプレート: `app/templates/bookmarks_only.html`
- サービス: `app/services/bookmark_service.py`（既存があれば利用、無ければ軽量な関数を `app/services/__init__.py` に追加）
- 既存テーブル: `bookmarks` (user_id, document_id, created_at), `documents`

## ルーティングとコントローラ
- ルート定義ファイル: `app/api/routes/bookmarks.py`
- 処理フロー:
  1. 現在のユーザーを取得（既存の auth/session ユーティリティを使用）
  2. 指定ページ（query param `page`, default=1）を受け取りページネーション情報を決定
  3. `bookmark_service.get_user_bookmarked_documents(user_id, page, per_page)` を呼び出す
  4. テンプレート `bookmarks_only.html` にドキュメント一覧とページネーション情報を渡す

## DBクエリ（高レベル）
- SQLAlchemy または既存のDBラッパーを利用して、次のようなクエリを実装:
  - Join `bookmarks` と `documents` on document_id
  - Filter by `bookmarks.user_id == current_user.id`
  - Order by `bookmarks.created_at DESC`
  - Limit/Offset を使用してページネーション

## テンプレート設計（`bookmarks_only.html`）
- ヘッダー: ページタイトル（例: 「ブックマーク」）
- 記事カード（リスト）: タイトル（リンク）、サムネイル（存在する場合）、短い要約（truncate）、ドメイン、ブックマーク日時
- ページネーション UI: 前へ/次へボタン（既存のスタイルを再利用）
- 空の場合: 日本語のプレースホルダメッセージ

## ページネーション
- `per_page` は環境または設定で決定（初期値: 20）
- UI はシンプルな前後ナビゲーション

## テスト計画
- 単体テスト: `bookmark_service.get_user_bookmarked_documents` の DB クエリの戻り値を検証
- 統合テスト: `GET /bookmarks` に対し、ログインユーザーのブックマークのみ表示されることを確認
- UI スナップショット (playwright テストが既にあれば追加)

## セキュリティ/権限
- 他ユーザーのブックマークを表示しない
- 未ログインユーザーはリダイレクトまたは空のメッセージを表示（既存挙動に合わせる）

## 変更ファイル一覧
- app/api/routes/bookmarks.py (新規)
- app/services/bookmark_service.py (新規または拡張)
- app/templates/bookmarks_only.html (新規)
- tests/test_bookmarks_only_page.py (新規)

## 実装マイルストーン
1. ルートとサービス実装（ローカルで手動確認）
2. テンプレート実装
3. 単体/統合テスト追加
4. PR 作成とレビュー
