from app.config import settings

def test_settings_load():
    assert settings.database_url.startswith("postgresql")
    assert settings.ollama_model == "llama3.1:8b"
