"""
Thumbnail and variant generation service for image optimization.

This service generates optimized image variants (thumbnails and previews)
to improve page load performance. It maintains the original images while
creating smaller, web-optimized versions.

Supports both local and R2 storage backends.
"""

import os
import io
import time
import logging
import requests
from typing import Dict, Optional, Tuple, List
from io import BytesIO
from flask import current_app

try:
    from PIL import Image, ImageOps, ImageFilter
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

from app.models import File, db
from app.services.storage_service import StorageService

logger = logging.getLogger(__name__)

# Configuration constants for multi-resolution variants
THUMBNAIL_SIZE = (200, 200)      # Small thumbnails for grid display
MEDIUM_WIDTH = 1200              # Medium preview width for lightbox
THUMBNAIL_QUALITY = 75           # JPEG quality for thumbnails (1-100)
MEDIUM_QUALITY = 85              # JPEG quality for medium previews (1-100)

# Supported image formats
SUPPORTED_FORMATS = {'.jpg', '.jpeg', '.png', '.webp', '.tiff', '.bmp', '.gif'}


class ThumbnailService:
    """Service for generating and managing image thumbnails and variants."""

    # Legacy thumbnail sizes for backward compatibility
    THUMBNAIL_SIZES = {
        'small': (150, 150),
        'medium': (300, 300),
        'large': (600, 600)
    }

    def __init__(self):
        self.storage_service = StorageService()
        self.r2_storage = getattr(current_app, 'r2_storage', None)
        self.backend = current_app.config.get('STORAGE_BACKEND', 'local')

    def generate_all_variants(self, file_record: File) -> Dict[str, any]:
        """
        Generate thumbnail and medium variants for a file using new multi-resolution approach.

        Args:
            file_record: File model instance

        Returns:
            Dict with:
                - success: bool
                - variants_generated: list of variant types created
                - errors: list of error messages (if any)
                - file_uuid: UUID of the file
        """
        if not PIL_AVAILABLE:
            logger.error("PIL/Pillow is not available. Cannot generate variants.")
            return {
                'success': False,
                'error': 'PIL not available',
                'variants_generated': [],
                'file_uuid': str(file_record.uuid)
            }

        if not file_record.is_image:
            logger.info(f"Skipping variant generation for non-image: {file_record.uuid}")
            return {
                'success': False,
                'error': 'Not an image file',
                'variants_generated': [],
                'file_uuid': str(file_record.uuid)
            }

        # Check if format is supported
        file_ext = os.path.splitext(file_record.original_filename)[1].lower()
        if file_ext not in SUPPORTED_FORMATS:
            logger.warning(f"Unsupported image format: {file_ext} for {file_record.uuid}")
            return {
                'success': False,
                'error': f'Unsupported format: {file_ext}',
                'variants_generated': [],
                'file_uuid': str(file_record.uuid)
            }

        try:
            # Download original image
            original_data = self._get_file_data(file_record)
            if not original_data:
                return {
                    'success': False,
                    'error': 'Failed to download original image',
                    'variants_generated': [],
                    'file_uuid': str(file_record.uuid)
                }

            # Open with PIL and validate
            try:
                image = Image.open(BytesIO(original_data))
                image.load()  # Force load to catch truncated/corrupted images
            except Exception as e:
                logger.error(f"Failed to open image {file_record.uuid}: {e}")
                return {
                    'success': False,
                    'error': 'Corrupted or invalid image file',
                    'variants_generated': [],
                    'file_uuid': str(file_record.uuid)
                }

            variants_generated = []
            errors = []

            # Generate thumbnail variant
            try:
                thumb_data = self._generate_thumbnail_variant(image)
                thumb_path = self._generate_variant_path(
                    file_record.storage_path, 'thumb'
                )
                self._upload_variant(thumb_data, thumb_path)
                file_record.thumb_path = thumb_path
                variants_generated.append('thumbnail')
                logger.debug(f"Generated thumbnail for {file_record.uuid}")
            except Exception as e:
                error_msg = f"Thumbnail generation failed: {str(e)}"
                logger.error(f"{error_msg} for {file_record.uuid}")
                errors.append(error_msg)

            # Generate medium preview variant
            try:
                medium_data = self._generate_medium_variant(image)
                medium_path = self._generate_variant_path(
                    file_record.storage_path, 'medium'
                )
                self._upload_variant(medium_data, medium_path)
                file_record.medium_path = medium_path
                variants_generated.append('medium')
                logger.debug(f"Generated medium preview for {file_record.uuid}")
            except Exception as e:
                error_msg = f"Medium variant generation failed: {str(e)}"
                logger.error(f"{error_msg} for {file_record.uuid}")
                errors.append(error_msg)

            # Commit database updates if any variants were generated
            if variants_generated:
                try:
                    db.session.commit()
                    logger.info(
                        f"Generated variants for {file_record.uuid}: {', '.join(variants_generated)}"
                    )
                except Exception as e:
                    logger.error(f"Failed to commit variant paths for {file_record.uuid}: {e}")
                    db.session.rollback()
                    errors.append(f"Database commit failed: {str(e)}")

            return {
                'success': len(variants_generated) > 0,
                'variants_generated': variants_generated,
                'file_uuid': str(file_record.uuid),
                'errors': errors if errors else None
            }

        except Exception as e:
            logger.error(f"Variant generation failed for {file_record.uuid}: {e}")
            return {
                'success': False,
                'error': str(e),
                'variants_generated': [],
                'file_uuid': str(file_record.uuid)
            }

    def _generate_thumbnail_variant(self, image: Image.Image) -> BytesIO:
        """Generate small thumbnail for grid display (square, cropped)."""
        return self._resize_image(
            image,
            size=THUMBNAIL_SIZE,
            quality=THUMBNAIL_QUALITY,
            crop_to_fit=True
        )

    def _generate_medium_variant(self, image: Image.Image) -> BytesIO:
        """Generate medium-size preview for lightbox (maintains aspect ratio)."""
        width, height = image.size

        # Calculate target size maintaining aspect ratio
        if width > MEDIUM_WIDTH:
            target_height = int((MEDIUM_WIDTH / width) * height)
            target_size = (MEDIUM_WIDTH, target_height)
        else:
            # Don't upscale small images
            target_size = (width, height)

        return self._resize_image(
            image,
            size=target_size,
            quality=MEDIUM_QUALITY,
            crop_to_fit=False
        )

    def _resize_image(
        self,
        image: Image.Image,
        size: Tuple[int, int],
        quality: int,
        crop_to_fit: bool = False
    ) -> BytesIO:
        """
        Resize image and return as BytesIO JPEG.

        Args:
            image: PIL Image object
            size: Target (width, height)
            quality: JPEG quality 1-100
            crop_to_fit: If True, crop to exact size; if False, fit within size

        Returns:
            BytesIO object containing the JPEG data
        """
        # Create a copy to avoid modifying original
        img = image.copy()

        # Apply orientation from EXIF data (handles rotated phone photos)
        try:
            img = ImageOps.exif_transpose(img)
        except Exception:
            pass  # Continue without orientation fix if it fails

        # Convert to RGB (handles RGBA, CMYK, palette modes)
        if img.mode not in ('RGB', 'L'):
            # For RGBA images, create white background
            if img.mode == 'RGBA':
                background = Image.new('RGB', img.size, (255, 255, 255))
                background.paste(img, mask=img.split()[3])  # Use alpha as mask
                img = background
            else:
                img = img.convert('RGB')

        # Resize using appropriate method
        if crop_to_fit:
            # Crop to exact size (for square thumbnails)
            img = ImageOps.fit(img, size, Image.Resampling.LANCZOS)
        else:
            # Fit within size maintaining aspect ratio
            img.thumbnail(size, Image.Resampling.LANCZOS)

        # Apply subtle sharpening for better perceived quality
        try:
            img = img.filter(ImageFilter.UnsharpMask(radius=0.5, percent=50, threshold=3))
        except Exception:
            pass  # Continue without sharpening if it fails

        # Save to BytesIO as optimized JPEG
        output = BytesIO()
        img.save(
            output,
            format='JPEG',
            quality=quality,
            optimize=True,          # Enable JPEG optimization
            progressive=True        # Progressive JPEG for better loading
        )
        output.seek(0)  # Reset position to beginning

        return output

    def _generate_variant_path(self, original_path: str, variant_type: str) -> str:
        """
        Generate organized storage path for variant.

        Example:
            Input:  "collections/abc-123/photo.jpg"
            Output: "collections/abc-123/variants/thumb_photo.jpg"
        """
        path_parts = original_path.rsplit('/', 1)
        if len(path_parts) == 2:
            directory, filename = path_parts
        else:
            directory = ''
            filename = original_path

        # Remove extension and add variant prefix
        name_without_ext = os.path.splitext(filename)[0]
        variant_filename = f"{variant_type}_{name_without_ext}.jpg"

        # Organize in variants subdirectory
        if directory:
            return f"{directory}/variants/{variant_filename}"
        else:
            return f"variants/{variant_filename}"

    def _upload_variant(self, image_data: BytesIO, storage_path: str) -> bool:
        """Upload variant to storage backend."""
        try:
            image_data.seek(0)  # Ensure position is at start

            if self.backend == 'r2' and self.r2_storage:
                # Upload to R2
                self.r2_storage.upload_single_file(
                    file_obj=image_data,
                    key=storage_path,
                    filename=os.path.basename(storage_path)
                )
            else:
                # Upload to local storage
                file_path = os.path.join(current_app.instance_path, storage_path)
                os.makedirs(os.path.dirname(file_path), exist_ok=True)

                with open(file_path, 'wb') as f:
                    f.write(image_data.read())

            return True

        except Exception as e:
            logger.error(f"Failed to upload variant to {storage_path}: {e}")
            raise

    def batch_generate_variants(
        self,
        file_records: List[File],
        max_workers: int = 3
    ) -> Dict[str, any]:
        """
        Generate variants for multiple files with controlled concurrency.

        Args:
            file_records: List of File model instances
            max_workers: Max concurrent threads (keep low for CPU-bound work)

        Returns:
            Dict with success/failure counts and detailed results
        """
        from concurrent.futures import ThreadPoolExecutor, as_completed

        results = []

        # Use ThreadPoolExecutor with limited workers (image processing is CPU-bound)
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_file = {
                executor.submit(self.generate_all_variants, file_record): file_record
                for file_record in file_records
            }

            for future in as_completed(future_to_file):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    file_record = future_to_file[future]
                    logger.error(f"Exception in batch processing for {file_record.uuid}: {e}")
                    results.append({
                        'success': False,
                        'error': str(e),
                        'variants_generated': [],
                        'file_uuid': str(file_record.uuid)
                    })

        success_count = sum(1 for r in results if r.get('success'))

        return {
            'total': len(file_records),
            'successful': success_count,
            'failed': len(file_records) - success_count,
            'results': results
        }

    # Legacy method - keep for backward compatibility
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