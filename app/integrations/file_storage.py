import os
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError, NoCredentialsError
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List, Optional, Callable, Union, BinaryIO
import mimetypes
import hashlib
import logging
from datetime import datetime, timedelta

required_envs = [
    'TOH_R2_ACCOUNT_ID',
    'TOH_R2_ACCESS_KEY',
    'TOH_R2_SECRET_KEY',
    'TOH_R2_BUCKET_NAME',
    'TOH_R2_REGION'
]

# Configuration Constants
R2_ACCOUNT_ID = os.getenv('TOH_R2_ACCOUNT_ID')
R2_ACCESS_KEY_ID = os.getenv('TOH_R2_ACCESS_KEY')
R2_SECRET_ACCESS_KEY = os.getenv('TOH_R2_SECRET_KEY')
R2_BUCKET_NAME = os.getenv('TOH_R2_BUCKET_NAME')
R2_REGION = os.getenv('TOH_R2_REGION', 'auto')

# File handling constants
MULTIPART_THRESHOLD = 100 * 1024 * 1024  # 100MB
MIN_PART_SIZE = 5 * 1024 * 1024  # 5MB - R2 minimum
MAX_PART_SIZE = 5 * 1024 * 1024 * 1024  # 5GB - R2 maximum
MAX_PARTS = 10000  # R2 maximum parts per upload
MAX_FILE_SIZE = 5 * 1024 * 1024 * 1024  # 5GB - R2 maximum object size

ALLOWED_IMAGE_TYPES = {'.jpg', '.jpeg', '.png', '.webp', '.tiff', '.bmp', '.gif'}
ALLOWED_MIME_TYPES = {
    'image/jpeg', 'image/png', 'image/webp', 'image/tiff',
    'image/bmp', 'image/gif'
}

logger = logging.getLogger(__name__)


class FileStorageError(Exception):
    pass


class ValidationError(FileStorageError):
    pass


class UploadError(FileStorageError):
    pass


class CloudflareR2Storage:
    def __init__(self):
        self.account_id = R2_ACCOUNT_ID
        self.access_key_id = R2_ACCESS_KEY_ID
        self.secret_access_key = R2_SECRET_ACCESS_KEY
        self.bucket_name = R2_BUCKET_NAME
        self.region = R2_REGION

        self._validate_config()
        self.client = self._create_client()
        self._verify_connection()

    def _validate_config(self) -> None:
        required_vars = {
            'TOH_R2_ACCOUNT_ID': self.account_id,
            'TOH_R2_ACCESS_KEY': self.access_key_id,
            'TOH_R2_SECRET_KEY': self.secret_access_key,
            'TOH_R2_BUCKET_NAME': self.bucket_name
        }

        missing = [var for var, value in required_vars.items() if not value]
        if missing:
            raise FileStorageError(f"Missing required R2 configuration: {', '.join(missing)}")

    def _create_client(self):
        try:
            return boto3.client(
                's3',
                endpoint_url=f'https://{self.account_id}.r2.cloudflarestorage.com',
                aws_access_key_id=self.access_key_id,
                aws_secret_access_key=self.secret_access_key,
                config=Config(
                    signature_version='s3v4',
                    s3={'addressing_style': 'path'},
                    retries={'max_attempts': 3},
                    max_pool_connections=50
                ),
                region_name=self.region
            )
        except NoCredentialsError:
            raise FileStorageError("Invalid R2 credentials provided")

    def _verify_connection(self) -> None:
        try:
            self.client.head_bucket(Bucket=self.bucket_name)
            logger.info(f"Successfully connected to R2 bucket: {self.bucket_name}")
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'NoSuchBucket':
                raise FileStorageError(f"R2 bucket '{self.bucket_name}' does not exist")
            elif error_code == 'AccessDenied':
                raise FileStorageError("Access denied to R2 bucket. Check API token permissions")
            else:
                raise FileStorageError(f"Failed to connect to R2: {error_code}")

    def _handle_r2_errors(self, error: ClientError) -> None:
        error_code = error.response['Error']['Code']

        error_mappings = {
            'AccessDenied': 'Insufficient permissions for R2 operation',
            'SignatureDoesNotMatch': 'Invalid R2 credentials or endpoint configuration',
            'InvalidRequest': 'Invalid request parameters for R2',
            'NoSuchBucket': f'R2 bucket "{self.bucket_name}" does not exist',
            'NoSuchKey': 'Requested file does not exist in R2',
            'EntityTooLarge': 'File size exceeds R2 limits (5GB maximum)',
            'InvalidPart': 'Invalid multipart upload part',
            'InvalidPartOrder': 'Multipart upload parts not in correct order'
        }

        user_message = error_mappings.get(error_code, f'R2 error: {error_code}')
        logger.error(f"R2 Error: {error_code} - {error.response['Error'].get('Message', '')}")
        raise UploadError(user_message) from error

    def validate_file(self, file_obj: BinaryIO, filename: str) -> Dict[str, any]:
        file_ext = Path(filename).suffix.lower()
        if file_ext not in ALLOWED_IMAGE_TYPES:
            raise ValidationError(f"Unsupported file type: {file_ext}. Allowed: {', '.join(ALLOWED_IMAGE_TYPES)}")

        file_obj.seek(0, 2)
        file_size = file_obj.tell()
        file_obj.seek(0)

        if file_size == 0:
            raise ValidationError("Cannot upload empty file")

        if file_size > MAX_FILE_SIZE:
            raise ValidationError(f"File too large: {file_size} bytes. Maximum: {MAX_FILE_SIZE} bytes")

        mime_type, _ = mimetypes.guess_type(filename)
        if mime_type and mime_type not in ALLOWED_MIME_TYPES:
            raise ValidationError(f"Invalid MIME type: {mime_type}")

        return {
            'filename': filename,
            'file_extension': file_ext,
            'file_size': file_size,
            'mime_type': mime_type or 'application/octet-stream'
        }

    def _generate_file_key(self, filename: str, prefix: str = None) -> str:
        timestamp = datetime.now().strftime('%Y/%m/%d')
        safe_filename = "".join(c for c in filename if c.isalnum() or c in '.-_').strip()

        if prefix:
            return f"{prefix}/{timestamp}/{safe_filename}"
        return f"uploads/{timestamp}/{safe_filename}"

    def _should_use_multipart(self, file_size: int) -> bool:
        return file_size >= MULTIPART_THRESHOLD

    def _calculate_part_size(self, file_size: int) -> int:
        if file_size <= MIN_PART_SIZE:
            return MIN_PART_SIZE

        target_parts = min(file_size // MIN_PART_SIZE, MAX_PARTS)
        part_size = max(MIN_PART_SIZE, file_size // target_parts)

        part_size = (part_size // (1024 * 1024)) * (1024 * 1024)

        return min(part_size, MAX_PART_SIZE)

    def upload_single_file(
        self,
        file_obj: BinaryIO,
        filename: str = None,
        key: str = None,
        metadata: Dict[str, str] = None,
        progress_callback: Callable[[int, int], None] = None
    ) -> Dict[str, any]:
        if not filename and not key:
            raise ValidationError("Either filename or key must be provided")

        if not key:
            key = self._generate_file_key(filename)

        file_info = self.validate_file(file_obj, filename or key)

        extra_args = {
            'ContentType': file_info['mime_type']
        }

        if metadata:
            extra_args['Metadata'] = metadata

        try:
            logger.info(f"Starting upload: {key} ({file_info['file_size']} bytes)")

            if self._should_use_multipart(file_info['file_size']):
                result = self._multipart_upload(file_obj, key, extra_args, progress_callback)
            else:
                # Handle progress callback for single-part uploads
                callback_wrapper = None
                if progress_callback:
                    def callback_wrapper(bytes_transferred):
                        progress_callback(bytes_transferred, file_info['file_size'])

                self.client.upload_fileobj(
                    file_obj,
                    self.bucket_name,
                    key,
                    ExtraArgs=extra_args,
                    Callback=callback_wrapper
                )
                result = {
                    'key': key,
                    'bucket': self.bucket_name,
                    'size': file_info['file_size'],
                    'upload_method': 'single_part'
                }

            logger.info(f"Upload successful: {key}")
            return result

        except ClientError as e:
            self._handle_r2_errors(e)

    def _multipart_upload(
        self,
        file_obj: BinaryIO,
        key: str,
        extra_args: Dict[str, any],
        progress_callback: Callable[[int, int], None] = None
    ) -> Dict[str, any]:
        file_obj.seek(0, 2)
        file_size = file_obj.tell()
        file_obj.seek(0)

        part_size = self._calculate_part_size(file_size)
        parts_count = (file_size + part_size - 1) // part_size

        logger.info(f"Starting multipart upload: {key}, {parts_count} parts of {part_size} bytes each")

        try:
            response = self.client.create_multipart_upload(
                Bucket=self.bucket_name,
                Key=key,
                **extra_args
            )
            upload_id = response['UploadId']

            parts = []
            bytes_uploaded = 0

            for part_num in range(1, parts_count + 1):
                start_byte = (part_num - 1) * part_size

                if part_num == parts_count:
                    end_byte = file_size
                else:
                    end_byte = start_byte + part_size

                part_data = file_obj.read(end_byte - start_byte)

                part_response = self.client.upload_part(
                    Bucket=self.bucket_name,
                    Key=key,
                    PartNumber=part_num,
                    UploadId=upload_id,
                    Body=part_data
                )

                parts.append({
                    'ETag': part_response['ETag'],
                    'PartNumber': part_num
                })

                bytes_uploaded += len(part_data)

                if progress_callback:
                    progress_callback(bytes_uploaded, file_size)

                logger.debug(f"Uploaded part {part_num}/{parts_count}")

            self.client.complete_multipart_upload(
                Bucket=self.bucket_name,
                Key=key,
                UploadId=upload_id,
                MultipartUpload={'Parts': parts}
            )

            return {
                'key': key,
                'bucket': self.bucket_name,
                'size': file_size,
                'upload_method': 'multipart',
                'parts_count': parts_count,
                'part_size': part_size
            }

        except Exception as e:
            try:
                self.client.abort_multipart_upload(
                    Bucket=self.bucket_name,
                    Key=key,
                    UploadId=upload_id
                )
                logger.info(f"Aborted failed multipart upload: {upload_id}")
            except:
                pass

            if isinstance(e, ClientError):
                self._handle_r2_errors(e)
            else:
                raise UploadError(f"Multipart upload failed: {str(e)}") from e

    def upload_multiple_files(
        self,
        files_data: List[Dict[str, any]],
        max_workers: int = 5,
        progress_callback: Callable[[int, int], None] = None
    ) -> List[Dict[str, any]]:
        if not files_data:
            raise ValidationError("No files provided for upload")

        if len(files_data) > 100:
            raise ValidationError("Too many files. Maximum 100 files per batch")

        results = []
        total_files = len(files_data)
        completed_files = 0

        def upload_single(file_data):
            nonlocal completed_files
            try:
                file_obj = file_data['file_obj']
                filename = file_data.get('filename')
                key = file_data.get('key')
                metadata = file_data.get('metadata')

                result = self.upload_single_file(
                    file_obj=file_obj,
                    filename=filename,
                    key=key,
                    metadata=metadata
                )

                completed_files += 1
                if progress_callback:
                    progress_callback(completed_files, total_files)

                return {'success': True, 'result': result, 'file_data': file_data}

            except Exception as e:
                logger.error(f"Failed to upload file {file_data.get('filename', 'unknown')}: {e}")
                completed_files += 1
                if progress_callback:
                    progress_callback(completed_files, total_files)

                return {'success': False, 'error': str(e), 'file_data': file_data}

        logger.info(f"Starting batch upload of {total_files} files with {max_workers} workers")

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_file = {executor.submit(upload_single, file_data): file_data
                             for file_data in files_data}

            for future in as_completed(future_to_file):
                result = future.result()
                results.append(result)

        success_count = sum(1 for r in results if r['success'])
        logger.info(f"Batch upload completed: {success_count}/{total_files} successful")

        return results

    def get_file_info(self, key: str) -> Dict[str, any]:
        try:
            response = self.client.head_object(Bucket=self.bucket_name, Key=key)

            return {
                'key': key,
                'bucket': self.bucket_name,
                'size': response.get('ContentLength'),
                'content_type': response.get('ContentType'),
                'last_modified': response.get('LastModified'),
                'etag': response.get('ETag', '').strip('"'),
                'metadata': response.get('Metadata', {})
            }

        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                return None
            self._handle_r2_errors(e)

    def delete_file(self, key: str) -> bool:
        try:
            self.client.delete_object(Bucket=self.bucket_name, Key=key)
            logger.info(f"Successfully deleted file: {key}")
            return True

        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                logger.warning(f"File not found for deletion: {key}")
                return False
            self._handle_r2_errors(e)

    def delete_multiple_files(self, keys: List[str]) -> Dict[str, any]:
        if not keys:
            return {'deleted': [], 'errors': []}

        if len(keys) > 1000:
            raise ValidationError("Too many files to delete at once. Maximum 1000 files")

        try:
            delete_request = {
                'Objects': [{'Key': key} for key in keys],
                'Quiet': False
            }

            response = self.client.delete_objects(
                Bucket=self.bucket_name,
                Delete=delete_request
            )

            deleted = [obj['Key'] for obj in response.get('Deleted', [])]
            errors = [{'key': obj['Key'], 'message': obj.get('Message', 'Unknown error')}
                     for obj in response.get('Errors', [])]

            logger.info(f"Batch delete completed: {len(deleted)} deleted, {len(errors)} errors")

            return {'deleted': deleted, 'errors': errors}

        except ClientError as e:
            self._handle_r2_errors(e)

    def list_files(self, prefix: str = "", max_keys: int = 1000) -> List[Dict[str, any]]:
        if max_keys > 1000:
            max_keys = 1000

        try:
            response = self.client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix,
                MaxKeys=max_keys
            )

            files = []
            for obj in response.get('Contents', []):
                files.append({
                    'key': obj['Key'],
                    'size': obj['Size'],
                    'last_modified': obj['LastModified'],
                    'etag': obj['ETag'].strip('"')
                })

            return files

        except ClientError as e:
            self._handle_r2_errors(e)

    def generate_presigned_url(
        self,
        key: str,
        expiry_seconds: int = 3600,
        http_method: str = 'get_object'
    ) -> str:
        if expiry_seconds > 604800:  # 7 days
            raise ValidationError("Presigned URL expiry cannot exceed 7 days")

        try:
            url = self.client.generate_presigned_url(
                http_method,
                Params={'Bucket': self.bucket_name, 'Key': key},
                ExpiresIn=expiry_seconds
            )

            logger.debug(f"Generated presigned URL for {key} (expires in {expiry_seconds}s)")
            return url

        except ClientError as e:
            self._handle_r2_errors(e)

    def copy_file(self, source_key: str, destination_key: str, metadata: Dict[str, str] = None) -> bool:
        try:
            copy_source = {'Bucket': self.bucket_name, 'Key': source_key}
            extra_args = {}

            if metadata:
                extra_args['Metadata'] = metadata
                extra_args['MetadataDirective'] = 'REPLACE'

            self.client.copy_object(
                CopySource=copy_source,
                Bucket=self.bucket_name,
                Key=destination_key,
                **extra_args
            )

            logger.info(f"Successfully copied file from {source_key} to {destination_key}")
            return True

        except ClientError as e:
            self._handle_r2_errors(e)

    def get_bucket_info(self) -> Dict[str, any]:
        try:
            location_response = self.client.get_bucket_location(Bucket=self.bucket_name)

            files = self.list_files(max_keys=1)

            return {
                'bucket_name': self.bucket_name,
                'region': location_response.get('LocationConstraint', 'auto'),
                'accessible': True,
                'sample_file_count': len(files)
            }

        except ClientError as e:
            self._handle_r2_errors(e)

    def calculate_file_hash(self, file_obj: BinaryIO, algorithm: str = 'md5') -> str:
        hash_obj = hashlib.new(algorithm)
        file_obj.seek(0)

        for chunk in iter(lambda: file_obj.read(8192), b''):
            hash_obj.update(chunk)

        file_obj.seek(0)
        return hash_obj.hexdigest()

    def upload_with_integrity_check(
        self,
        file_obj: BinaryIO,
        filename: str = None,
        key: str = None,
        check_algorithm: str = 'md5'
    ) -> Dict[str, any]:
        original_hash = self.calculate_file_hash(file_obj, check_algorithm)

        result = self.upload_single_file(file_obj, filename, key, metadata={
            f'{check_algorithm}_hash': original_hash
        })

        file_info = self.get_file_info(result['key'])
        stored_hash = file_info['metadata'].get(f'{check_algorithm}_hash')

        if stored_hash != original_hash:
            logger.error(f"Integrity check failed for {result['key']}")
            self.delete_file(result['key'])
            raise UploadError("File integrity check failed after upload")

        result['integrity_verified'] = True
        result['hash'] = original_hash

        return result
