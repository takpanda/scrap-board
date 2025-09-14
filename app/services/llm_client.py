import httpx
import json
from typing import List, Dict, Any, Optional
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


class LLMClient:
    """LLMクライアント（LM Studio/Ollama対応）"""
    
    def __init__(self):
        self.chat_api_base = settings.chat_api_base
        self.embed_api_base = settings.embed_api_base
        self.chat_model = settings.chat_model
        self.embed_model = settings.embed_model
        self.timeout = settings.timeout_sec
        
    async def chat_completion(self, messages: List[Dict[str, str]], temperature: float = 0.1) -> Optional[str]:
        """チャット補完を実行"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.chat_api_base}/chat/completions",
                    json={
                        "model": self.chat_model,
                        "messages": messages,
                        "temperature": temperature,
                        "max_tokens": 2048,
                    },
                    timeout=self.timeout
                )
                response.raise_for_status()
                data = response.json()
                return data["choices"][0]["message"]["content"]
        except Exception as e:
            logger.error(f"Chat completion error: {e}")
            return None
    
    async def create_embedding(self, text: str) -> Optional[List[float]]:
        """テキスト埋め込みを作成"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.embed_api_base}/embeddings",
                    json={
                        "model": self.embed_model,
                        "input": text
                    },
                    timeout=self.timeout
                )
                response.raise_for_status()
                data = response.json()
                return data["data"][0]["embedding"]
        except Exception as e:
            logger.error(f"Embedding creation error: {e}")
            return None
    
    async def summarize_text(self, text: str, summary_type: str = "short") -> Optional[str]:
        """テキスト要約を生成"""
        
        if summary_type == "short":
            prompt = """以下のテキストを3-4行で要約してください。重要なポイントを簡潔にまとめてください。

テキスト:
{text}

要約:"""
        else:  # medium
            prompt = """以下のテキストを7-10行で要約してください。主要な論点と詳細を含めて分かりやすくまとめてください。

テキスト:
{text}

要約:"""
        
        messages = [
            {"role": "system", "content": "あなたは日本語の文書要約の専門家です。"},
            {"role": "user", "content": prompt.format(text=text[:4000])}  # トークン制限
        ]
        
        return await self.chat_completion(messages)

    async def generate_summary(self, text: str, style: str = "short", timeout_sec: Optional[int] = None) -> Optional[str]:
        """高レベルな要約生成ラッパー。

        - `style`: 'short' または 'medium'
        - `timeout_sec`: 明示的なタイムアウト（指定がなければクライアント設定を使用）
        成功時に要約文字列、失敗時は None を返す。
        """
        import asyncio

        t = timeout_sec or self.timeout
        start = None
        try:
            start = asyncio.get_event_loop().time()
            coro = self.summarize_text(text, summary_type=("short" if style == "short" else "medium"))
            result = await asyncio.wait_for(coro, timeout=t)
            elapsed = asyncio.get_event_loop().time() - start
            logger.info(f"summary_generation_success model={self.chat_model} elapsed_ms={int(elapsed*1000)} style={style}")
            return result
        except asyncio.TimeoutError:
            elapsed = None
            try:
                if start is not None:
                    elapsed = int((asyncio.get_event_loop().time() - start) * 1000)
            except Exception:
                elapsed = None
            logger.error(f"summary_generation_timeout model={self.chat_model} timeout_ms={t*1000} elapsed_ms={elapsed}")
            return None
        except Exception as e:
            logger.error(f"summary_generation_failure model={self.chat_model} error={e}")
            return None
    
    async def classify_content(self, title: str, content: str) -> Optional[Dict[str, Any]]:
        """コンテンツ分類を実行"""
        
        categories = [
            "テック/AI", "ソフトウェア開発", "ビジネス", "セキュリティ", "研究", 
            "プロダクト", "法規制", "データサイエンス", "クラウド/インフラ", 
            "デザイン/UX", "教育", "ライフ", "その他"
        ]
        
        prompt = f"""以下の記事を分析し、最適なカテゴリとタグを選択してください。

記事タイトル: {title}
記事内容: {content[:2000]}

利用可能なカテゴリ:
{', '.join(categories)}

以下の形式でJSONで回答してください:
{{
    "primary_category": "選択されたカテゴリ",
    "tags": ["関連タグ1", "関連タグ2", "関連タグ3"],
    "confidence": 0.85
}}"""

        messages = [
            {"role": "system", "content": "あなたは記事分類の専門家です。記事の内容を分析し、適切なカテゴリとタグを付けます。"},
            {"role": "user", "content": prompt}
        ]
        
        response = await self.chat_completion(messages, temperature=0.0)
        if response:
            try:
                # JSONパースを試行
                import re
                json_match = re.search(r'\{.*\}', response, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group())
            except Exception as e:
                logger.error(f"Classification JSON parse error: {e}")
        
        return None


# グローバルクライアントインスタンス
llm_client = LLMClient()