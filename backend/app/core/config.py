from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "WhatsApp Compliance CRM"
    env: str = "dev"
    db_url: str = "sqlite:///./app.db"
    whatsapp_token: str = ""
    phone_number_id: str = ""
    waba_id: str = ""
    verify_token: str = ""
    app_secret: str = ""
    base_url: str = "http://localhost:8000"
    per_minute_cap: int = 20
    per_hour_cap: int = 300
    business_hours_start: int = 9
    business_hours_end: int = 22

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)


settings = Settings()
