from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    seed_data_file: str = "/app/seed-data/initial_data.json"
    clients_service_url: str = "http://clients-service:8004"


settings = Settings()
