# Playwright 日本語テスト設定ガイド

## 概要

このプロジェクトには、日本語テキストの文字化けを防ぐ Playwright ブラウザテスト設定が含まれています。

## 文字化け防止の設定ポイント

### 1. ロケール設定
- `locale: "ja-JP"` - 日本語ロケール
- `timezone_id: "Asia/Tokyo"` - 日本時間
- `Accept-Language: "ja,ja-JP;q=0.9,en;q=0.8"` - 言語ヘッダー

### 2. ブラウザ引数
- `--lang=ja-JP` - UI言語設定
- `--font-render-hinting=none` - フォントヒンティング無効化
- `--disable-font-subpixel-positioning` - サブピクセル位置調整無効化
- `--enable-font-antialiasing` - フォントアンチエイリアス有効化
- `--default-encoding=utf-8` - デフォルト文字エンコーディング

### 3. フォント最適化
- Noto CJK フォントの使用
- フォントヒンティングの無効化
- サブピクセルポジショニングの無効化

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

### 4. `setup_fonts.py` **[新規]**
- 日本語フォントの自動インストール
- フォント設定ファイルの作成
- レンダリング最適化設定

## インストール手順

```bash
# 1. Playwright とプラグインのインストール
pip install playwright pytest-playwright

# 2. 日本語フォントの設定（推奨）
python setup_fonts.py

# 3. ブラウザのインストール
playwright install chromium

# 4. 設定の確認
python verify_playwright_config.py
```

## 高速セットアップ

```bash
# 全自動セットアップ
./run_browser_tests.sh
```

## テスト実行

```bash
# ブラウザテストのみ実行
pytest tests/test_browser.py -v -m browser

# 単体テストのみ実行  
pytest tests/test_basic.py -v -m unit

# 全テスト実行
pytest -v

# 日本語テキスト表示テスト
python test_japanese_screenshot.py
```

## CI/CD環境での設定

### GitHub Actions
```yaml
- name: Setup Japanese fonts
  run: |
    sudo apt-get update
    sudo apt-get install -y fonts-noto-cjk fonts-liberation
    python setup_fonts.py

- name: Install Playwright
  run: |
    pip install playwright pytest-playwright
    playwright install chromium
```

### Docker環境
```dockerfile
# Dockerfile に追加
RUN apt-get update && apt-get install -y \
    fonts-noto-cjk \
    fonts-liberation \
    fontconfig \
    && rm -rf /var/lib/apt/lists/*

COPY setup_fonts.py .
RUN python setup_fonts.py
```

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

# フォント設定の再作成
python setup_fonts.py
```

### 文字化け問題
```bash
# 日本語テキスト表示テスト
python test_japanese_screenshot.py

# 設定ファイル確認
cat ~/.config/fontconfig/fonts.conf
```

### テストサーバーエラー
```bash
# FastAPI サーバーを手動起動してテスト
uvicorn app.main:app --host 127.0.0.1 --port 8000 &
pytest tests/test_browser.py -v
```

## 最新の変更点

### v1.1 - 文字化け問題修正 (2024/09)
- **ブラウザ引数の強化**: フォントレンダリング最適化オプション追加
- **フォント設定自動化**: `setup_fonts.py` による自動フォント設定
- **CI対応**: GitHub Actions での日本語フォント対応改善
- **テスト強化**: 日本語テキスト表示検証ツール追加
- **設定最適化**: Noto CJK フォントの優先設定

## テスト対象

### 基本機能
- ✅ ページナビゲーション
- ✅ 日本語テキスト表示確認
- ✅ フォーム操作（URL入力、検索）

### レンダリング品質
- ✅ フォントサイズと幅の適切性
- ✅ スクリーンショット撮影可能性
- ✅ UTF-8エンコーディング確認
- ✅ CJK文字の正確な表示
- ✅ 混合テキスト（漢字、ひらがな、カタカナ）の表示

### UI要素
- ✅ ナビゲーションメニューの日本語
- ✅ ボタンラベルの日本語
- ✅ フォームフィールドの日本語
- ✅ エラーメッセージの日本語
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