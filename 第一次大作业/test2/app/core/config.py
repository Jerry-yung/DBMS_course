from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    mongodb_url: str = Field(default="mongodb://localhost:27017", env="MONGODB_URL")
    mongodb_db: str = Field(default="questionnaire_system", env="MONGODB_DB")
    secret_key: str = Field(default="change-me-in-production", env="SECRET_KEY")
    jwt_expire_minutes: int = Field(default=1440, env="JWT_EXPIRE_MINUTES")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
