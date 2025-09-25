# CloudflareR2 Storage Integration Implementation Guide

## Project Overview

This document provides a comprehensive step-by-step implementation plan for integrating CloudflareR2 storage with The Open Harbor collection upload system. The integration will replace the current local file storage with cloud-based R2 storage, providing scalable file management with enhanced performance and reliability.

## Current System Architecture

### Existing Upload Flow
1. User creates collection with form data (name, description, privacy settings)
2. Files selected via drag-drop or file browser
3. Client-side validation (file type, size limits)
4. Collection created in database
5. Files uploaded to local storage (`instance_path/uploads/{collection_uuid}/`)
6. File records created in database with local `storage_path`

### Current File Limits
- **Max file size**: 50MB per file
- **Max total size**: 10GB per collection
- **No file count limit**: Optimized for photo shoots
- **Supported formats**: JPG, PNG, HEIC, TIFF, RAW formats

## Integration Goals

### Primary Objectives
- Replace local file storage with CloudflareR2 storage
- Maintain existing user experience and functionality
- Implement proper error handling and retry mechanisms
- Add comprehensive progress tracking for uploads
- Support large file uploads with multipart functionality
- Provide efficient thumbnail generation pipeline

### Performance Requirements
- Support concurrent uploads (5 simultaneous files)
- Progress tracking with sub-second updates
- Graceful handling of network interruptions
- Automatic retry with exponential backoff
- Memory-efficient handling of large files

## Implementation Plan

### Phase 1: Backend Infrastructure Setup

#### Step 1.1: Environment Configuration
**File:** `.env` (production), `.env.example` (template)

Add R2 configuration variables:
```bash
# Cloudflare R2 Storage Configuration
R2_ACCOUNT_ID=your_cloudflare_account_id
R2_ACCESS_KEY_ID=your_r2_access_key
R2_SECRET_ACCESS_KEY=your_r2_secret_key
R2_BUCKET_NAME=openharbor-files
R2_REGION=auto

# Storage Configuration
STORAGE_BACKEND=r2  # Options: local, r2
THUMBNAIL_BUCKET=openharbor-thumbnails  # Optional separate bucket for thumbnails
```

**⚠️ WARNING:** Never commit actual credentials to version control. Always use placeholder values in `.env.example`.

#### Step 1.2: Application Factory Integration
**File:** `app/__init__.py`

Modify the `create_app()` function to initialize R2 storage:

```python
from app.integrations.file_storage import CloudflareR2Storage, FileStorageError

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login.init_app(app)
    csrf.init_app(app)

    # Initialize R2 Storage
    try:
        if app.config.get('STORAGE_BACKEND') == 'r2':
            app.r2_storage = CloudflareR2Storage()
            app.logger.info("CloudflareR2 storage initialized successfully")
        else:
            app.r2_storage = None
            app.logger.info("Using local storage backend")
    except FileStorageError as e:
        app.logger.error(f"Failed to initialize R2 storage: {e}")
        if not app.config.get('TESTING'):
            raise  # Fail fast in production

    # Register blueprints...
```

**⚠️ WARNING:** Handle R2 initialization failures gracefully. In development, you might want to fall back to local storage, but in production, you should fail fast to prevent data inconsistency.

#### Step 1.3: Configuration Class Updates
**File:** `config.py`

Add storage-related configuration:

```python
class Config:
    # Existing configuration...

    # Storage Configuration
    STORAGE_BACKEND = os.environ.get('STORAGE_BACKEND', 'local')
    R2_ACCOUNT_ID = os.environ.get('R2_ACCOUNT_ID')
    R2_ACCESS_KEY_ID = os.environ.get('R2_ACCESS_KEY_ID')
    R2_SECRET_ACCESS_KEY = os.environ.get('R2_SECRET_ACCESS_KEY')
    R2_BUCKET_NAME = os.environ.get('R2_BUCKET_NAME')
    R2_REGION = os.environ.get('R2_REGION', 'auto')

    # File Upload Limits (matching R2 integration)
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB per file
    MAX_TOTAL_SIZE = 10 * 1024 * 1024 * 1024  # 10GB per collection
    MAX_BATCH_FILES = 100  # For batch operations

    @staticmethod
    def validate_required_config():
        """Validate that required configuration is present."""
        if Config.STORAGE_BACKEND == 'r2':
            required_vars = [
                'R2_ACCOUNT_ID', 'R2_ACCESS_KEY_ID',
                'R2_SECRET_ACCESS_KEY', 'R2_BUCKET_NAME'
            ]
            missing = [var for var in required_vars if not getattr(Config, var)]
            if missing:
                raise ValueError(f"Missing required R2 configuration: {', '.join(missing)}")
```

### Phase 2: Storage Service Layer

#### Step 2.1: Create Storage Service Abstraction
**File:** `app/services/storage_service.py` (NEW FILE)

Create a service layer that abstracts storage operations:

```python
"""
Storage service providing unified interface for file operations.
Supports both local and CloudflareR2 storage backends.
"""

import os
import logging
from typing import List, Dict, Optional, BinaryIO
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
                upload_complete=True,
                collection_id=collection.id
            )

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
        # Implementation for local storage fallback
        # This maintains backward compatibility for development
        pass

    def generate_file_url(self, file_record: File, expiry_seconds: int = 3600) -> str:
        """Generate a URL for file access."""
        if self.backend == 'r2' and self.r2_storage:
            return self.r2_storage.generate_presigned_url(
                file_record.storage_path,
                expiry_seconds=expiry_seconds
            )
        else:
            # Local file URL generation
            return f"/files/{file_record.uuid}"

    def delete_file(self, file_record: File) -> bool:
        """Delete file from storage."""
        if self.backend == 'r2' and self.r2_storage:
            return self.r2_storage.delete_file(file_record.storage_path)
        else:
            # Local file deletion
            pass

    def batch_upload(self, files_data: List[Dict], collection: Collection,
                    progress_callback: Optional[callable] = None) -> List[Dict]:
        """Upload multiple files with progress tracking."""
        if self.backend == 'r2' and self.r2_storage:
            return self._batch_upload_r2(files_data, collection, progress_callback)
        else:
            return self._batch_upload_local(files_data, collection)

    def _get_mime_type(self, filename: str) -> str:
        """Get MIME type from filename."""
        import mimetypes
        mime_type, _ = mimetypes.guess_type(filename)
        return mime_type or 'application/octet-stream'
```

**⚠️ WARNING:** Always validate file objects before passing to storage. The service layer should handle all validation to prevent malformed data from reaching storage backends.

#### Step 2.2: Update Upload Route Handler
**File:** `app/views/collections/collections_routes.py`

Replace the current upload implementation:

```python
from app.services.storage_service import StorageService

@collections.route('/api/upload-files', methods=['POST'])
@login_required
def upload_files():
    """API endpoint to handle file uploads with R2 integration."""
    try:
        collection_id = request.form.get('collection_id')
        if not collection_id:
            return jsonify({'success': False, 'error': 'Collection ID required'}), 400

        # Verify collection ownership
        collection = Collection.query.filter_by(
            id=collection_id,
            user_id=current_user.id
        ).first()

        if not collection:
            return jsonify({'success': False, 'error': 'Collection not found'}), 404

        storage_service = StorageService()
        uploaded_files = []
        upload_errors = []

        def progress_callback(file_key, bytes_uploaded, total_bytes):
            """Progress callback for individual file uploads."""
            # This could be extended to use WebSocket for real-time updates
            progress_percent = (bytes_uploaded / total_bytes) * 100
            current_app.logger.debug(
                f"Upload progress for {file_key}: {progress_percent:.1f}%"
            )

        for file_key in request.files:
            file = request.files[file_key]
            if file and file.filename:
                try:
                    # Create progress callback for this specific file
                    file_progress = lambda uploaded, total: progress_callback(
                        file.filename, uploaded, total
                    )

                    # Upload file using storage service
                    result = storage_service.upload_file(
                        file_obj=file.stream,
                        filename=file.filename,
                        collection=collection,
                        progress_callback=file_progress
                    )

                    if result['success']:
                        db.session.add(result['file_record'])
                        uploaded_files.append({
                            'filename': file.filename,
                            'size': result['file_record'].size,
                            'uuid': result['file_record'].uuid,
                            'storage_info': result['storage_info']
                        })
                    else:
                        upload_errors.append({
                            'filename': file.filename,
                            'error': result['error']
                        })

                except Exception as e:
                    upload_errors.append({
                        'filename': file.filename,
                        'error': str(e)
                    })

        if uploaded_files:
            db.session.commit()
            current_app.logger.info(
                f"Uploaded {len(uploaded_files)} files to collection {collection_id}"
            )

        return jsonify({
            'success': True,
            'uploaded_files': uploaded_files,
            'errors': upload_errors,
            'collection_url': url_for('collections.view', uuid=collection.uuid)
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"File upload error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Server error during upload'
        }), 500
```

**⚠️ WARNING:** Always wrap database operations in try-catch blocks and rollback on errors. File uploads can fail partially, leaving the database in an inconsistent state.

### Phase 3: Frontend Integration Updates

#### Step 3.1: Enhanced Progress Tracking
**File:** `app/views/collections/static/js/upload.js`

Update the upload method to handle R2-specific progress tracking:

```javascript
async uploadFiles(collectionId) {
    const validFiles = Array.from(this.files.values()).filter(f => f.status === 'valid');
    const totalFiles = validFiles.length;
    let completedFiles = 0;
    let totalBytes = validFiles.reduce((sum, file) => sum + file.file.size, 0);
    let uploadedBytes = 0;

    this.updateProgress(0, `Preparing upload...`);

    // Enhanced progress tracking for R2 uploads
    const fileProgressMap = new Map();

    // Upload files in batches to prevent overwhelming the server
    const batchSize = this.config.maxConcurrentUploads;
    for (let i = 0; i < validFiles.length; i += batchSize) {
        const batch = validFiles.slice(i, i + batchSize);

        const uploadPromises = batch.map(async (fileObj) => {
            const formData = new FormData();
            formData.append('collection_id', collectionId);
            formData.append(`file_${fileObj.id}`, fileObj.file);

            try {
                // Track progress for this specific file
                fileProgressMap.set(fileObj.id, { uploaded: 0, total: fileObj.file.size });

                const response = await this.uploadWithProgress(
                    '/collections/api/upload-files',
                    formData,
                    (progress) => this.handleFileProgress(fileObj.id, progress, fileProgressMap, totalBytes)
                );

                if (response.success) {
                    fileObj.status = 'uploaded';
                    completedFiles++;
                    this.updateFileCardStatus(fileObj.id, 'success');

                    // Update loading overlay
                    this.updateLoadingOverlay(completedFiles, totalFiles, uploadedBytes, totalBytes);
                } else {
                    fileObj.status = 'error';
                    fileObj.error = response.error || 'Upload failed';
                    this.updateFileCardStatus(fileObj.id, 'error', fileObj.error);
                    this.showError(`Failed to upload ${fileObj.file.name}: ${fileObj.error}`);
                }

                return response;

            } catch (error) {
                fileObj.status = 'error';
                fileObj.error = error.message;
                this.updateFileCardStatus(fileObj.id, 'error', error.message);
                return { success: false, error: error.message };
            }
        });

        // Wait for batch to complete before starting next batch
        await Promise.all(uploadPromises);

        // Update overall progress
        const overallProgress = (completedFiles / totalFiles) * 100;
        this.updateProgress(overallProgress, `Uploaded ${completedFiles} of ${totalFiles} files`);
    }

    const successfulUploads = validFiles.filter(f => f.status === 'uploaded').length;
    const failedUploads = validFiles.filter(f => f.status === 'error').length;

    if (successfulUploads > 0) {
        this.updateProgress(100, `Upload complete: ${successfulUploads} files uploaded successfully`);

        if (failedUploads > 0) {
            this.showWarning(`${successfulUploads} files uploaded successfully, ${failedUploads} failed`);
        }
    } else {
        this.showError('All file uploads failed');
    }
}

handleFileProgress(fileId, progress, progressMap, totalBytes) {
    // Update individual file progress
    const fileProgress = progressMap.get(fileId);
    if (fileProgress) {
        fileProgress.uploaded = (progress.loaded || 0);

        // Calculate overall upload progress
        let totalUploaded = 0;
        for (const [id, prog] of progressMap) {
            totalUploaded += prog.uploaded;
        }

        const overallPercent = (totalUploaded / totalBytes) * 100;
        this.updateLoadingProgress(overallPercent, totalUploaded, totalBytes);
    }
}

async uploadWithProgress(url, formData, progressCallback) {
    return new Promise((resolve, reject) => {
        const xhr = new XMLHttpRequest();

        xhr.upload.addEventListener('progress', (e) => {
            if (e.lengthComputable && progressCallback) {
                progressCallback({
                    loaded: e.loaded,
                    total: e.total,
                    percent: (e.loaded / e.total) * 100
                });
            }
        });

        xhr.addEventListener('load', () => {
            try {
                const response = JSON.parse(xhr.responseText);
                resolve(response);
            } catch (e) {
                reject(new Error('Invalid response format'));
            }
        });

        xhr.addEventListener('error', () => {
            reject(new Error('Network error during upload'));
        });

        xhr.addEventListener('abort', () => {
            reject(new Error('Upload was cancelled'));
        });

        xhr.open('POST', url);
        xhr.setRequestHeader('X-Requested-With', 'XMLHttpRequest');
        xhr.send(formData);
    });
}
```

**⚠️ WARNING:** XMLHttpRequest progress events only track upload progress, not processing time on the server. For large files, there may be a delay between upload completion and server response.

#### Step 3.2: Error Handling Improvements
**File:** `app/views/collections/static/js/upload.js`

Add comprehensive error handling for R2-specific errors:

```javascript
handleUploadError(error, filename) {
    console.error('Upload error:', error);

    // Map R2-specific errors to user-friendly messages
    const errorMappings = {
        'ValidationError': 'File validation failed',
        'UploadError': 'Upload failed due to network issues',
        'AccessDenied': 'Insufficient permissions to upload file',
        'EntityTooLarge': 'File size exceeds storage limits',
        'InvalidRequest': 'Invalid file format or corrupted file',
        'NetworkError': 'Network connection lost during upload'
    };

    let userMessage = error.message || error;

    // Check for known error patterns
    for (const [errorType, message] of Object.entries(errorMappings)) {
        if (userMessage.includes(errorType)) {
            userMessage = `${message}. Please try again.`;
            break;
        }
    }

    // Show retry option for recoverable errors
    const isRetryable = [
        'NetworkError', 'UploadError', 'timeout'
    ].some(type => userMessage.includes(type));

    if (isRetryable) {
        this.showRetryableError(userMessage, filename);
    } else {
        this.showError(`${filename}: ${userMessage}`);
    }
}

showRetryableError(message, filename) {
    const errorHtml = `
        <div class="alert alert-warning alert-dismissible fade show" role="alert">
            <i class="bi bi-exclamation-triangle me-2"></i>
            ${message}
            <button type="button" class="btn btn-sm btn-outline-primary ms-2"
                    onclick="collectionUploader.retryUpload('${filename}')">
                <i class="bi bi-arrow-clockwise me-1"></i>Retry
            </button>
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `;

    const container = document.getElementById('errorContainer') || this.elements.errorAlert.parentNode;
    container.insertAdjacentHTML('beforeend', errorHtml);
}
```

### Phase 4: File Serving and URL Generation

#### Step 4.1: File Serving Route
**File:** `app/views/collections/collections_routes.py`

Add route for serving files through presigned URLs:

```python
@collections.route('/files/<uuid:file_uuid>')
def serve_file(file_uuid):
    """Serve file through presigned URL or direct serving."""
    file_record = File.query.filter_by(uuid=str(file_uuid)).first_or_404()

    # Check access permissions
    collection = file_record.collection

    # Handle password-protected collections
    if collection.privacy == 'password':
        # Check if password was provided in session
        session_key = f'collection_access_{collection.uuid}'
        if session_key not in session:
            return redirect(url_for('collections.password_required', uuid=collection.uuid))

    # Check expiration
    if collection.expires_at and collection.expires_at < datetime.now(timezone.utc):
        abort(410)  # Gone

    try:
        storage_service = StorageService()
        file_url = storage_service.generate_file_url(file_record, expiry_seconds=3600)

        # Redirect to presigned URL for direct R2 access
        # This reduces server load and provides better performance
        return redirect(file_url)

    except Exception as e:
        current_app.logger.error(f"Failed to generate file URL for {file_uuid}: {e}")
        abort(500)

@collections.route('/files/<uuid:file_uuid>/thumbnail')
def serve_thumbnail(file_uuid):
    """Serve thumbnail if available."""
    file_record = File.query.filter_by(uuid=str(file_uuid)).first_or_404()

    # Similar access control as serve_file...

    if file_record.thumbnail_path:
        storage_service = StorageService()
        thumbnail_url = storage_service.generate_file_url(
            file_record.thumbnail_path,
            expiry_seconds=7200  # Longer cache for thumbnails
        )
        return redirect(thumbnail_url)
    else:
        # Generate thumbnail on-demand if not exists
        return redirect(url_for('collections.generate_thumbnail', file_uuid=file_uuid))
```

#### Step 4.2: Thumbnail Generation Service
**File:** `app/services/thumbnail_service.py` (NEW FILE)

Create a service for generating and managing thumbnails:

```python
"""
Thumbnail generation service for uploaded images.
Supports both local and R2 storage backends.
"""

import os
import io
from PIL import Image, ImageOps
from typing import Optional, Tuple
from flask import current_app

from app.models import File, db
from app.services.storage_service import StorageService

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
        if size not in self.THUMBNAIL_SIZES:
            raise ValueError(f"Invalid thumbnail size: {size}")

        try:
            # Download original file from storage
            original_url = self.storage_service.generate_file_url(file_record)

            # Process image
            thumbnail_data = self._create_thumbnail_data(original_url, size)
            if not thumbnail_data:
                return None

            # Upload thumbnail to storage
            thumbnail_key = f"thumbnails/{file_record.collection.uuid}/{size}_{file_record.filename}"

            # Upload thumbnail
            if self.storage_service.backend == 'r2':
                result = self.storage_service.r2_storage.upload_single_file(
                    file_obj=io.BytesIO(thumbnail_data),
                    key=thumbnail_key,
                    metadata={
                        'original_file_id': str(file_record.id),
                        'thumbnail_size': size,
                        'generated_timestamp': str(int(time.time()))
                    }
                )

                # Update file record
                if size == 'medium':  # Use medium as default thumbnail
                    file_record.thumbnail_path = result['key']
                    db.session.commit()

                return result['key']

        except Exception as e:
            current_app.logger.error(f"Thumbnail generation failed for {file_record.id}: {e}")
            return None

    def _create_thumbnail_data(self, image_url: str, size: str) -> Optional[bytes]:
        """Create thumbnail data from image URL."""
        try:
            # Download and process image
            import requests
            response = requests.get(image_url)
            response.raise_for_status()

            # Open and resize image
            image = Image.open(io.BytesIO(response.content))

            # Convert to RGB if necessary
            if image.mode in ('RGBA', 'LA', 'P'):
                image = image.convert('RGB')

            # Create thumbnail maintaining aspect ratio
            thumbnail_size = self.THUMBNAIL_SIZES[size]
            image.thumbnail(thumbnail_size, Image.Resampling.LANCZOS)

            # Save to bytes
            output = io.BytesIO()
            image.save(output, format='JPEG', quality=85, optimize=True)
            return output.getvalue()

        except Exception as e:
            current_app.logger.error(f"Image processing failed: {e}")
            return None
```

### Phase 5: Database Schema Updates

#### Step 5.1: Database Migration
**File:** `migrations/versions/xxx_add_r2_storage_fields.py` (GENERATED)

Create migration to add R2-specific fields:

```python
"""Add R2 storage support fields

Revision ID: xxx
Revises: yyy
Create Date: 2024-XX-XX XX:XX:XX.XXXXXX
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = 'xxx'
down_revision = 'yyy'
branch_labels = None
depends_on = None

def upgrade():
    # Add new columns to files table
    op.add_column('files', sa.Column('r2_key', sa.String(500), nullable=True))
    op.add_column('files', sa.Column('r2_bucket', sa.String(100), nullable=True))
    op.add_column('files', sa.Column('r2_version_id', sa.String(100), nullable=True))
    op.add_column('files', sa.Column('thumbnail_generated', sa.Boolean(), default=False))
    op.add_column('files', sa.Column('metadata_json', sa.Text(), nullable=True))

    # Add indexes for performance
    op.create_index('ix_files_r2_key', 'files', ['r2_key'])
    op.create_index('ix_files_thumbnail_generated', 'files', ['thumbnail_generated'])

def downgrade():
    # Remove indexes
    op.drop_index('ix_files_thumbnail_generated', table_name='files')
    op.drop_index('ix_files_r2_key', table_name='files')

    # Remove columns
    op.drop_column('files', 'metadata_json')
    op.drop_column('files', 'thumbnail_generated')
    op.drop_column('files', 'r2_version_id')
    op.drop_column('files', 'r2_bucket')
    op.drop_column('files', 'r2_key')
```

#### Step 5.2: Model Updates
**File:** `app/models.py`

Update File model to support R2 storage:

```python
class File(db.Model):
    """File model for uploaded files with R2 storage support."""

    __tablename__ = 'files'

    # Existing fields...

    # R2-specific fields
    r2_key = db.Column(db.String(500))  # R2 object key
    r2_bucket = db.Column(db.String(100))  # R2 bucket name
    r2_version_id = db.Column(db.String(100))  # R2 object version
    thumbnail_generated = db.Column(db.Boolean, default=False)
    metadata_json = db.Column(db.Text)  # JSON metadata from R2

    @property
    def is_r2_file(self):
        """Check if file is stored in R2."""
        return bool(self.r2_key and self.r2_bucket)

    @property
    def storage_url(self):
        """Get storage URL based on backend."""
        if self.is_r2_file:
            from app.services.storage_service import StorageService
            storage = StorageService()
            return storage.generate_file_url(self)
        else:
            return url_for('collections.serve_local_file', file_uuid=self.uuid)

    def get_metadata(self):
        """Parse and return metadata JSON."""
        if self.metadata_json:
            import json
            try:
                return json.loads(self.metadata_json)
            except json.JSONDecodeError:
                return {}
        return {}

    def set_metadata(self, metadata_dict):
        """Set metadata as JSON string."""
        if metadata_dict:
            import json
            self.metadata_json = json.dumps(metadata_dict)
        else:
            self.metadata_json = None
```

### Phase 6: Testing Strategy

#### Step 6.1: Update Existing Tests
**File:** `tests/collections/test_collections.py`

Update validation tests to match R2 limits:

```python
def test_validate_total_size_too_large(self, client, test_user):
    """Test validation rejects when total size exceeds R2 limit."""
    with client.session_transaction() as sess:
        sess['_user_id'] = str(test_user.id)
        sess['_fresh'] = True

    # Create files totaling over 10GB (updated limit)
    files_data = [
        {
            'name': f'photo{i}.jpg',
            'type': 'image/jpeg',
            'size': 2 * 1024 * 1024 * 1024  # 2GB each
        } for i in range(6)  # Total: 12GB > 10GB limit
    ]

    response = client.post('/collections/api/validate-files',
                          json={'files': files_data})

    assert response.status_code == 400
    data = response.get_json()
    assert data['success'] is False
    assert '10GB' in data['error']  # Updated error message
```

#### Step 6.2: R2 Integration Tests
**File:** `tests/integration/test_r2_storage.py` (NEW FILE)

Create comprehensive R2 integration tests:

```python
"""Integration tests for R2 storage functionality."""

import pytest
import io
import os
from unittest.mock import patch, MagicMock

from app.services.storage_service import StorageService
from app.integrations.file_storage import CloudflareR2Storage, ValidationError

class TestR2StorageIntegration:
    """Test R2 storage integration with mocked R2 client."""

    @pytest.fixture
    def mock_r2_client(self):
        """Mock R2 client for testing."""
        with patch('app.integrations.file_storage.boto3.client') as mock_client:
            mock_instance = MagicMock()
            mock_client.return_value = mock_instance

            # Mock successful responses
            mock_instance.head_bucket.return_value = {}
            mock_instance.upload_fileobj.return_value = {}
            mock_instance.generate_presigned_url.return_value = 'https://example.com/file.jpg'

            yield mock_instance

    def test_storage_service_initialization(self, app, mock_r2_client):
        """Test storage service initializes correctly."""
        with app.app_context():
            app.config['STORAGE_BACKEND'] = 'r2'
            app.r2_storage = CloudflareR2Storage()

            storage = StorageService()
            assert storage.backend == 'r2'
            assert storage.r2_storage is not None

    def test_file_upload_to_r2(self, app, test_collection, mock_r2_client):
        """Test file upload to R2 storage."""
        with app.app_context():
            app.config['STORAGE_BACKEND'] = 'r2'
            app.r2_storage = CloudflareR2Storage()

            storage = StorageService()

            # Create test file
            test_file = io.BytesIO(b'test file content')
            test_filename = 'test.jpg'

            # Mock R2 upload response
            mock_r2_client.upload_fileobj.return_value = {}

            result = storage.upload_file(
                file_obj=test_file,
                filename=test_filename,
                collection=test_collection
            )

            assert result['success'] is True
            assert result['file_record'] is not None
            assert result['file_record'].original_filename == test_filename

    def test_error_handling(self, app, test_collection, mock_r2_client):
        """Test error handling for R2 failures."""
        with app.app_context():
            app.config['STORAGE_BACKEND'] = 'r2'
            app.r2_storage = CloudflareR2Storage()

            storage = StorageService()

            # Mock R2 error
            from botocore.exceptions import ClientError
            mock_r2_client.upload_fileobj.side_effect = ClientError(
                {'Error': {'Code': 'AccessDenied'}}, 'UploadFile'
            )

            test_file = io.BytesIO(b'test content')

            result = storage.upload_file(
                file_obj=test_file,
                filename='test.jpg',
                collection=test_collection
            )

            assert result['success'] is False
            assert 'AccessDenied' in result['error'] or 'permission' in result['error'].lower()
```

### Phase 7: Deployment and Configuration

#### Step 7.1: Environment Setup
**File:** `deploy/environment-setup.md` (NEW FILE)

Document R2 setup requirements:

```markdown
# R2 Storage Environment Setup

## Cloudflare R2 Configuration

1. **Create R2 Bucket:**
   ```bash
   # Using Cloudflare CLI (wrangler)
   npx wrangler r2 bucket create openharbor-files
   npx wrangler r2 bucket create openharbor-thumbnails
   ```

2. **Generate API Tokens:**
   - Go to Cloudflare Dashboard > R2 Object Storage
   - Create API token with permissions:
     - `Object Storage:Edit` for upload/delete operations
     - `Object Storage:Read` for file serving
   - Note: Use separate tokens for production and development

3. **Configure CORS (if serving files directly):**
   ```json
   [
     {
       "AllowedOrigins": ["https://your-domain.com"],
       "AllowedMethods": ["GET", "PUT", "POST"],
       "AllowedHeaders": ["*"],
       "MaxAgeSeconds": 3000
     }
   ]
   ```

## Environment Variables

Production `.env`:
```bash
STORAGE_BACKEND=r2
R2_ACCOUNT_ID=your_account_id
R2_ACCESS_KEY_ID=your_access_key
R2_SECRET_ACCESS_KEY=your_secret_key
R2_BUCKET_NAME=openharbor-files
R2_REGION=auto
```
```

#### Step 7.2: Monitoring and Logging
**File:** `app/services/monitoring_service.py` (NEW FILE)

Add monitoring for R2 operations:

```python
"""Monitoring service for R2 storage operations."""

import time
import logging
from functools import wraps
from flask import current_app

logger = logging.getLogger(__name__)

def monitor_r2_operation(operation_name):
    """Decorator to monitor R2 storage operations."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()

            try:
                result = func(*args, **kwargs)

                duration = time.time() - start_time
                logger.info(
                    f"R2 {operation_name} completed successfully in {duration:.2f}s"
                )

                # Log metrics for monitoring dashboard
                if hasattr(current_app, 'metrics'):
                    current_app.metrics.timing(f'r2.{operation_name}.duration', duration)
                    current_app.metrics.incr(f'r2.{operation_name}.success')

                return result

            except Exception as e:
                duration = time.time() - start_time
                logger.error(
                    f"R2 {operation_name} failed after {duration:.2f}s: {str(e)}"
                )

                if hasattr(current_app, 'metrics'):
                    current_app.metrics.incr(f'r2.{operation_name}.error')

                raise

        return wrapper
    return decorator

class R2HealthCheck:
    """Health check service for R2 connectivity."""

    @staticmethod
    def check_r2_connection():
        """Check R2 connection and return health status."""
        try:
            if hasattr(current_app, 'r2_storage'):
                bucket_info = current_app.r2_storage.get_bucket_info()
                return {
                    'status': 'healthy',
                    'bucket': bucket_info['bucket_name'],
                    'accessible': bucket_info['accessible']
                }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e)
            }
```

## Common Pitfalls and Warnings

### Critical Warnings by Implementation Phase

#### Phase 1: Backend Setup
- **⚠️ Environment Variables**: Never commit R2 credentials to version control
- **⚠️ Initialization**: Handle R2 initialization failures gracefully to prevent app crashes
- **⚠️ Configuration**: Validate all required R2 configuration before startup

#### Phase 2: Storage Service
- **⚠️ File Validation**: Always validate files before uploading to prevent corrupted uploads
- **⚠️ Database Consistency**: Wrap file uploads and database operations in transactions
- **⚠️ Progress Tracking**: XMLHttpRequest progress only tracks network upload, not server processing

#### Phase 3: Frontend Updates
- **⚠️ Concurrent Uploads**: Limit concurrent uploads to prevent overwhelming the server
- **⚠️ Error Handling**: Implement retry logic for transient network errors
- **⚠️ Memory Usage**: Process large file sets in batches to prevent browser crashes

#### Phase 4: File Serving
- **⚠️ Access Control**: Always verify permissions before generating presigned URLs
- **⚠️ URL Expiration**: Use appropriate expiration times for different use cases
- **⚠️ Thumbnail Generation**: Handle thumbnail failures gracefully, don't break file serving

#### Phase 5: Database Updates
- **⚠️ Migration**: Test migrations on production-like data volumes
- **⚠️ Backward Compatibility**: Support both local and R2 files during transition
- **⚠️ Index Performance**: Add database indexes for R2-specific queries

## Performance Optimization Guidelines

### Upload Performance
- Use multipart uploads for files > 100MB
- Implement concurrent uploads with appropriate limits (3-5 simultaneous)
- Add progress callbacks for better user experience
- Use batch operations where possible

### File Serving Performance
- Use presigned URLs to reduce server load
- Implement proper caching headers for thumbnails
- Consider CDN integration for frequently accessed files
- Generate thumbnails asynchronously when possible

### Database Performance
- Index R2-specific fields (`r2_key`, `thumbnail_generated`)
- Use database connection pooling for high-concurrency scenarios
- Consider read replicas for file serving operations
- Archive old file records to maintain performance

## Security Considerations

### Access Control
- Implement proper authentication before file operations
- Use time-limited presigned URLs (1-24 hours max)
- Validate file types and sizes on both client and server
- Implement rate limiting for upload endpoints

### Data Protection
- Enable versioning on R2 buckets for data protection
- Use HTTPS for all file operations
- Implement CORS policies restrictively
- Log all file operations for audit trails

### Error Information
- Don't expose internal R2 errors to end users
- Log detailed errors server-side for debugging
- Use generic error messages for client responses
- Implement proper error tracking and alerting

## Testing Checklist

### Integration Tests Required
- [ ] R2 connection and authentication
- [ ] File upload with various sizes and types
- [ ] Progress tracking and error handling
- [ ] Presigned URL generation and access
- [ ] Thumbnail generation and serving
- [ ] Database consistency during failures
- [ ] Migration from local to R2 storage

### Performance Tests Required
- [ ] Concurrent upload stress testing
- [ ] Large file upload (multi-GB files)
- [ ] High-volume thumbnail generation
- [ ] Database performance with large file counts
- [ ] Memory usage during batch operations

### Security Tests Required
- [ ] Access control for protected collections
- [ ] File type validation bypass attempts
- [ ] Rate limiting effectiveness
- [ ] Presigned URL security
- [ ] Error message information disclosure

## Rollback Plan

In case of issues during deployment:

1. **Immediate Rollback**: Set `STORAGE_BACKEND=local` in environment
2. **Database Rollback**: Apply down migration to remove R2 fields
3. **File Cleanup**: Script to move files from R2 back to local storage
4. **Frontend Rollback**: Revert JavaScript changes to remove R2-specific features

## Success Metrics

### Technical Metrics
- File upload success rate > 99%
- Average upload time < 30s per 10MB file
- Thumbnail generation success rate > 95%
- Presigned URL generation time < 500ms
- Zero data loss during transition

### User Experience Metrics
- Upload error rate < 1%
- Progress tracking accuracy > 98%
- File access time < 2s for normal files
- Thumbnail load time < 1s
- User satisfaction with upload experience

## Post-Implementation Tasks

1. **Monitoring Setup**: Configure dashboards for R2 operations
2. **Backup Strategy**: Implement automated R2 bucket backups
3. **Cost Monitoring**: Track R2 usage and costs
4. **Documentation**: Update user guides and admin documentation
5. **Training**: Train support team on R2-specific troubleshooting

## Conclusion

This implementation plan provides a comprehensive roadmap for integrating CloudflareR2 storage with The Open Harbor collection upload system. Following these steps carefully, with attention to the warnings and best practices, will result in a robust, scalable file storage solution.

The integration maintains backward compatibility while providing enhanced performance, reliability, and scalability for growing file storage needs.