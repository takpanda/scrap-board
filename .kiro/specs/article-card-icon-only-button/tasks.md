# 実装タスク

## タスク概要
記事カードのパーソナライズ情報セクションにある「詳細を表示」トグルボタンを、テキストラベルを削除してアイコンのみのシンプルなUIに変更します。テンプレートとJavaScriptの2ファイルを最小限修正することで、クリーンなデザインとアクセシビリティを両立させます。

---

- [x] 1. テンプレートのトグルボタンをアイコンのみの表示に変更
- [x] 1.1 トグルボタンのHTML構造を簡略化
  - テキストラベル要素（data-personalized-toggle-text属性を持つspan要素）を完全に削除
  - アイコンとテキストの間隔を制御していたgap-1クラスを削除（アイコンのみなので不要）
  - アイコンサイズをw-3 h-3からw-4 h-4に拡大して視認性を向上
  - 既存のaria-label、aria-expanded属性は維持（アクセシビリティ保持）
  - ml-auto、inline-flex、items-center、px-2、py-0.5、text-xs、text-graphite、hover:text-emerald-700、transition-colorsのクラスは維持（スタイル整合性保持）
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 4.1, 4.2, 4.3_

- [x] 2. JavaScriptのトグル処理からテキスト更新ロジックを削除
- [x] 2.1 PersonalizedSortControllerのsetupToggleButtonメソッドを修正
  - toggleText変数の宣言と要素取得処理（querySelector呼び出し）を削除
  - 展開時のtoggleText.textContent = "詳細を非表示"の処理を削除
  - 折りたたみ時のtoggleText.textContent = "詳細を表示"の処理を削除
  - toggleTextのnullチェック（if (toggleText)）を削除
  - toggleIconのアイコン切り替え処理（chevron-down ↔ chevron-up）は維持
  - aria-label動的更新処理（おすすめの詳細を表示 ↔ おすすめの詳細を非表示）は維持
  - aria-expanded属性更新処理（true ↔ false）は維持
  - _Requirements: 2.1, 2.2, 2.3, 3.1, 3.2_

- [x] 3. ブラウザでの手動テストによる機能検証
- [x] 3.1 視覚的表示とインタラクションの検証
  - 記事カードのパーソナライズ情報セクションでトグルボタンがアイコンのみで表示されることを確認
  - テキストラベル（「詳細を表示」「詳細を非表示」）が表示されていないことを確認
  - トグルボタンをクリックして詳細セクションが正しく展開・折りたたみされることを確認
  - アイコンがchevron-downとchevron-upの間で正しく切り替わることを確認
  - ホバー時にtext-emerald-700色に変化することを確認
  - transition-colorsアニメーションが滑らかに動作することを確認
  - _Requirements: 1.1, 1.2, 1.3, 3.1, 3.2, 3.3, 4.1, 4.2_

- [x] 3.2 アクセシビリティとクロスブラウザ検証
  - ブラウザの開発者ツールでaria-label属性を確認（閉じた状態: "おすすめの詳細を表示"、開いた状態: "おすすめの詳細を非表示"）
  - aria-expanded属性が正しく更新されること（true ↔ false）を確認
  - キーボードナビゲーション（Tab、Enter）でトグルボタンが操作可能であることを確認
  - 複数の記事カードが表示されたページで各カードのトグルボタンが独立して動作することを確認
  - Chrome、Firefox、Safariなど主要ブラウザで表示と動作を確認
  - モバイル、タブレット、デスクトップの各画面サイズでアイコンボタンが適切に表示されることを確認
  - _Requirements: 2.1, 2.2, 2.3, 3.1_
