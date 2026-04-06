from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://tiro:tiro_dev_2026@localhost:5432/tiro"
    redis_url: str = "redis://localhost:6379/0"
    jwt_secret: str = "cambiami-in-produzione"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 480
    admin_email: str = "admin@firmamentotechnologies.com"
    admin_password: str = "cambiami"
    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
