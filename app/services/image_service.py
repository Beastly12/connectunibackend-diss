import cloudinary
import cloudinary.uploader
from fastapi import HTTPException, UploadFile, status

from app.core.config import settings




cloudinary.config(
    cloud_name=settings.CLOUDINARY_CLOUD_NAME,
    api_key=settings.CLOUDINARY_API_KEY,
    api_secret=settings.CLOUDINARY_API_SECRET,
    secure=True,  # always use https URLs
)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Magic bytes for each allowed MIME type
# We read the first 12 bytes of the file and check against these signatures
# This cannot be faked by renaming a file — it's the actual file content
ALLOWED_MIME_SIGNATURES: dict[bytes, str] = {
    b"\xff\xd8\xff": "image/jpeg",
    b"\x89PNG\r\n\x1a\n": "image/png",
    b"RIFF": "image/webp",   # WebP starts with RIFF....WEBP
    b"GIF87a": "image/gif",
    b"GIF89a": "image/gif",
}

# Max file sizes per image type (in bytes)
SIZE_LIMITS: dict[str, int] = {
    "avatar":        5 * 1024 * 1024,   # 5MB
    "event_cover":   10 * 1024 * 1024,  # 10MB
    "community_cover": 10 * 1024 * 1024, # 10MB
    "post_image":    10 * 1024 * 1024,  # 10MB
    "message_image": 10 * 1024 * 1024,  # 10MB
}

# Cloudinary folder per image type — keeps your media library organised
FOLDERS: dict[str, str] = {
    "avatar":          "connectuni/avatars",
    "event_cover":     "connectuni/events",
    "community_cover": "connectuni/communities",
    "post_image":      "connectuni/posts",
    "message_image":   "connectuni/messages",
}



class ImageService:

    async def upload(
        self,
        file: UploadFile,
        image_type: str,
        old_public_id: str | None = None,
    ) -> dict[str, str]:
        """
        Validates, uploads a file to Cloudinary, and optionally deletes the
        old image if one existed (e.g. user replacing their avatar).

        Returns: { "url": "https://...", "public_id": "connectuni/avatars/xyz" }
        """
        if image_type not in SIZE_LIMITS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown image type '{image_type}'.",
            )

        # Step 1: Read file contents into memory
        contents = await file.read()

        # Step 2: Validate file size
        size_limit = SIZE_LIMITS[image_type]
        if len(contents) > size_limit:
            limit_mb = size_limit // (1024 * 1024)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File too large. Maximum size for {image_type} is {limit_mb}MB.",
            )

        # Step 3: Validate file type via magic bytes — cannot be faked
        if not self._is_valid_image(contents):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid file type. Only JPEG, PNG, WebP, and GIF are allowed.",
            )

        # Step 4: Delete old image from Cloudinary before uploading new one
        # This prevents orphaned files accumulating in your media library
        if old_public_id:
            await self.delete(old_public_id)

        # Step 5: Upload to Cloudinary
        try:
            result = cloudinary.uploader.upload(
                contents,
                folder=FOLDERS[image_type],
                resource_type="image",
                # Cloudinary auto-generates a unique public_id within the folder
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Image upload failed: {str(e)}",
            )

        return {
            "url": result["secure_url"],
            "public_id": result["public_id"],
        }

    async def delete(self, public_id: str) -> None:
        """
        Deletes an image from Cloudinary by its public_id.
        Called automatically on replace, or explicitly on resource deletion.
        Fails silently if the image doesn't exist — avoids crashing on stale IDs.
        """
        try:
            cloudinary.uploader.destroy(public_id, resource_type="image")
        except Exception:
            # Log in production but don't crash — a missing image is not fatal
            pass

    def _is_valid_image(self, contents: bytes) -> bool:
        """
        Reads the magic bytes at the start of the file to verify it is actually
        an image. This is more reliable than checking the filename or Content-Type
        header, both of which can be trivially faked by a client.
        """
        header = contents[:12]

        for signature, _ in ALLOWED_MIME_SIGNATURES.items():
            if header.startswith(signature):
                return True

        # WebP needs a special check: bytes 0-3 are RIFF, bytes 8-11 are WEBP
        if header[:4] == b"RIFF" and header[8:12] == b"WEBP":
            return True

        return False