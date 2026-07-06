from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "PDF to Excel Extractor"
    debug: bool = True
    upload_dir: str = "uploads"
    output_dir: str = "outputs"
    max_upload_size_mb: int = 10
    allowed_extensions: str = ".pdf"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    @property
    def upload_path(self) -> Path:
        path = BASE_DIR / self.upload_dir
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def output_path(self) -> Path:
        path = BASE_DIR / self.output_dir
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def allowed_extensions_list(self) -> list[str]:
        return [ext.strip().lower() for ext in self.allowed_extensions.split(",") if ext.strip()]


settings = Settings()
