from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/followup"

    google_client_id: str
    google_client_secret: str
    google_redirect_uri: str = "http://localhost:8000/auth/callback"

    frontend_url: str = "http://localhost:3000"
    post_login_path: str = "/"
    secret_key: str
    token_encryption_key: str
    cookie_secure: bool = False
    session_ttl_hours: int = 24 * 7

    groq_api_key: str
    llm_model: str = "openai/gpt-oss-20b"

    email_lookback_days: int = 5
    max_threads: int = 50
    exclude_promotions: bool = True

    @property
    def checkpoint_db_url(self) -> str:
        """LangGraph's Postgres checkpointer uses psycopg, which wants a plain postgresql:// URL."""
        return self.database_url.replace("postgresql+asyncpg://", "postgresql://", 1)


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
