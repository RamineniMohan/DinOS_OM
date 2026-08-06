import os
import uuid

from fastapi import HTTPException, UploadFile, status

from app.core.config import settings

ALLOWED_MIME_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif", "image/svg+xml"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB


async def save_image_upload(file: UploadFile, folder: str = "menu_items") -> str:
    """
    Upload file to Cloudinary if credentials are configured,
    otherwise save to local uploads directory and return static path.
    """
    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_FILE_TYPE", "message": f"Unsupported file type '{file.content_type}'. Allowed types: JPEG, PNG, WebP, GIF, SVG."},
        )

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "FILE_TOO_LARGE", "message": "File size exceeds maximum allowed limit of 5MB."},
        )

    # Check if Cloudinary is configured
    if (settings.CLOUDINARY_CLOUD_NAME and settings.CLOUDINARY_API_KEY and settings.CLOUDINARY_API_SECRET) or settings.CLOUDINARY_URL:
        try:
            import cloudinary
            import cloudinary.uploader

            if settings.CLOUDINARY_URL:
                cloudinary.config(cloudinary_url=settings.CLOUDINARY_URL)
            else:
                cloudinary.config(
                    cloud_name=settings.CLOUDINARY_CLOUD_NAME,
                    api_key=settings.CLOUDINARY_API_KEY,
                    api_secret=settings.CLOUDINARY_API_SECRET,
                    secure=True,
                )

            res = cloudinary.uploader.upload(content, folder=f"dineos/{folder}")
            return res.get("secure_url", res.get("url"))
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"code": "UPLOAD_FAILED", "message": f"Cloudinary upload failed: {str(e)}"},
            )

    # Fallback to local storage
    ext = file.filename.split(".")[-1].lower() if file.filename and "." in file.filename else "jpg"
    filename = f"{uuid.uuid4().hex}.{ext}"
    local_dir = os.path.join("uploads", folder)
    os.makedirs(local_dir, exist_ok=True)
    local_path = os.path.join(local_dir, filename)

    with open(local_path, "wb") as f:
        f.write(content)

    return f"/static/uploads/{folder}/{filename}"
