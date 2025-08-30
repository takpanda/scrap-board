# Playwright 日本語テスト設定ガイド

## 概要

このプロジェクトには、日本語テキストの文字化けを防ぐ Playwright ブラウザテスト設定が含まれています。

## 設定ファイル

### 1. `playwright.config.py`
- ブラウザ起動時の日本語ロケール設定
- フォントレンダリング最適化
- 日本語フォント対応引数

### 2. `conftest.py`
- pytest と Playwright の統合設定
- テストサーバーの自動起動
- 日本語ブラウザコンテキスト設定

### 3. `tests/test_browser.py`
- 日本語テキストレンダリングのテスト
- フォーム入力での日本語文字サポート
- UI要素の日本語表示確認

## インストール手順

```bash
# 1. Playwright とプラグインのインストール
pip install playwright pytest-playwright

# 2. 日本語フォントのインストール（Ubuntu/Debian）
sudo apt-get update
sudo apt-get install -y fonts-noto-cjk fonts-liberation

# 3. ブラウザのインストール
playwright install chromium

# 4. 設定の確認
python verify_playwright_config.py
```

## テスト実行

```bash
# ブラウザテストのみ実行
pytest tests/test_browser.py -v -m browser

# 単体テストのみ実行  
pytest tests/test_basic.py -v -m unit

# 全テスト実行
pytest -v

# 高速テスト（ブラウザテストをスキップ）
pytest -v -m "not browser"
```

## 文字化け防止の設定ポイント

### 1. ロケール設定
```python
{
    "locale": "ja-JP",
    "timezone_id": "Asia/Tokyo",
    "extra_http_headers": {
        "Accept-Language": "ja,ja-JP;q=0.9,en;q=0.8",
        "Accept-Charset": "UTF-8"
    }
}
```

### 2. ブラウザ引数
```python
args=[
    '--lang=ja-JP',
    '--accept-lang=ja,ja-JP,en',
    '--font-render-hinting=none',
    '--disable-font-subpixel-positioning'
]
```

### 3. フォント最適化
- Noto CJK フォントの使用
- フォントヒンティングの無効化
- サブピクセルポジショニングの無効化

## テスト対象

### 日本語テキストレンダリング
- ✅ ホームページの日本語見出し
- ✅ ナビゲーションメニューの日本語
- ✅ フォーム項目の日本語ラベル
- ✅ カテゴリ選択の日本語オプション

### 入力機能
- ✅ 日本語URL入力
- ✅ 日本語検索クエリ
- ✅ フォーム入力での日本語サポート

### レンダリング品質
- ✅ フォントサイズと幅の適切性
- ✅ スクリーンショット撮影可能性
- ✅ UTF-8エンコーディング確認

## トラブルシューティング

### ブラウザインストールエラー
```bash
# エラーが発生した場合、手動でインストール
export PLAYWRIGHT_BROWSERS_PATH=~/.cache/ms-playwright
playwright install --with-deps chromium
```

### フォント問題
```bash
# 日本語フォントの確認
fc-list :lang=ja

# 追加フォントのインストール
sudo apt-get install fonts-noto-cjk-extra fonts-takao
```

### テストサーバーエラー
```bash
# FastAPI サーバーを手動起動してテスト
uvicorn app.main:app --host 127.0.0.1 --port 8000 &
pytest tests/test_browser.py -v
```

## CI/CD での使用

GitHub Actions などの CI 環境で使用する場合：

```yaml
- name: Install Japanese fonts
  run: |
    sudo apt-get update
    sudo apt-get install -y fonts-noto-cjk

- name: Install Playwright
  run: |
    pip install playwright pytest-playwright
    playwright install --with-deps chromium

- name: Run browser tests
  run: pytest tests/test_browser.py -v
```

## 設定の検証

プロジェクトルートで以下を実行して設定を確認：

```bash
python verify_playwright_config.py
```

正常に設定されている場合、すべての項目に ✅ が表示されます。