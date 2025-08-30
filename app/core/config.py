from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    """アプリケーション設定"""
    
    # データベース設定
    db_url: str = "sqlite:///./data/scraps.db"
    
    # LLM API設定
    chat_api_base: str = "http://localhost:1234/v1"
    chat_model: str = "gpt-4o-mini-compat-or-your-local"
    embed_api_base: str = "http://localhost:1234/v1"
    embed_model: str = "text-embedding-3-large-or-nomic-embed-text"
    
    # API設定
    timeout_sec: int = 30
    max_retries: int = 3
    
    # アプリケーション設定
    app_title: str = "Scrap-Board"
    app_version: str = "1.0.0"
    secret_key: str = "change-this-secret-key-in-production"
    
    # ログ設定
    log_level: str = "INFO"
    
    # ファイル設定
    upload_dir: str = "./data/uploads"
    assets_dir: str = "./data/assets"
    max_file_size: int = 50_000_000  # 50MB
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# グローバル設定インスタンス
settings = Settings()

# ディレクトリ作成
os.makedirs(os.path.dirname(settings.db_url.replace("sqlite:///", "")), exist_ok=True)
os.makedirs(settings.upload_dir, exist_ok=True)
os.makedirs(settings.assets_dir, exist_ok=True)