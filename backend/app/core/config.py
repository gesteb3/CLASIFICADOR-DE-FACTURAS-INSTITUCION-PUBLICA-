from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "ComprasBotGuatecompras"
    app_env: str = "local"
    app_debug: bool = True

    postgres_db: str = "compras_bot"
    postgres_user: str = "postgres"
    postgres_password: str = "postgres"
    postgres_host: str = "postgres"
    postgres_port: int = 5432

    redis_host: str = "redis"
    redis_port: int = 6379

    ollama_host: str = "http://ollama:11434"
    ollama_model: str = "qwen2.5:0.5b"

    secret_key: str = "cambiar_esta_clave_en_desarrollo"
    access_token_expire_minutes: int = 60

    max_pdfs_per_batch: int = 10
    max_pending_invoices_per_user: int = 20
    max_pdf_size_mb: int = 10
    max_workers: int = 2

    upload_dir: str = "uploads/invoices"
    catalog_dir: str = "/app/database/catalogos"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+psycopg2://{self.postgres_user}:"
            f"{self.postgres_password}@{self.postgres_host}:"
            f"{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def redis_url(self) -> str:
        return f"redis://{self.redis_host}:{self.redis_port}/0"


@lru_cache
def get_settings() -> Settings:
    return Settings()
