# Technical Requirements: Cloudflare R2 File Storage Integration

## Overview & Context

This document outlines the technical requirements for implementing Cloudflare R2 storage integration with The Open Harbor - a photographer-focused file sharing platform. The integration provides robust file upload capabilities with multipart upload support for large files and batch processing for collections.

**Target Users**: Professional photographers, creatives, small studios
**Storage Backend**: Cloudflare R2 with S3-compatible API
**Use Cases**: Single/batch photo uploads, large file handling (>5GB), gallery creation
**Skill Level**: Document written for junior developer implementation

---

## File Structure & Organization

### Required Directory Structure
```
app/
├── integrations/
│   ├── __init__.py
│   ├── file_storage.py         # Main R2 integration class
│   └── file_storage.md         # API documentation
├── config.py                   # Updated with R2 config
└── __init__.py                 # Updated with R2 initialization
```

### Environment Configuration
Add to `.env` file:
```bash
# Cloudflare R2 Configuration
R2_ACCOUNT_ID=your_cloudflare_account_id
R2_ACCESS_KEY_ID=your_r2_access_key
R2_SECRET_ACCESS_KEY=your_r2_secret_key
R2_BUCKET_NAME=your_bucket_name
R2_REGION=auto
R2_ENDPOINT_URL_TEMPLATE=https://{}.r2.cloudflarestorage.com
```

---

## Core Technical Requirements

### 1. Dependencies
Add to `requirements.txt`:
```txt
boto3>=1.40.0
botocore>=1.31.0
python-dotenv>=1.0.0
```

### 2. Configuration Validation
**Location**: `app/config.py`
```python
# Required R2 environment variables
R2_REQUIRED_VARS = [
    'R2_ACCOUNT_ID',
    'R2_ACCESS_KEY_ID',
    'R2_SECRET_ACCESS_KEY',
    'R2_BUCKET_NAME'
]

# Validate on app startup
def validate_r2_config():
    missing = [var for var in R2_REQUIRED_VARS if not os.getenv(var)]
    if missing:
        raise EnvironmentError(f"Missing R2 config: {', '.join(missing)}")
```

### 3. Core Storage Class Architecture

**Location**: `app/integrations/file_storage.py`

#### Class Structure:
```python
class CloudflareR2Storage:
    def __init__(self):
        # Initialize boto3 client with R2 config

    # Core Upload Methods
    def upload_single_file(self, file_obj, key, metadata=None) -> dict
    def upload_large_file(self, file_obj, key, part_size_mb=10) -> dict
    def upload_multiple_files(self, files_data, progress_callback=None) -> list

    # File Management
    def get_file_info(self, key) -> dict
    def delete_file(self, key) -> bool
    def list_files(self, prefix="", max_keys=1000) -> list
    def generate_presigned_url(self, key, expiry=3600) -> str

    # Utility Methods
    def validate_file_type(self, filename, allowed_types) -> bool
    def calculate_optimal_part_size(self, file_size) -> int
    def get_upload_progress(self, upload_id) -> dict
```

---

## Implementation Details

### 1. Client Configuration (Critical Setup)

**Common Mistake Prevention**:
- ❌ **Wrong**: Using AWS endpoints or credentials
- ❌ **Wrong**: Missing account ID in endpoint URL
- ❌ **Wrong**: Using 'us-east-1' region with wrong endpoint
- ✅ **Correct**: Use R2-specific endpoint with account ID

```python
def _create_client(self):
    """Create properly configured R2 client"""
    return boto3.client(
        's3',
        endpoint_url=f'https://{self.account_id}.r2.cloudflarestorage.com',
        aws_access_key_id=self.access_key_id,
        aws_secret_access_key=self.secret_access_key,
        config=Config(
            signature_version='s3v4',
            s3={'addressing_style': 'path'}  # Important for R2
        ),
        region_name='auto'  # R2 uses 'auto' region
    )
```

### 2. Multipart Upload Implementation

**File Size Thresholds**:
- Files < 100MB: Standard upload
- Files ≥ 100MB: Multipart upload (mandatory)
- Part size: 5MB - 5GB per part
- Max parts: 10,000 per upload

**Critical Requirements**:
- All parts except last must be same size
- Minimum part size: 5MB
- Incomplete uploads auto-abort after 7 days

```python
def _should_use_multipart(self, file_size_bytes):
    """Determine if multipart upload is needed"""
    return file_size_bytes >= 100 * 1024 * 1024  # 100MB threshold

def _calculate_part_size(self, file_size_bytes):
    """Calculate optimal part size for multipart upload"""
    # Ensure part size is between 5MB and 5GB
    min_part_size = 5 * 1024 * 1024   # 5MB
    max_part_size = 5 * 1024 * 1024 * 1024  # 5GB

    # Calculate parts needed
    target_parts = min(file_size_bytes // min_part_size, 10000)
    part_size = max(min_part_size, file_size_bytes // target_parts)

    return min(part_size, max_part_size)
```

### 3. Error Handling Patterns

**Common R2 Errors & Solutions**:

1. **AccessDenied**
   - Cause: Insufficient API token permissions
   - Solution: Verify token has Object:Write permissions

2. **SignatureDoesNotMatch**
   - Cause: Incorrect endpoint URL or credentials
   - Solution: Double-check account ID in endpoint

3. **InvalidRequest** (Multipart)
   - Cause: Incorrect part size or ordering
   - Solution: Validate part sizes and upload order

```python
def _handle_r2_errors(self, error):
    """Centralized R2 error handling"""
    error_code = error.response['Error']['Code']

    error_mappings = {
        'AccessDenied': 'Insufficient permissions for R2 operation',
        'SignatureDoesNotMatch': 'Invalid R2 credentials or endpoint',
        'InvalidRequest': 'Invalid multipart upload parameters',
        'NoSuchBucket': 'R2 bucket does not exist'
    }

    user_message = error_mappings.get(error_code, f'R2 error: {error_code}')
    raise FileStorageError(user_message) from error
```

---

## Security & Best Practices

### 1. API Token Management
- Use R2-specific API tokens (not Cloudflare Global API keys)
- Grant minimum required permissions: `Object:Write`, `Object:Read`
- Store tokens in environment variables only
- Never commit tokens to repository

### 2. File Validation
```python
ALLOWED_IMAGE_TYPES = {'.jpg', '.jpeg', '.png', '.webp', '.tiff', '.bmp'}
MAX_FILE_SIZE = 5 * 1024 * 1024 * 1024  # 5GB per R2 limits

def validate_upload_file(self, file_obj, filename):
    """Comprehensive file validation"""
    # File type validation
    file_ext = Path(filename).suffix.lower()
    if file_ext not in ALLOWED_IMAGE_TYPES:
        raise ValidationError(f"Unsupported file type: {file_ext}")

    # File size validation
    file_obj.seek(0, 2)  # Seek to end
    file_size = file_obj.tell()
    file_obj.seek(0)     # Reset to beginning

    if file_size > MAX_FILE_SIZE:
        raise ValidationError(f"File too large: {file_size} bytes")

    return True
```

### 3. Progress Tracking for Large Uploads
```python
def upload_with_progress(self, file_obj, key, progress_callback=None):
    """Upload with progress tracking for UX"""
    file_size = self._get_file_size(file_obj)

    if self._should_use_multipart(file_size):
        return self._multipart_upload_with_progress(
            file_obj, key, progress_callback
        )
    else:
        return self._single_upload_with_progress(
            file_obj, key, progress_callback
        )
```

---

## Integration Points

### 1. Flask Application Integration
**Location**: `app/__init__.py`
```python
from app.integrations.file_storage import CloudflareR2Storage

def create_app(config_name='default'):
    app = Flask(__name__)

    # Initialize R2 storage
    try:
        app.r2_storage = CloudflareR2Storage()
        app.logger.info("R2 storage initialized successfully")
    except Exception as e:
        app.logger.error(f"Failed to initialize R2: {e}")
        # Decide: fail fast or use fallback storage

    return app
```

### 2. Route Integration Example
**Location**: `app/views/collections/routes.py`
```python
from flask import current_app

@collections_bp.route('/upload', methods=['POST'])
def upload_collection():
    try:
        files = request.files.getlist('files')
        results = current_app.r2_storage.upload_multiple_files(files)
        return jsonify({'success': True, 'uploads': results})
    except FileStorageError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
```

---

## Testing Strategy

### 1. Unit Tests
**Location**: `tests/test_file_storage.py`
```python
@pytest.fixture
def mock_r2_storage():
    """Mock R2 storage for testing"""
    with patch('boto3.client') as mock_client:
        yield CloudflareR2Storage()

def test_single_file_upload(mock_r2_storage):
    """Test single file upload flow"""
    # Test implementation

def test_multipart_upload_threshold(mock_r2_storage):
    """Test multipart upload decision logic"""
    # Test implementation
```

### 2. Integration Tests
- Test with actual R2 bucket (separate test bucket)
- Test multipart uploads with large files
- Test error scenarios (invalid credentials, network issues)

---

## Common Junior Developer Mistakes

### 1. Configuration Mistakes
❌ **Mistake**: Hard-coding credentials in code
```python
# DON'T DO THIS
s3_client = boto3.client('s3', aws_access_key_id='AKIAI...')
```

✅ **Correct**: Use environment variables
```python
# DO THIS
s3_client = boto3.client('s3',
    aws_access_key_id=os.getenv('R2_ACCESS_KEY_ID'))
```

### 2. Endpoint URL Mistakes
❌ **Mistake**: Using AWS endpoints
```python
# DON'T DO THIS
endpoint_url = 'https://s3.amazonaws.com'
```

✅ **Correct**: Use R2 endpoint with account ID
```python
# DO THIS
endpoint_url = f'https://{account_id}.r2.cloudflarestorage.com'
```

### 3. Region Configuration Mistakes
❌ **Mistake**: Using wrong region
```python
# DON'T DO THIS
region_name = 'us-west-2'  # AWS region
```

✅ **Correct**: Use R2 regions
```python
# DO THIS
region_name = 'auto'  # or 'wnam', 'enam', 'weur', 'eeur', 'apac'
```

### 4. Error Handling Mistakes
❌ **Mistake**: Generic exception handling
```python
# DON'T DO THIS
try:
    upload_file()
except Exception:
    return "Upload failed"
```

✅ **Correct**: Specific R2 error handling
```python
# DO THIS
try:
    upload_file()
except ClientError as e:
    error_code = e.response['Error']['Code']
    if error_code == 'AccessDenied':
        return "Check R2 permissions"
    # Handle specific errors
```

### 5. Multipart Upload Mistakes
❌ **Mistake**: Wrong part size calculations
```python
# DON'T DO THIS - parts too small
part_size = 1024 * 1024  # 1MB - below 5MB minimum
```

✅ **Correct**: Respect R2 part size limits
```python
# DO THIS
min_part_size = 5 * 1024 * 1024  # 5MB minimum
part_size = max(min_part_size, calculated_size)
```

---

## Performance Optimization

### 1. Connection Pooling
```python
from botocore.config import Config

config = Config(
    retries={'max_attempts': 3},
    max_pool_connections=50  # For concurrent uploads
)
```

### 2. Parallel Multipart Upload
- Upload parts concurrently (max 10 concurrent parts)
- Use ThreadPoolExecutor for parallel processing
- Implement proper backoff for rate limits

### 3. Caching Strategies
- Cache presigned URLs (respect expiry times)
- Cache file metadata for recently accessed files
- Use ETags for client-side caching

---

## Monitoring & Observability

### 1. Logging Requirements
```python
import logging

logger = logging.getLogger('r2_storage')

def upload_file(self, file_obj, key):
    logger.info(f"Starting upload: {key}")
    try:
        result = self._do_upload(file_obj, key)
        logger.info(f"Upload successful: {key}")
        return result
    except Exception as e:
        logger.error(f"Upload failed: {key}, error: {e}")
        raise
```

### 2. Metrics to Track
- Upload success/failure rates
- Upload duration by file size
- Multipart vs single part upload ratios
- Error types and frequencies

---

## Deployment Checklist

### Pre-deployment
- [ ] R2 bucket created and configured
- [ ] API tokens generated with correct permissions
- [ ] Environment variables set in production
- [ ] Dependencies installed
- [ ] Tests passing

### Post-deployment
- [ ] Test file upload functionality
- [ ] Verify multipart uploads work for large files
- [ ] Check error handling with invalid files
- [ ] Monitor logs for R2 connection issues
- [ ] Verify presigned URL generation

### Rollback Plan
- [ ] Keep fallback to local storage if R2 fails
- [ ] Monitor error rates and revert if >5% upload failures
- [ ] Have backup of any configuration changes

---

## File Modifications Required

### 1. New Files to Create
- `app/integrations/__init__.py` - Empty init file
- `app/integrations/file_storage.py` - Main implementation
- `app/integrations/file_storage.md` - API documentation
- `tests/test_file_storage.py` - Unit tests

### 2. Files to Modify
- `requirements.txt` - Add boto3 dependencies
- `.env` - Add R2 configuration variables
- `app/config.py` - Add R2 config validation
- `app/__init__.py` - Initialize R2 storage
- Collection routes - Integrate R2 uploads

### 3. Optional Enhancements
- `app/utils/file_helpers.py` - File validation utilities
- `app/exceptions.py` - Custom R2 exceptions
- `config/logging.py` - R2-specific logging config

This comprehensive implementation guide ensures robust, secure, and performant Cloudflare R2 integration with proper error handling and junior developer guidance.