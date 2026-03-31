from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # App
    app_env: str = "development"
    app_secret_key: str
    app_base_url: str = "http://localhost:8000"
    frontend_url: str = "http://localhost:3000"

    # Database
    database_url: str
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "hwpbridge"
    postgres_user: str = "hwpbridge"
    postgres_password: str

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Claude API (USE_OLLAMA=true 시 불필요)
    anthropic_api_key: str = ""
    claude_model: str = "claude-sonnet-4-6"
    claude_max_tokens: int = 8192

    # AWS Bedrock
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_region: str = "us-east-1"
    bedrock_model_id: str = "us.anthropic.claude-sonnet-4-6"

    # Ollama
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1:8b"
    use_ollama: bool = False

    # Embedding
    embedding_model: str = "text-embedding-3-small"
    openai_api_key: str = ""
    embedding_dimension: int = 1536

    # File Storage
    upload_dir: str = "/tmp/hwpconverter/uploads"
    max_file_size_mb: int = 50

    # Security
    api_key_length: int = 64
    access_token_expire_minutes: int = 60
    cors_origins: list[str] = Field(default=["http://localhost:3000"])
    dev_api_key: str = ""  # 개발용 고정 키 (비어있으면 DB 조회)

    # Telegram 알림
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    # Sentry
    sentry_dsn: str = ""
    sentry_traces_sample_rate: float = 0.1

    # Rate Limit (IP당 하루 최대 횟수, 0=무제한)
    rate_limit_daily: int = 5          # 변환
    rate_limit_ai_daily: int = 3       # AI 기능 (초안/검색/교정)

    # Webhook
    webhook_secret: str = ""
    webhook_timeout_seconds: int = 30

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def max_file_size_bytes(self) -> int:
        return self.max_file_size_mb * 1024 * 1024


settings = Settings()
