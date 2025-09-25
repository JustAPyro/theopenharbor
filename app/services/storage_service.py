"""
Storage service providing unified interface for file operations.
Supports both local and CloudflareR2 storage backends.
"""

import os
import time
import logging
import mimetypes
from typing import List, Dict, Optional, BinaryIO, Union
from io import BytesIO
from flask import current_app

from app.integrations.file_storage import CloudflareR2Storage, ValidationError, UploadError
from app.models import File, Collection

logger = logging.getLogger(__name__)


class StorageService:
    """Unified storage service supporting multiple backends."""

    def __init__(self):
        self.backend = current_app.config.get('STORAGE_BACKEND', 'local')
        self.r2_storage = getattr(current_app, 'r2_storage', None)

    def upload_file(self, file_obj: BinaryIO, filename: str, collection: Collection,
                   progress_callback: Optional[callable] = None) -> Dict[str, any]:
        """
        Upload a single file to the configured storage backend.

        Args:
            file_obj: File object to upload
            filename: Original filename
            collection: Collection instance
            progress_callback: Optional progress callback function

        Returns:
            Dict containing upload result with keys:
                - success: bool
                - file_record: File model instance (if success)
                - error: str (if not success)
                - storage_info: dict with backend-specific info
        """
        try:
            if self.backend == 'r2' and self.r2_storage:
                return self._upload_to_r2(file_obj, filename, collection, progress_callback)
            else:
                return self._upload_to_local(file_obj, filename, collection)

        except Exception as e:
            logger.error(f"Upload failed for {filename}: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'file_record': None,
                'storage_info': None
            }

    def _upload_to_r2(self, file_obj: BinaryIO, filename: str, collection: Collection,
                     progress_callback: Optional[callable] = None) -> Dict[str, any]:
        """Upload file to CloudflareR2 storage."""
        try:
            # Generate storage key with collection context
            storage_key = f"collections/{collection.uuid}/{filename}"

            # Add metadata for tracking
            metadata = {
                'collection_id': str(collection.id),
                'collection_uuid': str(collection.uuid),
                'original_filename': filename,
                'upload_timestamp': str(int(time.time()))
            }

            # Upload to R2
            result = self.r2_storage.upload_single_file(
                file_obj=file_obj,
                filename=filename,
                key=storage_key,
                metadata=metadata,
                progress_callback=progress_callback
            )

            # Create database record
            file_record = File(
                filename=os.path.basename(result['key']),
                original_filename=filename,
                mime_type=self._get_mime_type(filename),
                size=result['size'],
                storage_path=result['key'],  # R2 key path
                storage_backend='r2',
                upload_complete=True,
                collection_id=collection.id
            )

            # Set R2 metadata
            file_record.set_metadata({
                'upload_method': result.get('upload_method', 'unknown'),
                'r2_bucket': result.get('bucket'),
                'parts_count': result.get('parts_count'),
                'part_size': result.get('part_size')
            })

            return {
                'success': True,
                'file_record': file_record,
                'error': None,
                'storage_info': result
            }

        except (ValidationError, UploadError) as e:
            return {
                'success': False,
                'error': str(e),
                'file_record': None,
                'storage_info': None
            }

    def _upload_to_local(self, file_obj: BinaryIO, filename: str, collection: Collection) -> Dict[str, any]:
        """Upload file to local storage (fallback/development)."""
        try:
            import uuid

            # Generate unique filename
            file_uuid = str(uuid.uuid4())
            file_extension = os.path.splitext(filename)[1].lower()
            storage_filename = f"{file_uuid}{file_extension}"

            # Create upload directory
            upload_dir = os.path.join(current_app.instance_path, 'uploads', str(collection.uuid))
            os.makedirs(upload_dir, exist_ok=True)

            # Save file
            storage_path = os.path.join(upload_dir, storage_filename)

            # Reset file object position
            file_obj.seek(0)

            with open(storage_path, 'wb') as f:
                f.write(file_obj.read())

            # Create database record
            file_record = File(
                filename=storage_filename,
                original_filename=filename,
                mime_type=self._get_mime_type(filename),
                size=os.path.getsize(storage_path),
                storage_path=f"uploads/{collection.uuid}/{storage_filename}",
                storage_backend='local',
                upload_complete=True,
                collection_id=collection.id
            )

            return {
                'success': True,
                'file_record': file_record,
                'error': None,
                'storage_info': {'upload_method': 'local', 'path': storage_path}
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'file_record': None,
                'storage_info': None
            }

    def generate_file_url(self, file_record: File, expiry_seconds: int = 3600) -> str:
        """Generate a URL for file access."""
        if self.backend == 'r2' and self.r2_storage:
            return self.r2_storage.generate_presigned_url(
                file_record.storage_path,
                expiry_seconds=expiry_seconds
            )
        else:
            # Local file URL generation
            from flask import url_for
            return url_for('collections.serve_file', file_uuid=file_record.uuid)

    def delete_file(self, file_record: File) -> bool:
        """Delete file from storage."""
        try:
            if self.backend == 'r2' and self.r2_storage:
                return self.r2_storage.delete_file(file_record.storage_path)
            else:
                # Local file deletion
                file_path = os.path.join(current_app.instance_path, file_record.storage_path)
                if os.path.exists(file_path):
                    os.remove(file_path)
                    return True
                return False
        except Exception as e:
            logger.error(f"Failed to delete file {file_record.uuid}: {e}")
            return False

    def batch_upload(self, files_data: List[Dict], collection: Collection,
                    progress_callback: Optional[callable] = None) -> List[Dict]:
        """Upload multiple files with progress tracking."""
        if self.backend == 'r2' and self.r2_storage:
            return self._batch_upload_r2(files_data, collection, progress_callback)
        else:
            return self._batch_upload_local(files_data, collection)

    def _batch_upload_r2(self, files_data: List[Dict], collection: Collection,
                        progress_callback: Optional[callable] = None) -> List[Dict]:
        """Batch upload to R2 storage."""
        results = []
        total_files = len(files_data)
        completed_files = 0

        for file_data in files_data:
            try:
                file_obj = file_data['file_obj']
                filename = file_data.get('filename')

                # Individual file progress callback
                def file_progress(uploaded, total):
                    if progress_callback:
                        progress_callback(completed_files, total_files, uploaded, total)

                result = self.upload_file(
                    file_obj=file_obj,
                    filename=filename,
                    collection=collection,
                    progress_callback=file_progress
                )

                completed_files += 1
                results.append(result)

            except Exception as e:
                logger.error(f"Failed to upload file {file_data.get('filename', 'unknown')}: {e}")
                results.append({
                    'success': False,
                    'error': str(e),
                    'file_record': None,
                    'storage_info': None
                })
                completed_files += 1

        return results

    def _batch_upload_local(self, files_data: List[Dict], collection: Collection) -> List[Dict]:
        """Batch upload to local storage."""
        results = []

        for file_data in files_data:
            try:
                file_obj = file_data['file_obj']
                filename = file_data.get('filename')

                result = self.upload_file(
                    file_obj=file_obj,
                    filename=filename,
                    collection=collection
                )

                results.append(result)

            except Exception as e:
                logger.error(f"Failed to upload file {file_data.get('filename', 'unknown')}: {e}")
                results.append({
                    'success': False,
                    'error': str(e),
                    'file_record': None,
                    'storage_info': None
                })

        return results

    def get_file_info(self, file_record: File) -> Optional[Dict]:
        """Get file information from storage."""
        if self.backend == 'r2' and self.r2_storage:
            return self.r2_storage.get_file_info(file_record.storage_path)
        else:
            # Local file info
            file_path = os.path.join(current_app.instance_path, file_record.storage_path)
            if os.path.exists(file_path):
                stat = os.stat(file_path)
                return {
                    'key': file_record.storage_path,
                    'size': stat.st_size,
                    'last_modified': stat.st_mtime,
                    'exists': True
                }
            return None

    def _get_mime_type(self, filename: str) -> str:
        """Get MIME type from filename."""
        mime_type, _ = mimetypes.guess_type(filename)
        return mime_type or 'application/octet-stream'