# CloudflareR2Storage API Documentation

## Overview
The `CloudflareR2Storage` class provides a comprehensive interface for uploading, managing, and retrieving files from Cloudflare R2 storage. It handles both single and multipart uploads, with automatic optimization for large files and batch operations.

## Configuration Requirements
Before using this class, ensure the following environment variables are set:
```bash
R2_ACCOUNT_ID=your_cloudflare_account_id
R2_ACCESS_KEY_ID=your_r2_access_key
R2_SECRET_ACCESS_KEY=your_r2_secret_key
R2_BUCKET_NAME=your_bucket_name
R2_REGION=auto  # Optional, defaults to 'auto'
```

## Class Initialization
```python
from app.integrations.file_storage import CloudflareR2Storage

# Initialize storage client
storage = CloudflareR2Storage()
```

The constructor automatically validates configuration and establishes connection to R2.

## Core Upload Methods

### upload_single_file()
**Purpose**: Upload a single file with automatic multipart handling for large files.

**Signature**:
```python
upload_single_file(
    file_obj: BinaryIO,
    filename: str = None,
    key: str = None,
    metadata: Dict[str, str] = None,
    progress_callback: Callable[[int, int], None] = None
) -> Dict[str, any]
```

**Parameters**:
- `file_obj`: Open file object or BytesIO buffer
- `filename`: Original filename (used for key generation if key not provided)
- `key`: Custom storage key/path (optional, auto-generated if not provided)
- `metadata`: Custom metadata dictionary to store with file
- `progress_callback`: Function called with (bytes_uploaded, total_bytes) for progress tracking

**Returns**:
```python
{
    'key': 'uploads/2024/09/25/photo.jpg',
    'bucket': 'my-bucket',
    'size': 2048576,
    'upload_method': 'single_part' | 'multipart',
    'parts_count': 5,  # Only for multipart uploads
    'part_size': 10485760  # Only for multipart uploads
}
```

**Example**:
```python
with open('photo.jpg', 'rb') as f:
    result = storage.upload_single_file(
        file_obj=f,
        filename='photo.jpg',
        metadata={'photographer': 'John Doe', 'camera': 'Canon EOS R5'}
    )
    print(f"Uploaded to: {result['key']}")
```

### upload_multiple_files()
**Purpose**: Upload multiple files concurrently with progress tracking.

**Signature**:
```python
upload_multiple_files(
    files_data: List[Dict[str, any]],
    max_workers: int = 5,
    progress_callback: Callable[[int, int], None] = None
) -> List[Dict[str, any]]
```

**Parameters**:
- `files_data`: List of file dictionaries, each containing:
  - `file_obj`: File object to upload
  - `filename`: Filename (optional if key provided)
  - `key`: Storage key (optional, auto-generated from filename)
  - `metadata`: File metadata dictionary (optional)
- `max_workers`: Number of concurrent upload threads (default: 5)
- `progress_callback`: Function called with (completed_files, total_files)

**Returns**:
```python
[
    {
        'success': True,
        'result': {...},  # Same as upload_single_file result
        'file_data': {...}  # Original file data
    },
    {
        'success': False,
        'error': 'Validation error message',
        'file_data': {...}
    }
]
```

**Example**:
```python
files_to_upload = [
    {'file_obj': open('photo1.jpg', 'rb'), 'filename': 'photo1.jpg'},
    {'file_obj': open('photo2.jpg', 'rb'), 'filename': 'photo2.jpg'},
    {'file_obj': open('photo3.jpg', 'rb'), 'key': 'custom/path/photo3.jpg'}
]

def progress_handler(completed, total):
    print(f"Progress: {completed}/{total} files uploaded")

results = storage.upload_multiple_files(files_to_upload, progress_callback=progress_handler)
```

### upload_with_integrity_check()
**Purpose**: Upload file with automatic integrity verification using hash comparison.

**Signature**:
```python
upload_with_integrity_check(
    file_obj: BinaryIO,
    filename: str = None,
    key: str = None,
    check_algorithm: str = 'md5'
) -> Dict[str, any]
```

**Parameters**:
- `file_obj`: File object to upload
- `filename`: Original filename
- `key`: Storage key (optional)
- `check_algorithm`: Hash algorithm ('md5', 'sha1', 'sha256')

**Returns**: Same as `upload_single_file()` plus:
```python
{
    # ... standard upload result fields
    'integrity_verified': True,
    'hash': 'calculated_hash_value'
}
```

## File Management Methods

### get_file_info()
**Purpose**: Retrieve metadata and information about a stored file.

**Signature**:
```python
get_file_info(key: str) -> Dict[str, any] | None
```

**Returns**:
```python
{
    'key': 'uploads/2024/09/25/photo.jpg',
    'bucket': 'my-bucket',
    'size': 2048576,
    'content_type': 'image/jpeg',
    'last_modified': datetime_object,
    'etag': 'file_etag_hash',
    'metadata': {'photographer': 'John Doe'}
}
```

**Returns `None`** if file does not exist.

### delete_file()
**Purpose**: Delete a single file from storage.

**Signature**:
```python
delete_file(key: str) -> bool
```

**Returns**: `True` if deleted successfully, `False` if file didn't exist.

### delete_multiple_files()
**Purpose**: Delete multiple files in a single batch operation.

**Signature**:
```python
delete_multiple_files(keys: List[str]) -> Dict[str, any]
```

**Returns**:
```python
{
    'deleted': ['file1.jpg', 'file2.jpg'],  # Successfully deleted files
    'errors': [
        {'key': 'file3.jpg', 'message': 'Access denied'}
    ]
}
```

### list_files()
**Purpose**: List files in the bucket with optional prefix filtering.

**Signature**:
```python
list_files(prefix: str = "", max_keys: int = 1000) -> List[Dict[str, any]]
```

**Returns**:
```python
[
    {
        'key': 'uploads/2024/09/25/photo1.jpg',
        'size': 2048576,
        'last_modified': datetime_object,
        'etag': 'file_etag'
    },
    # ... more files
]
```

### copy_file()
**Purpose**: Copy a file within the bucket to a new location.

**Signature**:
```python
copy_file(
    source_key: str,
    destination_key: str,
    metadata: Dict[str, str] = None
) -> bool
```

**Parameters**:
- `source_key`: Original file location
- `destination_key`: New file location
- `metadata`: New metadata (optional, replaces existing if provided)

## URL Generation Methods

### generate_presigned_url()
**Purpose**: Create a temporary signed URL for direct file access.

**Signature**:
```python
generate_presigned_url(
    key: str,
    expiry_seconds: int = 3600,
    http_method: str = 'get_object'
) -> str
```

**Parameters**:
- `key`: File key to generate URL for
- `expiry_seconds`: URL validity period (max 604800 = 7 days)
- `http_method`: HTTP method ('get_object', 'put_object')

**Returns**: Presigned URL string

**Example**:
```python
# Generate URL valid for 1 hour
url = storage.generate_presigned_url('uploads/photo.jpg', expiry_seconds=3600)
```

## Utility Methods

### validate_file()
**Purpose**: Validate file before upload (file type, size, etc.).

**Signature**:
```python
validate_file(file_obj: BinaryIO, filename: str) -> Dict[str, any]
```

**Returns**:
```python
{
    'filename': 'photo.jpg',
    'file_extension': '.jpg',
    'file_size': 2048576,
    'mime_type': 'image/jpeg'
}
```

**Raises**: `ValidationError` for invalid files.

### calculate_file_hash()
**Purpose**: Calculate hash of file contents.

**Signature**:
```python
calculate_file_hash(file_obj: BinaryIO, algorithm: str = 'md5') -> str
```

### get_bucket_info()
**Purpose**: Get information about the connected R2 bucket.

**Signature**:
```python
get_bucket_info() -> Dict[str, any]
```

**Returns**:
```python
{
    'bucket_name': 'my-bucket',
    'region': 'auto',
    'accessible': True,
    'sample_file_count': 1
}
```

## File Type and Size Constraints

### Supported File Types
- **Extensions**: .jpg, .jpeg, .png, .webp, .tiff, .bmp, .gif
- **MIME Types**: image/jpeg, image/png, image/webp, image/tiff, image/bmp, image/gif

### Size Limits
- **Maximum file size**: 5GB (R2 limit)
- **Multipart threshold**: 100MB (files ≥100MB use multipart upload)
- **Part size range**: 5MB - 5GB per part
- **Maximum parts**: 10,000 per multipart upload

### Batch Limits
- **Multiple file upload**: 100 files per batch maximum
- **Multiple file deletion**: 1,000 files per batch maximum
- **List files**: 1,000 files per request maximum

## Error Handling

### Custom Exceptions
- `FileStorageError`: Base exception for all storage errors
- `ValidationError`: File validation errors (extends FileStorageError)
- `UploadError`: Upload operation errors (extends FileStorageError)

### Common Error Scenarios
1. **Configuration Errors**: Missing environment variables
2. **Access Errors**: Invalid credentials or insufficient permissions
3. **Validation Errors**: Unsupported file types or sizes
4. **Network Errors**: Connection timeouts or interruptions
5. **R2 Service Errors**: Rate limits or service unavailability

## Progress Tracking

### Progress Callback Pattern
```python
def progress_handler(current, total):
    percentage = (current / total) * 100
    print(f"Progress: {percentage:.1f}% ({current}/{total})")

# Single file upload progress (bytes)
storage.upload_single_file(file_obj, progress_callback=progress_handler)

# Multiple file upload progress (files completed)
storage.upload_multiple_files(files_data, progress_callback=progress_handler)
```

## Usage Patterns

### Basic File Upload
```python
# Simple upload
with open('photo.jpg', 'rb') as f:
    result = storage.upload_single_file(f, filename='photo.jpg')
    print(f"File uploaded: {result['key']}")
```

### Large File Upload with Progress
```python
def show_progress(uploaded, total):
    percent = (uploaded / total) * 100
    print(f"\rUploading: {percent:.1f}%", end='', flush=True)

with open('large_video.mp4', 'rb') as f:
    result = storage.upload_single_file(
        f,
        filename='large_video.mp4',
        progress_callback=show_progress
    )
```

### Batch Upload with Error Handling
```python
results = storage.upload_multiple_files(files_data)

successful = [r for r in results if r['success']]
failed = [r for r in results if not r['success']]

print(f"Uploaded: {len(successful)}, Failed: {len(failed)}")

for failure in failed:
    print(f"Failed: {failure['file_data']['filename']} - {failure['error']}")
```

### File Management
```python
# Check if file exists
info = storage.get_file_info('uploads/photo.jpg')
if info:
    print(f"File size: {info['size']} bytes")
else:
    print("File not found")

# List recent uploads
recent_files = storage.list_files(prefix='uploads/2024/09/')

# Generate shareable URL
share_url = storage.generate_presigned_url(
    'uploads/photo.jpg',
    expiry_seconds=86400  # 24 hours
)
```

## Integration with Flask Application

### Application Factory Pattern
```python
# In app/__init__.py
from app.integrations.file_storage import CloudflareR2Storage

def create_app():
    app = Flask(__name__)

    try:
        app.r2_storage = CloudflareR2Storage()
        app.logger.info("R2 storage initialized")
    except FileStorageError as e:
        app.logger.error(f"R2 initialization failed: {e}")
        # Handle gracefully or fail fast

    return app
```

### Route Usage
```python
from flask import current_app, request, jsonify

@app.route('/upload', methods=['POST'])
def upload_file():
    try:
        file = request.files['file']
        result = current_app.r2_storage.upload_single_file(
            file_obj=file,
            filename=file.filename
        )
        return jsonify({'success': True, 'url': result['key']})

    except ValidationError as e:
        return jsonify({'error': str(e)}), 400
    except UploadError as e:
        return jsonify({'error': str(e)}), 500
```

## Performance Considerations

1. **Multipart uploads** are automatically used for files ≥100MB
2. **Concurrent uploads** use ThreadPoolExecutor with configurable worker count
3. **Connection pooling** is enabled with 50 max connections
4. **Retry logic** with exponential backoff for transient failures
5. **Part size optimization** based on file size for optimal performance

## Security Notes

1. **Environment variables** should be properly secured in production
2. **API tokens** should have minimal required permissions
3. **File validation** is performed before upload to prevent malicious files
4. **Presigned URLs** have configurable expiry times (max 7 days)
5. **Integrity checking** available for critical uploads
