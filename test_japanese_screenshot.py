#!/usr/bin/env python3
"""
Japanese text screenshot validation test.
Creates a simple HTML page with Japanese text and takes a screenshot to verify rendering.
"""

import os
import tempfile
from pathlib import Path


def create_test_html():
    """Create a test HTML page with Japanese text."""
    html_content = """<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>日本語テストページ</title>
    <style>
        body {
            font-family: 'Noto Sans CJK JP', 'Hiragino Sans', 'Hiragino Kaku Gothic ProN', 'Meiryo', sans-serif;
            font-size: 16px;
            line-height: 1.6;
            margin: 40px;
            background: white;
            color: #333;
        }
        .header {
            font-size: 24px;
            font-weight: bold;
            margin-bottom: 20px;
            color: #2BB673;
        }
        .section {
            margin-bottom: 30px;
            padding: 20px;
            border: 1px solid #eee;
            border-radius: 8px;
        }
        .label {
            font-weight: bold;
            color: #666;
            margin-bottom: 10px;
        }
        .kanji { font-size: 18px; }
        .hiragana { font-size: 16px; }
        .katakana { font-size: 16px; }
        .mixed { font-size: 17px; }
    </style>
</head>
<body>
    <div class="header">
        Scrap-Board 日本語テキスト表示テスト
    </div>
    
    <div class="section">
        <div class="label">漢字テスト:</div>
        <div class="kanji">
            人工知能技術の発展により、機械学習とディープラーニングが
            自然言語処理分野で革命的な進歩を遂げています。
        </div>
    </div>
    
    <div class="section">
        <div class="label">ひらがなテスト:</div>
        <div class="hiragana">
            このページでは、にほんごのぶんしょうが
            ただしくひょうじされているかをかくにんします。
        </div>
    </div>
    
    <div class="section">
        <div class="label">カタカナテスト:</div>
        <div class="katakana">
            アプリケーション、データベース、システム、
            プログラミング、インターフェース、アルゴリズム
        </div>
    </div>
    
    <div class="section">
        <div class="label">混合テキスト:</div>
        <div class="mixed">
            AI（人工知能）システムによる日本語コンテンツの収集と管理は、
            WebスクレイピングとNLP技術を組み合わせることで実現できます。
        </div>
    </div>
    
    <div class="section">
        <div class="label">UI要素テスト:</div>
        <div>
            <button style="padding: 8px 16px; margin: 4px; border: 1px solid #2BB673; background: white; color: #2BB673; border-radius: 4px;">
                追加
            </button>
            <button style="padding: 8px 16px; margin: 4px; border: 1px solid #2BB673; background: #2BB673; color: white; border-radius: 4px;">
                保存
            </button>
            <button style="padding: 8px 16px; margin: 4px; border: 1px solid #666; background: white; color: #666; border-radius: 4px;">
                キャンセル
            </button>
        </div>
    </div>
    
    <div class="section">
        <div class="label">数値と記号:</div>
        <div>
            2024年1月15日、価格：¥12,580、評価：92%、
            記号：「」『』【】〈〉（）・→←↑↓
        </div>
    </div>
    
    <div style="margin-top: 40px; text-align: center; color: #666; font-size: 14px;">
        このテストページが正しく表示されていれば、日本語フォント設定は正常です。
    </div>
</body>
</html>"""
    
    # Create temporary HTML file
    temp_dir = Path(tempfile.gettempdir())
    html_file = temp_dir / "japanese_test.html"
    html_file.write_text(html_content, encoding='utf-8')
    
    return html_file


def take_screenshot_sync():
    """Take a screenshot using Playwright synchronously."""
    from playwright.sync_api import sync_playwright
    
    html_file = create_test_html()
    screenshot_path = Path(tempfile.gettempdir()) / "japanese_test_screenshot.png"
    
    print(f"📄 Created test HTML: {html_file}")
    print(f"📸 Screenshot will be saved to: {screenshot_path}")
    
    with sync_playwright() as p:
        # Launch browser with Japanese text support
        browser = p.chromium.launch(
            headless=True,
            args=[
                '--font-render-hinting=none',
                '--disable-font-subpixel-positioning',
                '--disable-gpu-sandbox',
                '--no-sandbox',
                '--lang=ja-JP',
                '--accept-lang=ja,ja-JP,en',
                '--force-device-scale-factor=1',
                '--disable-features=VizDisplayCompositor',
                '--disable-dev-shm-usage',
                '--disable-extensions',
                '--disable-background-timer-throttling',
                '--disable-backgrounding-occluded-windows',
                '--disable-renderer-backgrounding',
                '--font-config-file=/etc/fonts/fonts.conf',
                '--enable-font-antialiasing',
                '--disable-lcd-text',
                '--default-encoding=utf-8',
                '--disable-gpu',
                '--disable-software-rasterizer',
            ]
        )
        
        context = browser.new_context(
            locale="ja-JP",
            timezone_id="Asia/Tokyo",
            viewport={"width": 1280, "height": 1024},
            extra_http_headers={
                "Accept-Language": "ja,ja-JP;q=0.9,en;q=0.8",
                "Accept-Charset": "UTF-8"
            },
            font_size=16,
            device_scale_factor=1.0,
        )
        
        page = context.new_page()
        
        # Navigate to the test page
        page.goto(f"file://{html_file}")
        
        # Wait for page to load
        page.wait_for_load_state("networkidle")
        
        # Take screenshot
        page.screenshot(path=str(screenshot_path), full_page=True)
        
        browser.close()
    
    print(f"✅ Screenshot saved: {screenshot_path}")
    return screenshot_path


def main():
    """Main test function."""
    print("🧪 Testing Japanese text rendering in Playwright screenshots...\n")
    
    try:
        screenshot_path = take_screenshot_sync()
        
        # Check if screenshot was created
        if Path(screenshot_path).exists():
            size = Path(screenshot_path).stat().st_size
            print(f"✅ Screenshot created successfully ({size} bytes)")
            print(f"📂 Location: {screenshot_path}")
            print("\n📋 Next steps:")
            print("1. Open the screenshot to verify Japanese text is rendered correctly")
            print("2. Check that all text is clear and not garbled")
            print("3. If text appears garbled, check font installation and browser configuration")
        else:
            print("❌ Screenshot was not created")
            return False
            
    except Exception as e:
        print(f"❌ Error during screenshot test: {e}")
        return False
    
    return True


if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)