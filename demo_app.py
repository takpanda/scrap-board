"""
簡易デモアプリケーション
デザインパターンのプレビュー用
"""
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from datetime import datetime
from markdown_it import MarkdownIt

# FastAPIアプリケーション
app = FastAPI(title="Scrap-Board Design Patterns Demo")

# 静的ファイル
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# テンプレート
templates = Jinja2Templates(directory="app/templates")

# Markdownフィルタを追加
md = MarkdownIt()

def markdown_filter(text):
    """MarkdownテキストをHTMLに変換するJinja2フィルタ"""
    if not text:
        return ""
    return md.render(text)

templates.env.filters["markdown"] = markdown_filter

# サンプルドキュメントデータ
def get_sample_document():
    return type('Document', (), {
        'id': 'sample-ai-doc',
        'title': 'AI と機械学習の最新トレンド：2024年版',
        'url': 'https://example.com/ai-trends-2024',
        'domain': 'example.com',
        'author': '田中 太郎',
        'content_text': 'AI（人工知能）と機械学習の分野は、2024年に入っても急速な進歩を続けています。特に大規模言語モデル（LLM）の発展により、自然言語処理の精度が格段に向上し、様々な業界での実用化が進んでいます。ChatGPTやGPT-4などのモデルは、従来の枠を超えて、コンテンツ生成、コード開発、データ分析など幅広い分野で活用されています。また、コンピュータビジョンの分野でも、画像認識や動画解析の精度が向上し、医療診断、自動運転、製造業での品質管理など、より実用的なアプリケーションが登場しています。一方で、AI倫理や責任あるAI開発への関心も高まっており、技術の進歩と並行して、適切なガバナンスとレギュレーションの整備が重要な課題となっています。本記事では、これらの最新動向について詳しく解説し、今後の展望についても考察します。',
        'content_md': '''# AI と機械学習の最新トレンド：2024年版

AI（人工知能）と機械学習の分野は、2024年に入っても**急速な進歩**を続けています。

## 大規模言語モデル（LLM）の進化

特に**大規模言語モデル（LLM）**の発展により、自然言語処理の精度が格段に向上し、様々な業界での実用化が進んでいます。

### 主要な活用分野

- **ChatGPT**やGPT-4などのモデル
- コンテンツ生成への活用
- コード開発の支援
- データ分析の自動化

## コンピュータビジョンの進歩

また、コンピュータビジョンの分野でも、画像認識や動画解析の精度が向上し、より実用的なアプリケーションが登場しています：

1. **医療診断** - 画像診断の精度向上
2. **自動運転** - 環境認識技術の発達  
3. **製造業** - 品質管理の自動化

## AI倫理への取り組み

一方で、AI倫理や責任あるAI開発への関心も高まっており、技術の進歩と並行して、適切な**ガバナンスとレギュレーション**の整備が重要な課題となっています。

### 重要な課題

> AI技術の発展には、技術的進歩だけでなく、社会的責任も伴います。

- プライバシー保護
- アルゴリズムの透明性
- バイアスの除去
- 社会への影響評価

## 今後の展望

2024年後半から2025年にかけて、以下の分野での更なる発展が期待されています：

- **マルチモーダルAI**の実用化
- **エッジAI**の普及拡大
- **量子機械学習**の研究加速

本記事では、これらの最新動向について詳しく解説し、今後の展望についても考察します。''',
        'published_at': datetime(2024, 1, 15),
        'fetched_at': datetime(2024, 1, 16),
        'created_at': datetime(2024, 1, 16),
        'classifications': [type('Classification', (), {
            'primary_category': 'テクノロジー/AI',
            'tags': ['機械学習', 'ChatGPT', 'コンピュータビジョン', 'AI倫理', 'LLM'],
            'confidence': 0.92
        })()]
    })()


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """ホームページ - デザインパターン一覧へリダイレクト"""
    return templates.TemplateResponse("demo_patterns_index.html", {
        "request": request
    })


@app.get("/demo/patterns", response_class=HTMLResponse)
async def design_patterns_index(request: Request):
    """デザインパターン一覧ページ"""
    return templates.TemplateResponse("demo_patterns_index.html", {
        "request": request
    })


@app.get("/demo/pattern1/{document_id}", response_class=HTMLResponse)
async def document_detail_pattern1(request: Request, document_id: str):
    """ドキュメント詳細ページ - パターン1（従来型改良版）"""
    document = get_sample_document()
    return templates.TemplateResponse("document_detail_pattern1.html", {
        "request": request,
        "document": document
    })


@app.get("/demo/pattern2/{document_id}", response_class=HTMLResponse)
async def document_detail_pattern2(request: Request, document_id: str):
    """ドキュメント詳細ページ - パターン2（分割レイアウト）"""
    document = get_sample_document()
    return templates.TemplateResponse("document_detail_pattern2.html", {
        "request": request,
        "document": document
    })


@app.get("/demo/pattern3/{document_id}", response_class=HTMLResponse)
async def document_detail_pattern3(request: Request, document_id: str):
    """ドキュメント詳細ページ - パターン3（タブベース）"""
    document = get_sample_document()
    return templates.TemplateResponse("document_detail_pattern3.html", {
        "request": request,
        "document": document
    })


@app.get("/health")
async def health_check():
    """ヘルスチェック"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("demo_app:app", host="0.0.0.0", port=8000, reload=True)