"""Configuración centralizada y validada para CCE-M5.

Usa pydantic-settings para leer variables de entorno y archivos .env
con validación de tipos y defaults seguros. Los módulos legacy que leían
os.environ directamente deberían migrar a importar settings desde aquí.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuración global del proyecto."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ------------------------------------------------------------------
    # Rutas del proyecto
    # ------------------------------------------------------------------
    project_dir: Path = Field(
        default=Path.home() / "proyectos" / "CCE-M5-Web-Presentaciones",
        alias="CCE_PROJECT_DIR",
    )

    # ------------------------------------------------------------------
    # Web estática / Astro
    # ------------------------------------------------------------------
    base_path: str = Field(default="/", alias="CCE_BASE_PATH")
    site_url: str = Field(default="http://localhost:4321", alias="CCE_SITE_URL")
    web_host: str = Field(default="0.0.0.0", alias="CCE_WEB_HOST")
    web_port: int = Field(default=4321, alias="CCE_WEB_PORT")

    # ------------------------------------------------------------------
    # Admin API
    # ------------------------------------------------------------------
    admin_host: str = Field(default="0.0.0.0", alias="CCE_ADMIN_HOST")
    admin_port: int = Field(default=4323, alias="CCE_ADMIN_PORT")
    jwt_secret: str | None = Field(default=None, alias="CCE_ADMIN_JWT_SECRET")
    jwt_ttl_minutes: int = Field(default=480, alias="CCE_ADMIN_TOKEN_TTL")
    default_admin_username: str = Field(default="rafael.torres", alias="CCE_ADMIN_DEFAULT_USER")
    default_admin_password: str | None = Field(default=None, alias="CCE_ADMIN_DEFAULT_PASSWORD")
    default_admin_name: str = Field(default="Rafael Torres", alias="CCE_ADMIN_DEFAULT_NAME")
    cors_origins_raw: str = Field(
        default="http://localhost:4321,http://localhost:4323",
        alias="ADMIN_CORS_ORIGINS",
    )

    # ------------------------------------------------------------------
    # Editores legacy (Flask)
    # ------------------------------------------------------------------
    editor_host: str = Field(default="0.0.0.0", alias="EDITOR_HOST")
    editor_port: int = Field(default=4324, alias="EDITOR_PORT")
    editor_acordes_host: str = Field(default="0.0.0.0", alias="EDITOR_ACORDES_HOST")
    editor_acordes_port: int = Field(default=4322, alias="EDITOR_ACORDES_PORT")

    # ------------------------------------------------------------------
    # GitHub proxy de comentarios
    # ------------------------------------------------------------------
    github_token_comentarios: str = Field(default="", alias="GITHUB_TOKEN_CC5M5")
    github_comentarios_owner: str = Field(default="cce-m5", alias="CCE_GITHUB_COMENTARIOS_OWNER")
    github_comentarios_repo: str = Field(default="cce-m5-music", alias="CCE_GITHUB_COMENTARIOS_REPO")

    # ------------------------------------------------------------------
    # Rate limiting
    # ------------------------------------------------------------------
    rate_limit_max_attempts: int = Field(default=5, alias="CCE_ADMIN_RATE_LIMIT_MAX_ATTEMPTS")
    rate_limit_window_seconds: float = Field(default=300.0, alias="CCE_ADMIN_RATE_LIMIT_WINDOW_SECONDS")
    rate_limit_block_seconds: float = Field(default=900.0, alias="CCE_ADMIN_RATE_LIMIT_BLOCK_SECONDS")
    redis_url: str | None = Field(default=None, alias="CCE_ADMIN_REDIS_URL")

    # ------------------------------------------------------------------
    # Node / build
    # ------------------------------------------------------------------
    node_bin: Path = Field(default=Path("/usr/bin"), alias="CCE_NODE_BIN")

    # ------------------------------------------------------------------
    # Backup
    # ------------------------------------------------------------------
    backup_keep_days: int = Field(default=30, alias="CCE_BACKUP_KEEP_DAYS")

    # ------------------------------------------------------------------
    # Campos derivados
    # ------------------------------------------------------------------
    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins_raw.split(",") if origin.strip()]

    @property
    def data_dir(self) -> Path:
        return self.project_dir / "data"

    @property
    def db_path(self) -> Path:
        return self.data_dir / "db.sqlite3"

    @property
    def assets_dir(self) -> Path:
        return self.project_dir / "assets"

    @property
    def backups_dir(self) -> Path:
        return self.project_dir / "backups"

    @property
    def web_dir(self) -> Path:
        return self.project_dir / "web"

    # ------------------------------------------------------------------
    # Validadores
    # ------------------------------------------------------------------
    @field_validator("project_dir", mode="before")
    @classmethod
    def _coerce_path(cls, v: str | Path) -> Path:
        return Path(v).expanduser().resolve()

    @field_validator("cors_origins_raw", mode="before")
    @classmethod
    def _default_cors_if_empty(cls, v: Any) -> str:
        if not v:
            return "http://localhost:4321,http://localhost:4323"
        return str(v)

    def model_post_init(self, __context: object) -> None:
        # Asegurar que existan los directorios esenciales.
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.assets_dir.mkdir(parents=True, exist_ok=True)
        self.backups_dir.mkdir(parents=True, exist_ok=True)


# Instancia global para importar directamente.
settings = Settings()
