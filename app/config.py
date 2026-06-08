from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Gemini
    gemini_api_key: str
    gemini_model: str = "gemini-2.0-flash"

    # app-control-manager GraphQL endpoint
    acm_graphql_url: str

    # Service config
    log_level: str = "INFO"
    max_input_length: int = 4000


settings = Settings()
