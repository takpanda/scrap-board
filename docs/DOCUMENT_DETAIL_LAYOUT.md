# ドキュメント詳細ページのレイアウト改善

## 概要
このドキュメントは、ドキュメント詳細ページ（`document_detail.html`）のレイアウト全体見直しで実装された改善点をまとめたものです。

## 実装された改善

### 1. レスポンシブレイアウトの強化

#### グリッドレイアウトの改善
- **変更前**: `md:grid-cols-3` (768px以上で3カラム)
- **変更後**: `lg:grid-cols-3` (1024px以上で3カラム)
- **効果**: タブレット端末で1カラム表示となり、コンテンツの可読性が向上

#### コンテナ幅の最適化
- **変更前**: `max-w-6xl` (72rem / 1152px)
- **変更後**: `max-w-7xl` (80rem / 1280px)
- **効果**: 大画面での表示領域が広がり、情報密度が向上

#### レスポンシブパディング
```html
<!-- 変更前 -->
<div class="max-w-6xl mx-auto px-6 py-8">

<!-- 変更後 -->
<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 sm:py-8">
```
- **効果**: 画面サイズに応じた適切な余白で、モバイルでの表示領域が拡大

### 2. 情報のグルーピング・視認性向上

#### カードスペーシングの最適化
```css
/* デスクトップ */
.dify-header-card,
.dify-content-card {
    padding: 1.5rem;
    margin-bottom: 1.5rem;
}

/* タブレット (max-width: 1024px) */
.dify-header-card,
.dify-content-card {
    padding: 1.25rem;
}

/* モバイル (max-width: 640px) */
.dify-header-card,
.dify-content-card {
    padding: 1rem;
    border-radius: 8px;
}
```

#### セクション見出しの階層化
```css
.dify-section-title {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 1.125rem;  /* デスクトップ */
    font-weight: 600;
    color: var(--dify-gray-800, #1F2328);
}

/* タブレット */
@media (max-width: 1024px) {
    .dify-section-title {
        font-size: 1rem;
    }
}

/* モバイル */
@media (max-width: 640px) {
    .dify-section-title {
        font-size: 0.9375rem;
    }
}
```

#### タイトル・サムネイルレイアウトの改善
```css
.dify-title-with-thumb {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    margin-bottom: 1rem;
    padding-bottom: 1rem;
    border-bottom: 1px solid var(--dify-border-light, #E4E7EA);
}

.dify-title-with-thumb .dify-thumb {
    width: 56px;
    height: 56px;
    min-width: 56px;
    object-fit: cover;
    border-radius: 8px;
}

.dify-title-with-thumb .dify-title {
    flex: 1;
    font-size: 1.5rem;
    font-weight: 600;
    line-height: 1.3;
    word-break: break-word;
}
```

### 3. UIコンポーネントの統一

#### ボタンスタイルの改善
```css
.dify-toggle-btn {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.5rem 1rem;
    background: var(--dify-gray-50, #FAFBFC);
    border: 1px solid var(--dify-border-light, #E4E7EA);
    border-radius: 8px;
    font-size: 0.875rem;
    font-weight: 500;
    transition: all 0.2s ease;
}

.dify-toggle-btn:hover {
    background: var(--dify-gray-100, #F1F3F4);
    border-color: var(--dify-border, #D0D4D9);
    transform: translateY(-1px);
}
```

#### タグデザインの統一
```css
.dify-tag-primary {
    display: inline-flex;
    align-items: center;
    gap: 0.375rem;
    padding: 0.375rem 0.75rem;
    background: linear-gradient(135deg, rgba(16, 185, 129, 0.1), rgba(16, 185, 129, 0.05));
    color: #059669;
    border: 1px solid rgba(16, 185, 129, 0.2);
    border-radius: 6px;
    font-size: 0.8125rem;
    font-weight: 500;
}

.dify-tag-secondary {
    display: inline-flex;
    align-items: center;
    padding: 0.375rem 0.75rem;
    background: var(--dify-gray-100, #F1F3F4);
    color: var(--dify-gray-600, #4A5056);
    border: 1px solid var(--dify-border-light, #E4E7EA);
    border-radius: 6px;
    font-size: 0.8125rem;
    font-weight: 500;
}
```

### 4. アクセシビリティの向上

#### フォーカス状態の改善
```css
.dify-toggle-btn:focus-visible,
.dify-back-btn:focus-visible,
button[aria-label="ブックマーク"]:focus-visible {
    outline: 2px solid var(--dify-primary, #1C64F2);
    outline-offset: 2px;
}
```

#### タッチターゲットの最適化
```css
/* モバイルデバイス用の最小タッチ領域 */
@media (hover: none) and (pointer: coarse) {
    .dify-toggle-btn,
    .dify-back-btn,
    button[aria-label="ブックマーク"] {
        min-height: 44px;
        min-width: 44px;
    }
}
```

#### ARIAラベルの追加
```html
<!-- ボタンにaria-labelを追加 -->
<button
    onclick="toggleFullContent()"
    id="content-toggle"
    class="dify-toggle-btn"
    aria-label="全文表示切り替え"
>
```

### 5. コードクリーンアップ

#### 削除された重複スタイル
- `.dify-title-with-thumb` の重複定義（6箇所→1箇所に統合）
- 競合する `display: flex` と `display: grid` の定義
- 不要な `!important` フラグの削除

#### 削除されたクラス
- `overflow-x-auto` / `overflow-x-visible` - 横スクロール問題の原因となっていた
- 不要な Tailwind ユーティリティクラスの重複

## ブレークポイント

本実装では以下のブレークポイントを使用しています：

| 名称 | 幅 | 説明 |
|------|-----|------|
| モバイル | < 640px | スマートフォン |
| タブレット | 640px - 1024px | タブレット、小型ノートPC |
| デスクトップ | ≥ 1024px | 大画面デバイス |

## レスポンシブ動作

### モバイル（< 640px）
- 1カラムレイアウト
- padding: 1rem
- font-size: 0.9375rem (section titles)
- サムネイル: 44px × 44px
- タイトル: 1.125rem

### タブレット（640px - 1024px）
- 1カラムレイアウト
- padding: 1.25rem
- font-size: 1rem (section titles)
- サムネイル: 56px × 56px
- タイトル: 1.5rem

### デスクトップ（≥ 1024px）
- 3カラムレイアウト（メインコンテンツ2 : サイドバー1）
- padding: 1.5rem
- font-size: 1.125rem (section titles)
- サムネイル: 56px × 56px
- タイトル: 1.5rem

## CSS変数の使用

一貫したデザインのため、以下のCSS変数を使用：

```css
:root {
    /* Dify Primary Brand Colors */
    --dify-primary: #1C64F2;
    --dify-primary-light: #3F83F8;
    
    /* Dify Gray Scale */
    --dify-gray-50: #FAFBFC;
    --dify-gray-100: #F1F3F4;
    --dify-gray-200: #E4E7EA;
    --dify-gray-600: #4A5056;
    --dify-gray-700: #2D3338;
    --dify-gray-800: #1F2328;
    --dify-gray-900: #0F1419;
    
    /* Borders */
    --dify-border-light: #E4E7EA;
    --dify-border: #D0D4D9;
    
    /* Surface */
    --dify-surface: #FFFFFF;
}
```

## パフォーマンス最適化

### トランジション
- `transition: all 0.2s ease` - 滑らかなUI遷移
- `transform: translateY(-1px)` - GPU加速による高速なホバーエフェクト

### 画像の遅延読み込み
```html
<img loading="lazy" />
```

## テスト要件

以下の項目を手動でテストすることを推奨：

1. **レスポンシブ表示**
   - [ ] モバイル（375px、390px）
   - [ ] タブレット（768px、1024px）
   - [ ] デスクトップ（1280px、1920px）

2. **操作性**
   - [ ] タップ/クリック領域の適切さ
   - [ ] ボタンのホバー/フォーカス状態
   - [ ] キーボードナビゲーション

3. **視認性**
   - [ ] テキストの可読性
   - [ ] コントラスト比
   - [ ] カード間の視覚的区切り

4. **機能**
   - [ ] 全文表示切り替え
   - [ ] ブックマーク機能
   - [ ] 関連ドキュメントの読み込み
   - [ ] AI要約の生成

## 今後の改善案

1. **ダークモード対応**
   - CSS変数を使用しているため、ダークモードの追加が容易

2. **アニメーション強化**
   - カード表示時のフェードインアニメーション
   - スムーズなレイアウトシフト

3. **カスタマイズ機能**
   - ユーザーによるフォントサイズ調整
   - カラーテーマの選択

4. **プリント対応**
   - 印刷用CSSの追加
   - 不要な要素の非表示化

## 参考リンク

- [Tailwind CSS - Responsive Design](https://tailwindcss.com/docs/responsive-design)
- [MDN - CSS Grid Layout](https://developer.mozilla.org/en-US/docs/Web/CSS/CSS_Grid_Layout)
- [WCAG 2.1 - Touch Target Size](https://www.w3.org/WAI/WCAG21/Understanding/target-size.html)
