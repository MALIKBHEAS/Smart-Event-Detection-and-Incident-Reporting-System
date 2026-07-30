from pydantic import BaseSettings, Field, AnyUrl
from typing import Optional

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = Field(..., env="DATABASE_URL")
    TEST_DATABASE_URL: Optional[str] = Field(None, env="TEST_DATABASE_URL")

    # Redis/Celery
    REDIS_URL: str = Field(..., env="REDIS_URL")

    # RabbitMQ (or Kafka)
    RABBITMQ_URL: str = Field(..., env="RABBITMQ_URL")

    # JWT
    JWT_SECRET: str = Field(..., env="JWT_SECRET")
    JWT_ALGORITHM: str = Field("HS256", env="JWT_ALGORITHM")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(15, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(7, env="REFRESH_TOKEN_EXPIRE_DAYS")

    # S3 / MinIO
    S3_ENDPOINT_URL: Optional[AnyUrl] = Field(None, env="S3_ENDPOINT_URL")
    S3_ACCESS_KEY: Optional[str] = Field(None, env="S3_ACCESS_KEY")
    S3_SECRET_KEY: Optional[str] = Field(None, env="S3_SECRET_KEY")
    S3_BUCKET: Optional[str] = Field(None, env="S3_BUCKET")

    # Other
    DEDUPE_WINDOW_SECONDS: int = Field(10, env="DEDUPE_WINDOW_SECONDS")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
