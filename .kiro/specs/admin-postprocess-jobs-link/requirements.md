# Requirements Document

## Introduction

管理画面（`/admin`）に既存のPostprocess Jobs Dashboard（`/admin/postprocess_jobs`）へのナビゲーションリンクを追加します。現在、ジョブダッシュボードは実装済みですが、管理画面からアクセスするための導線が存在しないため、管理者はURLを直接入力する必要があります。この機能追加により、管理画面から簡単にジョブモニタリングダッシュボードへアクセスできるようになり、システム運用性が向上します。

## Requirements

### Requirement 1: 管理画面へのナビゲーションリンク追加

**Objective:** 管理者として、管理画面からPostprocess Jobs Dashboardへ簡単にアクセスしたい。これにより、ジョブステータスの確認が効率化される。

#### Acceptance Criteria

1. WHEN 管理者が `/admin` ページを表示した時 THEN 管理画面は Postprocess Jobs Dashboard へのリンクを表示すること
2. WHEN 管理者が Postprocess Jobs Dashboard リンクをクリックした時 THEN システムは `/admin/postprocess_jobs` ページへ遷移すること
3. WHERE リンクが管理画面のヘッダー、サイドバー、またはメインコンテンツエリア内に配置されている場合 THE 管理画面は リンクを視覚的に識別可能な形式で表示すること
4. IF リンクがアイコンを含む場合 THEN 管理画面は 適切なアイコン（例: ダッシュボード、ジョブ、モニタリング関連）を表示すること

### Requirement 2: リンクの視覚的デザインと配置

**Objective:** 管理者として、リンクが既存の管理画面UIと一貫性を持ち、容易に発見できることを期待する。これにより、ユーザビリティが向上する。

#### Acceptance Criteria

1. WHEN 管理画面が表示された時 THEN リンクは 既存のUIコンポーネント（ボタン、ナビゲーションリンク、カード等）と同じデザインパターンを使用すること
2. IF 管理画面が他の管理機能へのリンク（例: ソース管理）を含む場合 THEN Postprocess Jobs Dashboard へのリンクは 同じセクション内に配置されること
3. WHERE リンクがテキストラベルを持つ場合 THE 管理画面は 「Postprocess Jobs Dashboard」または「ジョブダッシュボード」等の明確なラベルを表示すること
4. WHILE 管理画面が表示されている間 THE リンクは 常に表示され、隠れたり無効化されたりしないこと

### Requirement 3: アクセシビリティとレスポンシブ対応

**Objective:** 管理者として、モバイルデバイスを含むあらゆる環境からリンクにアクセスできることを期待する。これにより、運用の柔軟性が向上する。

#### Acceptance Criteria

1. WHEN 管理画面がモバイルデバイス（画面幅 < 768px）で表示された時 THEN リンクは タップ可能な十分なサイズ（最小 44x44px）で表示されること
2. IF スクリーンリーダーが使用されている場合 THEN リンクは 適切な `aria-label` または代替テキストを持つこと
3. WHERE キーボードナビゲーションが使用される場合 THE リンクは Tab キーでフォーカス可能であること
4. WHEN リンクにフォーカスが当たった時 THEN 管理画面は 視覚的なフォーカスインジケーター（アウトライン等）を表示すること

### Requirement 4: 既存機能との統合

**Objective:** 開発者として、既存のテンプレート構造やルーティングに影響を与えずにリンクを追加したい。これにより、保守性が維持される。

#### Acceptance Criteria

1. WHEN 管理画面テンプレート（`app/templates/admin/sources.html`）が編集される時 THEN 変更は 既存のHTMLレイアウト構造を破壊しないこと
2. IF 管理画面が `base.html` を継承している場合 THEN リンク追加は テンプレート継承構造を維持すること
3. WHERE 管理画面が HTMX を使用している場合 THE リンクは 標準的な `<a>` タグまたは HTMX 互換の形式で実装されること
4. WHEN リンクが追加された後 THEN 既存の管理機能（ソース作成、編集、削除等）は 正常に動作し続けること
