from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(".env", "../.env"), extra="ignore")

    database_url: str = "postgresql+asyncpg://jev:jev@localhost:5432/jev_support"

    beatapi_api_key: str = ""
    beatapi_base_url: str = "https://api.beatapi.io"
    jev_model: str = "jev-1.13-free"
    jev_timeout_seconds: float = 30.0

    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"

    jwt_secret: str = "change-me"


settings = Settings()
