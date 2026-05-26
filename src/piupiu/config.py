from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
        populate_by_name=True,
    )

    passphrase: str = Field(..., validation_alias="PIUPIU_PASSPHRASE")
    data_dir: Path = Field(Path(".piupiu"), validation_alias="PIUPIU_DATA_DIR")
    channel: str = Field("cli", validation_alias="PIUPIU_CHANNEL")

    ai_provider: str = Field("anthropic", validation_alias="PIUPIU_AI_PROVIDER")

    anthropic_api_key: str = Field("", validation_alias="ANTHROPIC_API_KEY")
    ai_model: str = Field("claude-sonnet-4-6", validation_alias="PIUPIU_AI_MODEL")

    nim_api_key: str = Field("", validation_alias="NIM_API_KEY")
    nim_model: str = Field("meta/llama-3.1-70b-instruct", validation_alias="PIUPIU_NIM_MODEL")
    nim_base_url: str = Field("https://integrate.api.nvidia.com/v1", validation_alias="PIUPIU_NIM_BASE_URL")

    telegram_bot_token: str = Field("", validation_alias="TELEGRAM_BOT_TOKEN")

    debug: bool = Field(False, validation_alias="PIUPIU_DEBUG")

    ollama_enabled: bool = Field(False, validation_alias="PIUPIU_OLLAMA_ENABLED")
    ollama_base_url: str = Field("http://localhost:11434", validation_alias="PIUPIU_OLLAMA_BASE_URL")
    ollama_model: str = Field("qwen2.5:3b", validation_alias="PIUPIU_OLLAMA_MODEL")
    ollama_timeout: int = Field(30, validation_alias="PIUPIU_OLLAMA_TIMEOUT")

    web_enabled: bool = Field(False, validation_alias="PIUPIU_WEB_ENABLED")
    web_host: str = Field("127.0.0.1", validation_alias="PIUPIU_WEB_HOST")
    web_port: int = Field(8080, validation_alias="PIUPIU_WEB_PORT")


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
