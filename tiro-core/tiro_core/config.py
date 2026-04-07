from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://tiro:tiro_dev_2026@localhost:5432/tiro"
    redis_url: str = "redis://localhost:6379/0"
    jwt_secret: str = "cambiami-in-produzione"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 480
    admin_email: str = "admin@firmamentotechnologies.com"
    admin_password: str = "cambiami"

    # Celery
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    # Raccolta
    imap_host: str = ""
    imap_user: str = ""
    imap_password: str = ""
    imap_poll_interval_sec: int = 300  # 5 minuti
    nanobot_redis_channel: str = "nanobot:messaggi"
    whisper_api_url: str = "http://whisper:9000/v1/audio/transcriptions"
    gdrive_sync_interval_sec: int = 900  # 15 minuti
    gdrive_folder_id: str = ""
    gdrive_credentials_path: str = ""

    # Elaborazione
    embedding_provider: str = "local"  # "local" | "openai"
    embedding_model: str = "nomic-embed-text"
    embedding_api_url: str = "http://ollama:11434/api/embeddings"
    openai_api_key: str = ""
    spacy_model: str = "it_core_news_md"
    fuzzy_match_threshold: int = 80  # soglia Levenshtein (0-100)
    dedup_hash_algorithm: str = "sha256"
    classification_confidence_threshold: float = 0.6

    # Intelligenza
    fascicolo_max_flussi_recenti: int = 50  # quanti flussi recenti includere nel fascicolo
    fascicolo_llm_timeout_sec: int = 30
    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"

    # Governance - Notifiche
    nanobot_invio_channel: str = "nanobot:invio"
    notifiche_ws_channel: str = "tiro:notifiche:proposte"
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "tiro@firmamentotechnologies.com"
    dashboard_url: str = "http://localhost:3000"

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
