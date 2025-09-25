"""
Thumbnail generation service for uploaded images.
Supports both local and R2 storage backends.
"""

import os
import io
import time
import logging
import requests
from typing import Dict, Optional, Tuple
from flask import current_app

try:
    from PIL import Image, ImageOps
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

from app.models import File, db
from app.services.storage_service import StorageService

logger = logging.getLogger(__name__)


class ThumbnailService:
    """Service for generating and managing image thumbnails."""

    THUMBNAIL_SIZES = {
        'small': (150, 150),
        'medium': (300, 300),
        'large': (600, 600)
    }

    def __init__(self):
        self.storage_service = StorageService()

    def generate_thumbnail(self, file_record: File, size: str = 'medium') -> Optional[str]:
        """
        Generate thumbnail for image file.

        Args:
            file_record: File model instance
            size: Thumbnail size (small, medium, large)

        Returns:
            Storage path of generated thumbnail or None if failed
        """
        if not PIL_AVAILABLE:
            logger.error("PIL/Pillow is not available. Cannot generate thumbnails.")
            return None

        if size not in self.THUMBNAIL_SIZES:
            raise ValueError(f"Invalid thumbnail size: {size}")

        # Only generate thumbnails for image files
        if not file_record.mime_type.startswith('image/'):
            logger.info(f"Skipping thumbnail generation for non-image file: {file_record.mime_type}")
            return None

        try:
            # Get original file data
            original_data = self._get_file_data(file_record)
            if not original_data:
                return None

            # Process image
            thumbnail_data = self._create_thumbnail_data(original_data, size)
            if not thumbnail_data:
                return None

            # Upload thumbnail to storage
            thumbnail_key = f"thumbnails/{file_record.collection.uuid}/{size}_{file_record.filename}"

            # Upload thumbnail
            if self.storage_service.backend == 'r2' and self.storage_service.r2_storage:
                result = self.storage_service.r2_storage.upload_single_file(
                    file_obj=io.BytesIO(thumbnail_data),
                    key=thumbnail_key,
                    metadata={
                        'original_file_id': str(file_record.id),
                        'thumbnail_size': size,
                        'generated_timestamp': str(int(time.time()))
                    }
                )
                return result['key']
            else:
                # Save to local storage
                thumbnail_dir = os.path.join(
                    current_app.instance_path,
                    'thumbnails',
                    str(file_record.collection.uuid)
                )
                os.makedirs(thumbnail_dir, exist_ok=True)

                thumbnail_filename = f"{size}_{file_record.filename}"
                # Ensure .jpg extension for thumbnails
                if not thumbnail_filename.lower().endswith('.jpg'):
                    thumbnail_filename = os.path.splitext(thumbnail_filename)[0] + '.jpg'

                thumbnail_path = os.path.join(thumbnail_dir, thumbnail_filename)

                with open(thumbnail_path, 'wb') as f:
                    f.write(thumbnail_data)

                return f"thumbnails/{file_record.collection.uuid}/{thumbnail_filename}"

        except Exception as e:
            logger.error(f"Thumbnail generation failed for {file_record.id}: {e}")
            return None

    def _get_file_data(self, file_record: File) -> Optional[bytes]:
        """Get file data from storage."""
        try:
            if self.storage_service.backend == 'r2' and self.storage_service.r2_storage:
                # Download from R2
                file_url = self.storage_service.generate_file_url(file_record, expiry_seconds=300)
                response = requests.get(file_url, timeout=30)
                response.raise_for_status()
                return response.content
            else:
                # Read from local storage
                file_path = os.path.join(current_app.instance_path, file_record.storage_path)
                if os.path.exists(file_path):
                    with open(file_path, 'rb') as f:
                        return f.read()
                return None

        except Exception as e:
            logger.error(f"Failed to get file data for {file_record.id}: {e}")
            return None

    def _create_thumbnail_data(self, image_data: bytes, size: str) -> Optional[bytes]:
        """Create thumbnail data from image data."""
        if not PIL_AVAILABLE:
            return None

        try:
            # Open and process image
            image = Image.open(io.BytesIO(image_data))

            # Convert to RGB if necessary (handles RGBA, P, etc.)
            if image.mode in ('RGBA', 'LA', 'P'):
                # Create a white background for transparent images
                background = Image.new('RGB', image.size, (255, 255, 255))
                if image.mode == 'P':
                    image = image.convert('RGBA')
                background.paste(image, mask=image.split()[-1] if image.mode in ('RGBA', 'LA') else None)
                image = background
            elif image.mode != 'RGB':
                image = image.convert('RGB')

            # Auto-rotate based on EXIF orientation
            try:
                image = ImageOps.exif_transpose(image)
            except Exception:
                # If exif_transpose fails, continue without rotation
                pass

            # Create thumbnail maintaining aspect ratio
            thumbnail_size = self.THUMBNAIL_SIZES[size]
            image.thumbnail(thumbnail_size, Image.Resampling.LANCZOS)

            # Save to bytes
            output = io.BytesIO()
            image.save(output, format='JPEG', quality=85, optimize=True)
            return output.getvalue()

        except Exception as e:
            logger.error(f"Image processing failed: {e}")
            return None

    def batch_generate_thumbnails(self, file_records: list, size: str = 'medium') -> Dict[str, str]:
        """
        Generate thumbnails for multiple files.

        Args:
            file_records: List of File model instances
            size: Thumbnail size

        Returns:
            Dict mapping file IDs to thumbnail paths (successful generations only)
        """
        results = {}

        for file_record in file_records:
            try:
                thumbnail_path = self.generate_thumbnail(file_record, size)
                if thumbnail_path:
                    results[str(file_record.id)] = thumbnail_path

                    # Update the file record
                    file_record.thumbnail_path = thumbnail_path

            except Exception as e:
                logger.error(f"Failed to generate thumbnail for file {file_record.id}: {e}")

        # Commit all updates at once
        if results:
            try:
                db.session.commit()
                logger.info(f"Generated {len(results)} thumbnails")
            except Exception as e:
                logger.error(f"Failed to update database with thumbnail paths: {e}")
                db.session.rollback()

        return results