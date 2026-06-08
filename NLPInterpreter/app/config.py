from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Anthropic
    anthropic_api_key: str
    # claude-haiku is the lowest cost Anthropic model
    anthropic_model: str = "claude-haiku-4-5-20251001"

    # app-control-manager base URL (REST) — set ACM_URL in .env
    acm_url: str = "http://localhost:7091"

    # Service config
    port: int = 8082
    log_level: str = "INFO"
    max_input_length: int = 4000


settings = Settings()
