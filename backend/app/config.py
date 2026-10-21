from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "ProcesoImagen"
    app_env: str = "development"
    api_prefix: str = "/api"
    database_url: str = (
        "postgresql+psycopg://procesoimagen:procesoimagen@localhost:5438/procesoimagen"
    )
    storage_path: str = "./storage"
    dataset_path: str = "../dataset"
    max_upload_mb: int = 15
    cors_origins: str = (
        "http://localhost:5273,http://127.0.0.1:5273,http://localhost:8300,"
        "http://161.132.53.51:5273,http://161.132.53.51:8300"
    )

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
