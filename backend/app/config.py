from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Real environment variables win over values in backend/.env.
    database_url: str = "sqlite:///./pulsewatch.db"
    cors_origins: str = "http://localhost:5173"
    request_timeout_seconds: float = 8
    latency_threshold_ms: int = 1500
    max_response_bytes: int = 65536
    scheduler_enabled: bool = True
    # Old health-check rows are deleted by the scheduler so the table cannot grow forever.
    retention_days: int = 30
    # --- Login (single owner). Set these in backend/.env; login is refused until they exist. ---
    auth_username: str = ""
    auth_password: str = ""
    # Signs login tokens. If empty, a random key is generated at startup (everyone is logged out on restart).
    secret_key: str = ""
    token_ttl_hours: int = 12
    # --- Email alerts (all optional; alerts are skipped until host + recipient are set). ---
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_security: str = "starttls"  # "starttls" (port 587), "ssl" (port 465) or "none"
    alert_email_from: str = ""
    alert_email_to: str = ""
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
