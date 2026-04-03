from datetime import datetime

from pydantic import BaseModel


class MediaAssetResponse(BaseModel):
    id: str
    entity_type: str
    entity_id: str
    original_filename: str
    mime_type: str
    file_size_bytes: int
    url: str
    access_mode: str
    uploaded_by: str
    created_at: datetime
    updated_at: datetime
