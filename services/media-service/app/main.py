from typing import Annotated

from fastapi import Depends, FastAPI, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from .database import Base, engine, get_db
from .schemas import MediaAssetResponse
from .service import create_media_asset, get_media_asset, list_media_assets_by_entity

app = FastAPI(title="Media Service", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    Base.metadata.create_all(bind=engine)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "media-service"}


@app.post("/internal/media/upload", response_model=MediaAssetResponse, status_code=201)
async def upload_media(
    file: UploadFile = File(...),
    entity_type: str = Form(...),
    entity_id: str = Form(...),
    uploaded_by: str = Form(...),
    access_mode: str | None = Form(default=None),
    db: Session = Depends(get_db),
) -> MediaAssetResponse:
    content = await file.read()
    return create_media_asset(
        db,
        entity_type=entity_type,
        entity_id=entity_id,
        uploaded_by=uploaded_by,
        original_filename=file.filename or "upload.bin",
        mime_type=file.content_type or "application/octet-stream",
        content=content,
        access_mode=access_mode,
    )


@app.get("/internal/media/by-entity", response_model=list[MediaAssetResponse])
def media_by_entity(
    entity_type: str,
    entity_id: str,
    db: Annotated[Session, Depends(get_db)],
) -> list[MediaAssetResponse]:
    return list_media_assets_by_entity(entity_type, entity_id, db)


@app.get("/internal/media/{media_id}", response_model=MediaAssetResponse)
def media_get(media_id: str, db: Annotated[Session, Depends(get_db)]) -> MediaAssetResponse:
    return get_media_asset(media_id, db)
