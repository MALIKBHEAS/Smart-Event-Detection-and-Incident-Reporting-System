from __future__ import annotations

import logging
from typing import Any, Optional

from pydantic import Field
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)

# Only ever used as a fallback in development. AppSettings warns loudly if
# this is still active while app_env=production.
_INSECURE_DEV_JWT_SECRET = "dev-only-insecure-secret-change-me"


class AppSettings(BaseSettings):
    """Application settings loaded from environment variables.

    Fields:
    - app_env: environment name (development|production|test)
    - worker_manager_type: which WorkerManager implementation to use (real|mock|dev)
    """

    app_env: str = Field("development", env="APP_ENV")
    worker_manager_type: str = Field("real", env="WORKER_MANAGER_TYPE")
    # Optional runtime metadata
    version: str = Field("1.0.0", env="APP_VERSION")
    database_url: Optional[str] = Field(None, env="DATABASE_URL")

    # Auth / JWT
    jwt_secret_key: str = Field(_INSECURE_DEV_JWT_SECRET, env="JWT_SECRET_KEY")
    jwt_algorithm: str = Field("HS256", env="JWT_ALGORITHM")
    jwt_access_token_expire_minutes: int = Field(1440, env="JWT_ACCESS_TOKEN_EXPIRE_MINUTES")
    jwt_refresh_token_expire_days: int = Field(30, env="JWT_REFRESH_TOKEN_EXPIRE_DAYS")

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        if self.app_env == "production" and self.jwt_secret_key == _INSECURE_DEV_JWT_SECRET:
            logger.warning(
                "JWT_SECRET_KEY is not set (using the insecure development default) while "
                "APP_ENV=production. Set a real JWT_SECRET_KEY before deploying."
            )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


def get_settings() -> AppSettings:
    return AppSettings()
