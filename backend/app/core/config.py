"""Configuración de la API, leída de variables de entorno (ADR-0002).

El mismo código corre en todos los ambientes; solo cambian estas variables.
"""

from functools import lru_cache
from typing import Annotated, Literal

from pydantic import SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: Literal["local", "staging", "production", "test"] = "local"
    app_version: str = "0.1.0"
    database_url: str | None = None
    cors_origins: Annotated[list[str], NoDecode] = []

    # Sesión (ADR-0005, research R2–R5).
    jwt_secret: SecretStr | None = None
    access_token_minutes: int = 15
    session_hours: int = 12
    refresh_reuse_grace_seconds: int = 30
    refresh_cookie_name: str = "sht_refresh"
    refresh_cookie_samesite: Literal["strict", "lax", "none"] = "strict"
    refresh_cookie_secure: bool = True
    refresh_cookie_domain: str | None = None

    # Instalación del primer administrador (FR-001, research R7).
    setup_code: SecretStr | None = None

    # Argon2id (research R1). Por defecto, los valores de argon2-cffi.
    argon2_time_cost: int = 3
    argon2_memory_cost: int = 65536
    argon2_parallelism: int = 4

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, value: object) -> object:
        # Se recibe como texto separado por comas en la variable de entorno.
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @model_validator(mode="after")
    def _require_secrets(self) -> Settings:
        if self.environment in ("staging", "production") and self.jwt_secret is None:
            raise ValueError("Falta la variable de entorno JWT_SECRET")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
