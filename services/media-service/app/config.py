from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str

    r2_endpoint_url: str
    r2_access_key_id: str
    r2_secret_access_key: str
    r2_bucket_name: str
    r2_public_base_url: str | None = None
    r2_region_name: str = "auto"

    max_upload_size_mb: int = 10
    allowed_image_mime_types: str = "image/jpeg,image/png,image/webp"
    public_entity_types: str = "clients"
    signed_entity_types: str = "trips,dispatch"
    r2_signed_url_expire_seconds: int = 3600


settings = Settings()
