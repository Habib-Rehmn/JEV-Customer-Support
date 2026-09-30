from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(".env", "../.env"), extra="ignore")

    database_url: str = "postgresql+asyncpg://jev:jev@localhost:5432/jev_support"

    beatapi_api_key: str = ""
    beatapi_base_url: str = "https://api.beatapi.io"
    jev_model: str = "jev-1.13-free"
    jev_timeout_seconds: float = 30.0

    openai_api_key: str = ""
    openai_model: str = "gpt-5.4-mini"
    openai_reasoning_effort: str = "low"  # set empty for non-reasoning models such as gpt-4o-mini
    openai_timeout_seconds: float = 60.0

    jwt_secret: str = "change-me"
    access_token_minutes: int = 8 * 60

    # Business rules (see services/rules_service.py)
    rule_min_confidence: float = 0.70
    rule_refund_approval_limit: float = 500.0
    rule_max_refunds_30_days: int = 3
    rule_replacement_window_days: int = 30
    rule_auto_replacement_limit: float = 100.0
    rule_signal_threshold: float = 0.5

    # Response-time targets (hours from ticket creation to the first reply), by priority
    sla_hours_urgent: float = 1
    sla_hours_high: float = 4
    sla_hours_normal: float = 24
    sla_hours_low: float = 72


settings = Settings()
