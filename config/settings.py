"""
Gruha Alankara — Application Settings
Typed configuration using Pydantic BaseSettings.
All values are loaded from environment variables or .env file.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parent.parent


class FlaskSettings(BaseSettings):
    """Core Flask configuration."""

    model_config = SettingsConfigDict(env_prefix="", env_file=".env", extra="ignore")

    FLASK_ENV: str = "development"
    FLASK_DEBUG: bool = True
    SECRET_KEY: str = "change-me-to-a-secure-random-string"


class JWTSettings(BaseSettings):
    """JWT authentication configuration."""

    model_config = SettingsConfigDict(env_prefix="JWT_", env_file=".env", extra="ignore")

    SECRET_KEY: str = Field(alias="JWT_SECRET_KEY", default="change-me")
    ACCESS_TOKEN_EXPIRES: int = Field(alias="JWT_ACCESS_TOKEN_EXPIRES", default=3600)
    REFRESH_TOKEN_EXPIRES: int = Field(alias="JWT_REFRESH_TOKEN_EXPIRES", default=2592000)


class MongoSettings(BaseSettings):
    """MongoDB Atlas configuration."""

    model_config = SettingsConfigDict(env_prefix="MONGODB_", env_file=".env", extra="ignore")

    URI: str = Field(alias="MONGODB_URI", default="mongodb://localhost:27017")
    DB_NAME: str = Field(alias="MONGODB_DB_NAME", default="gruha_alankara")


class RedisSettings(BaseSettings):
    """Redis configuration."""

    model_config = SettingsConfigDict(env_prefix="REDIS_", env_file=".env", extra="ignore")

    URL: str = Field(alias="REDIS_URL", default="redis://localhost:6379/0")


class CelerySettings(BaseSettings):
    """Celery task queue configuration."""

    model_config = SettingsConfigDict(env_prefix="CELERY_", env_file=".env", extra="ignore")

    BROKER_URL: str = Field(alias="CELERY_BROKER_URL", default="redis://localhost:6379/1")
    RESULT_BACKEND: str = Field(alias="CELERY_RESULT_BACKEND", default="redis://localhost:6379/2")


class ChromaDBSettings(BaseSettings):
    """ChromaDB vector database configuration."""

    model_config = SettingsConfigDict(env_prefix="CHROMADB_", env_file=".env", extra="ignore")

    # Cloud client settings
    API_KEY: Optional[str] = Field(alias="CHROMADB_API_KEY", default=None)
    TENANT: Optional[str] = Field(alias="CHROMADB_TENANT", default=None)
    DATABASE: Optional[str] = Field(alias="CHROMADB_DATABASE", default=None)
    
    # Local client settings (fallback)
    HOST: str = Field(alias="CHROMADB_HOST", default="localhost")
    PORT: int = Field(alias="CHROMADB_PORT", default=8000)
    PERSIST_DIR: str = Field(alias="CHROMADB_PERSIST_DIR", default="./data/chromadb")

    @field_validator("PERSIST_DIR")
    @classmethod
    def ensure_absolute_path(cls, v: str) -> str:
        """Convert relative paths to absolute based on BASE_DIR."""
        if not Path(v).is_absolute():
            v = str(BASE_DIR / v)
        Path(v).mkdir(parents=True, exist_ok=True)
        return v

    @property
    def use_cloud_client(self) -> bool:
        """Check if cloud client should be used based on available credentials."""
        return bool(self.API_KEY and self.TENANT and self.DATABASE)


class GroqBuddySettings(BaseSettings):
    """Groq API configuration for Buddy Agent."""

    model_config = SettingsConfigDict(env_prefix="GROQ_BUDDY_", env_file=".env", extra="ignore")

    API_KEY: str = Field(alias="GROQ_BUDDY_API_KEY", default="")
    API_URL: str = Field(alias="GROQ_BUDDY_API_URL", default="https://api.groq.com/openai/v1")
    MODEL: str = Field(alias="GROQ_BUDDY_MODEL", default="llama-3.3-70b-versatile")


class GroqDesignSettings(BaseSettings):
    """Groq API configuration for Design Agent."""

    model_config = SettingsConfigDict(env_prefix="GROQ_DESIGN_", env_file=".env", extra="ignore")

    API_KEY: str = Field(alias="GROQ_DESIGN_API_KEY", default="")
    API_URL: str = Field(alias="GROQ_DESIGN_API_URL", default="https://api.groq.com/openai/v1")
    MODEL: str = Field(alias="GROQ_DESIGN_MODEL", default="llama-3.3-70b-versatile")


class GroqFurnitureSettings(BaseSettings):
    """Groq API configuration for Furniture Agent."""

    model_config = SettingsConfigDict(env_prefix="GROQ_FURNITURE_", env_file=".env", extra="ignore")

    API_KEY: str = Field(alias="GROQ_FURNITURE_API_KEY", default="")
    API_URL: str = Field(alias="GROQ_FURNITURE_API_URL", default="https://api.groq.com/openai/v1")
    MODEL: str = Field(alias="GROQ_FURNITURE_MODEL", default="llama-3.1-8b-instant")


class GroqBudgetSettings(BaseSettings):
    """Groq API configuration for Budget Agent."""

    model_config = SettingsConfigDict(env_prefix="GROQ_BUDGET_", env_file=".env", extra="ignore")

    API_KEY: str = Field(alias="GROQ_BUDGET_API_KEY", default="")
    API_URL: str = Field(alias="GROQ_BUDGET_API_URL", default="https://api.groq.com/openai/v1")
    MODEL: str = Field(alias="GROQ_BUDGET_MODEL", default="llama-3.1-8b-instant")


class GroqReasoningSettings(BaseSettings):
    """Groq Reasoning API configuration (Supervisor + Critic)."""

    model_config = SettingsConfigDict(env_prefix="GROQ_REASONING_", env_file=".env", extra="ignore")

    API_KEY: str = Field(alias="GROQ_REASONING_API_KEY", default="")
    API_URL: str = Field(alias="GROQ_REASONING_API_URL", default="https://api.groq.com/openai/v1")
    MODEL: str = Field(alias="GROQ_REASONING_MODEL", default="llama-3.3-70b-versatile")


class DeepSeekSettings(BaseSettings):
    """DeepSeek-R1 API configuration (Deprecated - Use GroqReasoningSettings)."""

    model_config = SettingsConfigDict(env_prefix="DEEPSEEK_", env_file=".env", extra="ignore")

    API_KEY: str = Field(alias="DEEPSEEK_API_KEY", default="")
    API_URL: str = Field(alias="DEEPSEEK_API_URL", default="https://api.deepseek.com/v1")
    MODEL: str = Field(alias="DEEPSEEK_MODEL", default="deepseek-reasoner")



class EmbeddingSettings(BaseSettings):
    """Embedding model configuration."""

    model_config = SettingsConfigDict(env_prefix="EMBEDDING_", env_file=".env", extra="ignore")

    MODEL: str = Field(alias="EMBEDDING_MODEL", default="BAAI/bge-m3")
    API_URL: Optional[str] = Field(alias="EMBEDDING_API_URL", default=None)


class GroqSettings(BaseSettings):
    """Groq API configuration (Buddy, Design, Furniture, Budget when MODEL_PROVIDER=groq)."""

    model_config = SettingsConfigDict(env_prefix="GROQ_", env_file=".env", extra="ignore")

    API_KEY: str = Field(alias="GROQ_API_KEY", default="")
    API_URL: str = Field(alias="GROQ_API_URL", default="https://api.groq.com/openai/v1")
    MODEL: str = Field(alias="GROQ_MODEL", default="llama-3.3-70b-versatile")



class ImageGenSettings(BaseSettings):
    """Image generation model endpoints."""

    model_config = SettingsConfigDict(env_prefix="", env_file=".env", extra="ignore")

    SDXL_ENDPOINT: str = Field(default="http://localhost:8004/v1/image/generate")
    CONTROLNET_ENDPOINT: str = Field(default="http://localhost:8004/v1/image/controlnet")


class VisionSettings(BaseSettings):
    """Vision model serving endpoints."""

    model_config = SettingsConfigDict(env_prefix="", env_file=".env", extra="ignore")

    FLORENCE2_ENDPOINT: str = "http://localhost:8001/v1/vision/florence2"
    YOLOV11_ENDPOINT: str = "http://localhost:8002/v1/vision/yolo"
    SAM2_ENDPOINT: str = "http://localhost:8003/v1/vision/sam2"


class VoiceSettings(BaseSettings):
    """Voice model configuration."""

    model_config = SettingsConfigDict(env_prefix="", env_file=".env", extra="ignore")

    WHISPER_MODEL_SIZE: str = "large-v3"
    TTS_MODEL: str = "tts_models/multilingual/multi-dataset/xtts_v2"


class StorageSettings(BaseSettings):
    """File storage configuration."""

    model_config = SettingsConfigDict(env_prefix="", env_file=".env", extra="ignore")

    UPLOAD_DIR: str = "./data/uploads"
    MAX_UPLOAD_SIZE_MB: int = 50

    @field_validator("UPLOAD_DIR")
    @classmethod
    def ensure_upload_dir(cls, v: str) -> str:
        # Convert to absolute path relative to BASE_DIR
        if not Path(v).is_absolute():
            v = str(BASE_DIR / v)
        Path(v).mkdir(parents=True, exist_ok=True)
        return v


class LoggingSettings(BaseSettings):
    """Logging configuration."""

    model_config = SettingsConfigDict(env_prefix="LOG_", env_file=".env", extra="ignore")

    LEVEL: str = Field(alias="LOG_LEVEL", default="INFO")
    FORMAT: str = Field(alias="LOG_FORMAT", default="json")


class ServerSettings(BaseSettings):
    """Server configuration."""

    model_config = SettingsConfigDict(env_prefix="", env_file=".env", extra="ignore")

    HOST: str = "0.0.0.0"
    PORT: int = 5000
    WORKERS: int = 4


class Settings:
    """
    Aggregated application settings.
    Lazily instantiates each settings group on first access.
    """

    def __init__(self) -> None:
        self._flask: FlaskSettings | None = None
        self._jwt: JWTSettings | None = None
        self._mongo: MongoSettings | None = None
        self._redis: RedisSettings | None = None
        self._celery: CelerySettings | None = None
        self._chromadb: ChromaDBSettings | None = None
        self._groq_buddy: GroqBuddySettings | None = None
        self._groq_design: GroqDesignSettings | None = None
        self._groq_furniture: GroqFurnitureSettings | None = None
        self._groq_budget: GroqBudgetSettings | None = None
        self._groq_reasoning: GroqReasoningSettings | None = None
        self._deepseek: DeepSeekSettings | None = None
        self._embedding: EmbeddingSettings | None = None
        self._groq: GroqSettings | None = None
        self._image_gen: ImageGenSettings | None = None
        self._vision: VisionSettings | None = None
        self._voice: VoiceSettings | None = None
        self._storage: StorageSettings | None = None
        self._logging: LoggingSettings | None = None
        self._server: ServerSettings | None = None

    @property
    def flask(self) -> FlaskSettings:
        if self._flask is None:
            self._flask = FlaskSettings()
        return self._flask

    @property
    def jwt(self) -> JWTSettings:
        if self._jwt is None:
            self._jwt = JWTSettings()
        return self._jwt

    @property
    def mongo(self) -> MongoSettings:
        if self._mongo is None:
            self._mongo = MongoSettings()
        return self._mongo

    @property
    def redis(self) -> RedisSettings:
        if self._redis is None:
            self._redis = RedisSettings()
        return self._redis

    @property
    def celery(self) -> CelerySettings:
        if self._celery is None:
            self._celery = CelerySettings()
        return self._celery

    @property
    def chromadb(self) -> ChromaDBSettings:
        if self._chromadb is None:
            self._chromadb = ChromaDBSettings()
        return self._chromadb

    @property
    def groq_buddy(self) -> GroqBuddySettings:
        if self._groq_buddy is None:
            self._groq_buddy = GroqBuddySettings()
        return self._groq_buddy

    @property
    def groq_design(self) -> GroqDesignSettings:
        if self._groq_design is None:
            self._groq_design = GroqDesignSettings()
        return self._groq_design

    @property
    def groq_furniture(self) -> GroqFurnitureSettings:
        if self._groq_furniture is None:
            self._groq_furniture = GroqFurnitureSettings()
        return self._groq_furniture

    @property
    def groq_budget(self) -> GroqBudgetSettings:
        if self._groq_budget is None:
            self._groq_budget = GroqBudgetSettings()
        return self._groq_budget

    @property
    def groq_reasoning(self) -> GroqReasoningSettings:
        if self._groq_reasoning is None:
            self._groq_reasoning = GroqReasoningSettings()
        return self._groq_reasoning

    @property
    def deepseek(self) -> DeepSeekSettings:
        if self._deepseek is None:
            self._deepseek = DeepSeekSettings()
        return self._deepseek

    @property
    def embedding(self) -> EmbeddingSettings:
        if self._embedding is None:
            self._embedding = EmbeddingSettings()
        return self._embedding

    @property
    def groq(self) -> GroqSettings:
        if self._groq is None:
            self._groq = GroqSettings()
        return self._groq

    @property
    def image_gen(self) -> ImageGenSettings:
        if self._image_gen is None:
            self._image_gen = ImageGenSettings()
        return self._image_gen

    @property
    def vision(self) -> VisionSettings:
        if self._vision is None:
            self._vision = VisionSettings()
        return self._vision

    @property
    def voice(self) -> VoiceSettings:
        if self._voice is None:
            self._voice = VoiceSettings()
        return self._voice

    @property
    def storage(self) -> StorageSettings:
        if self._storage is None:
            self._storage = StorageSettings()
        return self._storage

    @property
    def logging(self) -> LoggingSettings:
        if self._logging is None:
            self._logging = LoggingSettings()
        return self._logging

    @property
    def server(self) -> ServerSettings:
        if self._server is None:
            self._server = ServerSettings()
        return self._server


# Module-level singleton
settings = Settings()
