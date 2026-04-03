from datetime import datetime
from mimetypes import guess_extension
from uuid import uuid4

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import settings
from .models import MediaAsset
from .schemas import MediaAssetResponse


def _csv_to_set(raw: str) -> set[str]:
    return {value.strip() for value in raw.split(",") if value.strip()}


def _allowed_mime_types() -> set[str]:
    return _csv_to_set(settings.allowed_image_mime_types)


def _public_entity_types() -> set[str]:
    return _csv_to_set(settings.public_entity_types)


def _signed_entity_types() -> set[str]:
    return _csv_to_set(settings.signed_entity_types)


def _resolve_access_mode(entity_type: str, access_mode: str | None) -> str:
    if access_mode and access_mode not in {"public", "signed"}:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="access_mode must be 'public' or 'signed'",
        )
    if access_mode in {"public", "signed"}:
        return access_mode
    if entity_type in _public_entity_types():
        return "public"
    return "signed"


def _validate_entity_type(entity_type: str) -> None:
    allowed = _public_entity_types() | _signed_entity_types()
    if entity_type not in allowed:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unsupported entity_type '{entity_type}'",
        )


def _validate_payload(content: bytes, mime_type: str, file_name: str) -> None:
    if not file_name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File name is required")
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File content is empty")
    if mime_type not in _allowed_mime_types():
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Unsupported image MIME type")

    max_size_bytes = settings.max_upload_size_mb * 1024 * 1024
    if len(content) > max_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds max allowed size ({settings.max_upload_size_mb} MB)",
        )


def _build_r2_key(entity_type: str, entity_id: str, mime_type: str) -> str:
    extension = guess_extension(mime_type) or ""
    date_folder = datetime.utcnow().strftime("%Y/%m/%d")
    return f"{entity_type}/{entity_id}/{date_folder}/{uuid4().hex}{extension}"


def _get_r2_client():
    try:
        return boto3.client(
            "s3",
            endpoint_url=settings.r2_endpoint_url,
            aws_access_key_id=settings.r2_access_key_id,
            aws_secret_access_key=settings.r2_secret_access_key,
            region_name=settings.r2_region_name,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Invalid R2 endpoint configuration. Use a valid URL without angle brackets.",
        ) from exc


def _build_object_url(key: str) -> str:
    if settings.r2_public_base_url:
        return f"{settings.r2_public_base_url.rstrip('/')}/{key}"
    return f"{settings.r2_endpoint_url.rstrip('/')}/{settings.r2_bucket_name}/{key}"


def _build_download_url(access_mode: str, key: str, object_url: str) -> str:
    if access_mode == "public":
        return object_url

    try:
        r2 = _get_r2_client()
        return r2.generate_presigned_url(
            "get_object",
            Params={"Bucket": settings.r2_bucket_name, "Key": key},
            ExpiresIn=settings.r2_signed_url_expire_seconds,
        )
    except (BotoCoreError, ClientError) as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Failed to sign media URL") from exc


def _to_response(asset: MediaAsset) -> MediaAssetResponse:
    download_url = _build_download_url(asset.access_mode, asset.r2_key, asset.url)
    return MediaAssetResponse(
        id=asset.id,
        entity_type=asset.entity_type,
        entity_id=asset.entity_id,
        original_filename=asset.original_filename,
        mime_type=asset.mime_type,
        file_size_bytes=asset.file_size_bytes,
        url=download_url,
        access_mode=asset.access_mode,
        uploaded_by=asset.uploaded_by,
        created_at=asset.created_at,
        updated_at=asset.updated_at,
    )


def create_media_asset(
    db: Session,
    *,
    entity_type: str,
    entity_id: str,
    uploaded_by: str,
    original_filename: str,
    mime_type: str,
    content: bytes,
    access_mode: str | None,
) -> MediaAssetResponse:
    _validate_entity_type(entity_type)
    _validate_payload(content, mime_type, original_filename)

    final_access_mode = _resolve_access_mode(entity_type, access_mode)
    key = _build_r2_key(entity_type, entity_id, mime_type)
    object_url = _build_object_url(key)

    try:
        r2 = _get_r2_client()
        r2.put_object(
            Bucket=settings.r2_bucket_name,
            Key=key,
            Body=content,
            ContentType=mime_type,
        )
    except (BotoCoreError, ClientError) as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Failed to upload file to Cloudflare R2") from exc

    asset = MediaAsset(
        id=str(uuid4()),
        entity_type=entity_type,
        entity_id=entity_id,
        original_filename=original_filename,
        mime_type=mime_type,
        file_size_bytes=len(content),
        r2_key=key,
        url=object_url,
        access_mode=final_access_mode,
        uploaded_by=uploaded_by,
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return _to_response(asset)


def get_media_asset(media_id: str, db: Session) -> MediaAssetResponse:
    asset = db.get(MediaAsset, media_id)
    if not asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media not found")
    return _to_response(asset)


def list_media_assets_by_entity(entity_type: str, entity_id: str, db: Session) -> list[MediaAssetResponse]:
    _validate_entity_type(entity_type)
    records = db.scalars(
        select(MediaAsset).where(MediaAsset.entity_type == entity_type, MediaAsset.entity_id == entity_id)
    ).all()
    return [_to_response(item) for item in records]
