import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from pydantic import BaseModel

load_dotenv()


class LLMConfig(BaseModel):
    api_key: str
    base_url: str
    model_name: str


class EmbeddingConfig(BaseModel):
    api_key: str
    base_url: str
    model_name: str
    dims: int


class SeekDBConfig(BaseModel):
    dir: str
    name: str
    host: Optional[str] = None
    port: Optional[int] = None
    user: Optional[str] = None
    password: Optional[str] = None


class PowerMemConfig(BaseModel):
    collection_name: str


class LegalAnalyzerConfig(BaseModel):
    legal_collection_name: str
    risk_collection_name: str


class Config:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_config()
        return cls._instance

    def _load_config(self):
        self.llm = LLMConfig(
            api_key=os.getenv("OPENAI_API_KEY", ""),
            base_url=os.getenv("OPENAI_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"),
            model_name=os.getenv("OPENAI_MODEL_NAME", "qwen-plus"),
        )

        self.embedding = EmbeddingConfig(
            api_key=os.getenv("EMBEDDING_API_KEY", os.getenv("OPENAI_API_KEY", "")),
            base_url=os.getenv("EMBEDDING_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"),
            model_name=os.getenv("EMBEDDING_MODEL_NAME", "text-embedding-v4"),
            dims=int(os.getenv("EMBEDDING_DIMS", "1024")),
        )

        self.seekdb = SeekDBConfig(
            dir=os.getenv("SEEKDB_DIR", "./data/seekdb_legal"),
            name=os.getenv("SEEKDB_NAME", "legal_risk"),
            host=os.getenv("SEEKDB_HOST"),
            port=int(os.getenv("SEEKDB_PORT", "2881")) if os.getenv("SEEKDB_PORT") else None,
            user=os.getenv("SEEKDB_USER"),
            password=os.getenv("SEEKDB_PASSWORD", ""),
        )

        self.powermem = PowerMemConfig(
            collection_name=os.getenv("POWERMEM_COLLECTION_NAME", "legal_memories"),
        )

        self.legal_analyzer = LegalAnalyzerConfig(
            legal_collection_name=os.getenv("LEGAL_COLLECTION_NAME", "legal_documents"),
            risk_collection_name=os.getenv("RISK_COLLECTION_NAME", "risk_knowledge"),
        )

        self.data_dir = Path(os.getenv("SEEKDB_DIR", "./data/seekdb_legal"))
        self.data_dir.mkdir(parents=True, exist_ok=True)

    @classmethod
    def get_llm_config(cls) -> LLMConfig:
        return cls().llm

    @classmethod
    def get_embedding_config(cls) -> EmbeddingConfig:
        return cls().embedding

    @classmethod
    def get_seekdb_config(cls) -> SeekDBConfig:
        return cls().seekdb

    @classmethod
    def get_powermem_config(cls) -> PowerMemConfig:
        return cls().powermem

    @classmethod
    def get_legal_analyzer_config(cls) -> LegalAnalyzerConfig:
        return cls().legal_analyzer
