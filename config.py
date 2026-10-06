from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):

    database_url: str
    secret_key: str
    redis_url: str = "redis://localhost:6379/0"
    algorithm: str = "HS256"
    stripe_secret_key: str
    stripe_webhook_secret: str
    access_token_expiry_minutes: int = 30 
    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()


