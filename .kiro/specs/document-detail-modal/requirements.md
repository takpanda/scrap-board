# Requirements Document

## 概要
記事詳細をポップアップ（モーダル）表示に変更することで、記事一覧からの操作性を改善する。現在の実装では記事詳細は別ページ遷移となっており、詳細から戻った際に一覧が先頭にリセットされる問題がある。モーダル表示により、ユーザーは一覧のスクロール位置を維持したまま記事を閲覧でき、複数の記事を素早く確認できるようになる。

## Requirements

### Requirement 1: モーダル表示による記事詳細の閲覧
**Objective:** ユーザーとして、記事一覧のスクロール位置を維持したまま記事詳細を確認したい。これにより、複数の記事を効率的に閲覧できる。

#### Acceptance Criteria
1. WHEN ユーザーが記事一覧で記事カードの詳細表示ボタンをクリックする THEN Scrap-Boardアプリケーション SHALL モーダルウィンドウで記事詳細を表示する
2. WHILE モーダルが表示されている THE Scrap-Boardアプリケーション SHALL 背景の記事一覧を表示したまま維持する
3. WHEN モーダルが表示される THEN Scrap-Boardアプリケーション SHALL 背景にオーバーレイ（半透明の暗いレイヤー）を表示する
4. WHERE モーダルが表示されている THE Scrap-Boardアプリケーション SHALL 背景の記事一覧のスクロール位置を保持する

### Requirement 2: モーダルの閉じる操作
**Objective:** ユーザーとして、直感的な操作でモーダルを閉じて記事一覧に戻りたい。これにより、スムーズな閲覧体験を提供する。

#### Acceptance Criteria
1. WHEN ユーザーがモーダル内の閉じるボタン（×アイコン）をクリックする THEN Scrap-Boardアプリケーション SHALL モーダルを閉じて記事一覧を表示する
2. WHEN ユーザーがモーダル外の背景オーバーレイをクリックする THEN Scrap-Boardアプリケーション SHALL モーダルを閉じて記事一覧を表示する
3. WHEN ユーザーがESCキーを押下する AND モーダルが開いている THEN Scrap-Boardアプリケーション SHALL モーダルを閉じて記事一覧を表示する
4. WHEN モーダルが閉じられる THEN Scrap-Boardアプリケーション SHALL 記事一覧の元のスクロール位置を復元する

### Requirement 3: モーダル内での記事詳細表示
**Objective:** ユーザーとして、モーダル内で現在の記事詳細ページと同等の情報を閲覧したい。これにより、詳細情報へのアクセス性を維持する。

#### Acceptance Criteria
1. WHEN モーダルが表示される THEN Scrap-Boardアプリケーション SHALL 記事のタイトルを表示する
2. WHEN モーダルが表示される THEN Scrap-Boardアプリケーション SHALL 記事の本文（Markdown形式）を表示する
3. WHEN モーダルが表示される THEN Scrap-Boardアプリケーション SHALL 記事のメタデータ（カテゴリ、タグ、公開日、ソース）を表示する
4. WHEN モーダルが表示される AND 記事にサムネイル画像が存在する THEN Scrap-Boardアプリケーション SHALL サムネイル画像を表示する
5. WHEN モーダルが表示される THEN Scrap-Boardアプリケーション SHALL 元のURL、Reader Mode、類似記事へのリンクを表示する

### Requirement 4: モーダル内でのインタラクション機能
**Objective:** ユーザーとして、モーダル内で記事に対する操作（ブックマーク、削除等）を実行したい。これにより、一覧に戻ることなく記事を管理できる。

#### Acceptance Criteria
1. WHEN ユーザーがモーダル内のブックマークボタンをクリックする THEN Scrap-Boardアプリケーション SHALL 記事をブックマークに追加する
2. WHEN ユーザーがモーダル内のブックマーク解除ボタンをクリックする AND 記事が既にブックマーク済み THEN Scrap-Boardアプリケーション SHALL ブックマークを解除する
3. WHEN ブックマーク操作が完了する THEN Scrap-Boardアプリケーション SHALL モーダル内のブックマーク状態表示を更新する
4. WHEN ブックマーク操作が完了する THEN Scrap-Boardアプリケーション SHALL 背景の記事一覧のブックマーク状態を更新する

### Requirement 5: モーダルのレスポンシブデザイン
**Objective:** ユーザーとして、デバイスサイズに応じた最適なモーダル表示で記事を閲覧したい。これにより、デスクトップとモバイルの両方で快適な閲覧体験を提供する。

#### Acceptance Criteria
1. WHERE デスクトップ画面（幅768px以上）でモーダルが表示される THE Scrap-Boardアプリケーション SHALL 画面中央に最大幅800pxのモーダルを表示する
2. WHERE モバイル画面（幅768px未満）でモーダルが表示される THE Scrap-Boardアプリケーション SHALL 画面全体にモーダルを表示する
3. WHEN モーダル内のコンテンツが画面高さを超える THEN Scrap-Boardアプリケーション SHALL モーダル内にスクロールバーを表示する
4. WHILE モーダルが表示されている THE Scrap-Boardアプリケーション SHALL 背景のスクロールを無効化する

### Requirement 6: URL管理とブラウザ履歴の統合
**Objective:** ユーザーとして、モーダルを開いた状態をURLとして共有したり、ブラウザの戻るボタンでモーダルを閉じたい。これにより、標準的なWebブラウジング体験を提供する。

#### Acceptance Criteria
1. WHEN ユーザーが記事詳細モーダルを開く THEN Scrap-Boardアプリケーション SHALL URL履歴に記事IDを含むエントリを追加する
2. WHEN ユーザーがブラウザの戻るボタンをクリックする AND モーダルが開いている THEN Scrap-Boardアプリケーション SHALL モーダルを閉じて記事一覧を表示する
3. WHEN ユーザーが記事詳細のURLを直接開く THEN Scrap-Boardアプリケーション SHALL 記事一覧をロードした後にモーダルを自動的に開く
4. WHEN ユーザーがモーダルを閉じる THEN Scrap-Boardアプリケーション SHALL URL履歴から記事IDエントリを削除する

### Requirement 7: パフォーマンスとアクセシビリティ
**Objective:** ユーザーとして、高速で応答性の高いモーダル表示とアクセシブルな操作を体験したい。これにより、すべてのユーザーに快適な閲覧体験を提供する。

#### Acceptance Criteria
1. WHEN ユーザーが記事詳細を開く THEN Scrap-Boardアプリケーション SHALL 500ms以内にモーダルを表示する
2. WHEN モーダルが開く THEN Scrap-Boardアプリケーション SHALL キーボードフォーカスをモーダル内の最初の操作可能要素に移動する
3. WHILE モーダルが開いている THE Scrap-Boardアプリケーション SHALL キーボードフォーカスをモーダル内に制限する（フォーカストラップ）
4. WHEN モーダルが表示される THEN Scrap-Boardアプリケーション SHALL スクリーンリーダー向けにARIA属性（role="dialog", aria-modal="true"）を設定する
5. WHEN モーダルが閉じる THEN Scrap-Boardアプリケーション SHALL キーボードフォーカスを元の記事カードのボタンに戻す
