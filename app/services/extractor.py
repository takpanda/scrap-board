import trafilatura
import httpx
from typing import Optional, Dict, Any
from urllib.parse import urlparse
import hashlib
import logging
from datetime import datetime
import asyncio
import tempfile
import os

# PDF処理
try:
    from docling.document_converter import DocumentConverter
    DOCLING_AVAILABLE = True
except ImportError:
    DOCLING_AVAILABLE = False
    
try:
    from pdfminer.high_level import extract_text
    PDFMINER_AVAILABLE = True  
except ImportError:
    PDFMINER_AVAILABLE = False

logger = logging.getLogger(__name__)


class ContentExtractor:
    """コンテンツ抽出サービス"""
    
    def __init__(self):
        self.user_agent = "Scrap-Board/1.0 (+https://github.com/takpanda/scrap-board)"
    
    async def extract_from_url(self, url: str) -> Optional[Dict[str, Any]]:
        """URLからコンテンツを抽出"""
        try:
            async with httpx.AsyncClient(
                headers={"User-Agent": self.user_agent},
                timeout=30.0,
                follow_redirects=True
            ) as client:
                response = await client.get(url)
                response.raise_for_status()
                
                # HTMLコンテンツ抽出
                extracted = trafilatura.extract(
                    response.text,
                    output_format='markdown',
                    include_comments=False,
                    include_links=False,
                    include_images=True,
                    include_tables=True,
                    favor_precision=True
                )
                
                if not extracted:
                    logger.warning(f"Failed to extract content from {url}")
                    return None
                
                # メタデータ抽出
                metadata = trafilatura.extract_metadata(response.text)
                
                # ドメイン抽出
                domain = urlparse(url).netloc
                
                # ハッシュ生成
                content_hash = hashlib.sha256(extracted.encode()).hexdigest()
                
                # 言語検出
                lang = self._detect_language(extracted)
                
                return {
                    "url": url,
                    "domain": domain,
                    "title": metadata.title if metadata and metadata.title else "無題",
                    "author": metadata.author if metadata and metadata.author else None,
                    "published_at": self._parse_date(metadata.date) if metadata and metadata.date else None,
                    "content_md": extracted,
                    "content_text": trafilatura.extract(response.text, output_format='txt') or "",
                    "hash": content_hash,
                    "lang": lang
                }
                
        except Exception as e:
            logger.error(f"URL extraction error for {url}: {e}")
            return None
    
    async def extract_from_pdf(self, file_path: str, original_filename: str) -> Optional[Dict[str, Any]]:
        """PDFファイルからコンテンツを抽出"""
        
        # Doclingを最初に試行
        if DOCLING_AVAILABLE:
            try:
                converter = DocumentConverter()
                result = converter.convert(file_path)
                
                if result and result.document:
                    content_md = result.document.export_to_markdown()
                    content_text = result.document.export_to_text()
                    
                    if content_md and content_text:
                        return self._create_pdf_result(content_md, content_text, original_filename)
                        
            except Exception as e:
                logger.warning(f"Docling extraction failed, trying pdfminer: {e}")
        
        # フォールバック: pdfminer.six
        if PDFMINER_AVAILABLE:
            try:
                content_text = extract_text(file_path)
                if content_text.strip():
                    # シンプルなMarkdown変換
                    content_md = self._text_to_markdown(content_text)
                    return self._create_pdf_result(content_md, content_text, original_filename)
                    
            except Exception as e:
                logger.error(f"PDFminer extraction failed: {e}")
        
        logger.error("PDF extraction failed: No available PDF processor")
        return None
    
    def _create_pdf_result(self, content_md: str, content_text: str, filename: str) -> Dict[str, Any]:
        """PDF抽出結果を作成"""
        content_hash = hashlib.sha256(content_text.encode()).hexdigest()
        lang = self._detect_language(content_text)
        
        return {
            "url": None,
            "domain": "pdf",
            "title": filename,
            "author": None,
            "published_at": None,
            "content_md": content_md,
            "content_text": content_text,
            "hash": content_hash,
            "lang": lang
        }
    
    def _text_to_markdown(self, text: str) -> str:
        """プレーンテキストを簡単なMarkdownに変換"""
        lines = text.split('\n')
        markdown_lines = []
        
        for line in lines:
            line = line.strip()
            if not line:
                markdown_lines.append('')
                continue
                
            # 大文字が多い行をヘッダーとして扱う
            if len(line) > 3 and line.isupper():
                markdown_lines.append(f"## {line}")
            else:
                markdown_lines.append(line)
        
        return '\n'.join(markdown_lines)
    
    def _detect_language(self, text: str) -> str:
        """言語検出"""
        try:
            import langdetect
            return langdetect.detect(text)
        except:
            # 日本語文字の検出による簡単な判定
            japanese_chars = sum(1 for char in text if ord(char) > 0x3000)
            if japanese_chars > len(text) * 0.1:
                return "ja"
            return "en"
    
    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """日付文字列をパース"""
        try:
            from dateutil import parser
            return parser.parse(date_str)
        except:
            return None


# グローバルエクストラクターインスタンス
content_extractor = ContentExtractor()