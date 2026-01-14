from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # App
    ENV: str = "development"
    DEBUG: bool = True

    # Auth
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Database
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str

    DATABASE_URL: str

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )


settings = Settings()