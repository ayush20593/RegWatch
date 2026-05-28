from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    database_url: str = "postgresql://regwatch:regwatch@localhost:5432/regwatch"
    secret_key: str = "change-me-in-production"
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1:8b"
    brevo_api_key: str = ""
    sender_email: str = ""
    fetch_schedule_hours: int = 6
    digest_time_ist: str = "08:00"

settings = Settings()
