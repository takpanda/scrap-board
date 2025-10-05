# Requirements Document

## Project Description (Input)
記事カードの「詳細を表示」ボタンをアイコンのみのシンプルな表示に変更する

## Introduction
記事カードのパーソナライズ情報セクションにある「詳細を表示」トグルボタンを、テキストラベルを削除してアイコンのみのシンプルなデザインに変更します。これにより、UIがよりクリーンになり、視覚的なノイズを減らしつつ、機能性は維持します。

## Requirements

### Requirement 1: ボタン表示の変更
**Objective:** ユーザーとして、記事カードのパーソナライズ情報セクションで詳細を展開する際に、よりシンプルでクリーンなUIを体験したい

#### Acceptance Criteria

1. WHEN パーソナライズ情報セクションが表示される THEN 記事カードシステム SHALL 「詳細を表示」テキストを表示せず、アイコンのみのトグルボタンを表示する
2. WHEN トグルボタンが閉じた状態である THEN 記事カードシステム SHALL chevron-downアイコンを表示する
3. WHEN トグルボタンが開いた状態である THEN 記事カードシステム SHALL chevron-upアイコンを表示する
4. WHERE トグルボタンが配置される THE 記事カードシステム SHALL パーソナライズ情報ヘッダーの右端に配置する

### Requirement 2: アクセシビリティの維持
**Objective:** スクリーンリーダーユーザーとして、テキストラベルがなくてもボタンの機能を理解できるようにしたい

#### Acceptance Criteria

1. WHEN トグルボタンが閉じた状態である THEN 記事カードシステム SHALL aria-label属性に「おすすめの詳細を表示」を設定する
2. WHEN トグルボタンが開いた状態である THEN 記事カードシステム SHALL aria-label属性を「おすすめの詳細を非表示」に更新する
3. WHEN トグルボタンの状態が変化する THEN 記事カードシステム SHALL aria-expanded属性をtrueまたはfalseに適切に更新する

### Requirement 3: インタラクション動作の保持
**Objective:** ユーザーとして、既存のトグル機能が正常に動作し続けることを期待する

#### Acceptance Criteria

1. WHEN ユーザーがトグルボタンをクリックする THEN 記事カードシステム SHALL パーソナライズ詳細セクションの表示/非表示を切り替える
2. WHEN ユーザーがトグルボタンをクリックする THEN 記事カードシステム SHALL アイコンをchevron-downとchevron-upの間で切り替える
3. WHEN 詳細セクションが展開される THEN 記事カードシステム SHALL スムーズなアニメーション効果を表示する

### Requirement 4: 既存スタイルとの整合性
**Objective:** デザイナーとして、新しいアイコンボタンが既存のデザインシステムと調和することを確認したい

#### Acceptance Criteria

1. WHEN トグルボタンが表示される THEN 記事カードシステム SHALL 既存のテキスト色（text-graphite / hover:text-emerald-700）を維持する
2. WHEN トグルボタンが表示される THEN 記事カードシステム SHALL 既存のホバー効果とトランジション（transition-colors）を維持する
3. WHEN アイコンが表示される THEN 記事カードシステム SHALL アイコンサイズを適切に設定する（w-4 h-4またはw-5 h-5）
