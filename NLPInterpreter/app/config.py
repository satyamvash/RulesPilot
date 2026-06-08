from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Anthropic
    anthropic_api_key: str
    # claude-3-haiku is the lowest cost Anthropic model
    anthropic_model: str = "claude-haiku-4-5-20251001"

    # app-control-manager GraphQL endpoint
    acm_graphql_url: str

    # Service config
    log_level: str = "INFO"
    max_input_length: int = 4000


settings = Settings()
