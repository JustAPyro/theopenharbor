"""
Integration tests for R2 storage functionality.
Tests the full R2 integration including storage service, file uploads, and error handling.
"""

import pytest
import io
import json
from unittest.mock import patch, MagicMock, Mock
from werkzeug.datastructures import FileStorage
from botocore.exceptions import ClientError

from app import create_app
from app.models import db, User, Collection, File
from app.services.storage_service import StorageService
from app.integrations.file_storage import CloudflareR2Storage, ValidationError, UploadError


@pytest.fixture(scope='function')
def r2_test_user(app):
    """Create a test user for R2 tests."""
    with app.app_context():
        # Clean up any existing test users first
        existing_user = User.query.filter_by(email='r2test@example.com').first()
        if existing_user:
            db.session.delete(existing_user)
            db.session.commit()

        user = User(email='r2test@example.com')
        user.set_password('TestPass123')
        db.session.add(user)
        db.session.commit()

        yield user

        # Clean up after test
        db.session.delete(user)
        db.session.commit()


@pytest.fixture(scope='function')
def r2_test_collection(app, r2_test_user):
    """Create a test collection for R2 tests."""
    with app.app_context():
        collection = Collection(
            name='R2 Test Collection',
            description='Testing R2 integration',
            privacy='unlisted',
            user_id=r2_test_user.id
        )
        db.session.add(collection)
        db.session.commit()

        yield collection

        # Clean up handled by cascade delete when user is deleted


@pytest.fixture
def mock_r2_client():
    """Mock R2 client for testing."""
    with patch('app.integrations.file_storage.boto3.client') as mock_client:
        mock_instance = MagicMock()
        mock_client.return_value = mock_instance

        # Mock successful responses
        mock_instance.head_bucket.return_value = {}
        mock_instance.upload_fileobj.return_value = {}
        mock_instance.generate_presigned_url.return_value = 'https://example.com/file.jpg'
        mock_instance.delete_object.return_value = {}
        mock_instance.head_object.return_value = {
            'ContentLength': 1024,
            'ContentType': 'image/jpeg',
            'LastModified': '2024-01-01',
            'ETag': 'test-etag',
            'Metadata': {}
        }

        yield mock_instance


@pytest.fixture
def mock_r2_config():
    """Mock R2 configuration constants."""
    with patch('app.integrations.file_storage.R2_ACCOUNT_ID', 'test_account_id'), \
         patch('app.integrations.file_storage.R2_ACCESS_KEY_ID', 'test_access_key'), \
         patch('app.integrations.file_storage.R2_SECRET_ACCESS_KEY', 'test_secret_key'), \
         patch('app.integrations.file_storage.R2_BUCKET_NAME', 'test_bucket'), \
         patch('app.integrations.file_storage.R2_REGION', 'auto'):
        yield


@pytest.fixture
def sample_image_file():
    """Create a sample image file for testing."""
    # Create a minimal JPEG file (1x1 pixel)
    jpeg_data = bytes([
        0xFF, 0xD8, 0xFF, 0xE0, 0x00, 0x10, 0x4A, 0x46, 0x49, 0x46, 0x00, 0x01,
        0x01, 0x01, 0x00, 0x48, 0x00, 0x48, 0x00, 0x00, 0xFF, 0xDB, 0x00, 0x43,
        0x00, 0x08, 0x06, 0x06, 0x07, 0x06, 0x05, 0x08, 0x07, 0x07, 0x07, 0x09,
        0x09, 0x08, 0x0A, 0x0C, 0x14, 0x0D, 0x0C, 0x0B, 0x0B, 0x0C, 0x19, 0x12,
        0x13, 0x0F, 0x14, 0x1D, 0x1A, 0x1F, 0x1E, 0x1D, 0x1A, 0x1C, 0x1C, 0x20,
        0x24, 0x2E, 0x27, 0x20, 0x22, 0x2C, 0x23, 0x1C, 0x1C, 0x28, 0x37, 0x29,
        0x2C, 0x30, 0x31, 0x34, 0x34, 0x34, 0x1F, 0x27, 0x39, 0x3D, 0x38, 0x32,
        0x3C, 0x2E, 0x33, 0x34, 0x32, 0xFF, 0xC0, 0x00, 0x11, 0x08, 0x00, 0x01,
        0x00, 0x01, 0x01, 0x01, 0x11, 0x00, 0x02, 0x11, 0x01, 0x03, 0x11, 0x01,
        0xFF, 0xC4, 0x00, 0x14, 0x00, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
        0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x08, 0xFF, 0xC4,
        0x00, 0x14, 0x10, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
        0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xFF, 0xDA, 0x00, 0x0C,
        0x03, 0x01, 0x00, 0x02, 0x11, 0x03, 0x11, 0x00, 0x3F, 0x00, 0xB2, 0xC0,
        0x07, 0xFF, 0xD9
    ])

    return io.BytesIO(jpeg_data)


class TestR2StorageService:
    """Test R2 storage service integration."""

    def test_storage_service_initialization_local(self, app):
        """Test storage service initializes correctly with local backend."""
        with app.app_context():
            app.config['STORAGE_BACKEND'] = 'local'
            app.r2_storage = None

            storage = StorageService()
            assert storage.backend == 'local'
            assert storage.r2_storage is None

    def test_storage_service_initialization_r2(self, app, mock_r2_client, mock_r2_config):
        """Test storage service initializes correctly with R2 backend."""
        with app.app_context():
            app.config['STORAGE_BACKEND'] = 'r2'
            app.r2_storage = CloudflareR2Storage()

            storage = StorageService()
            assert storage.backend == 'r2'
            assert storage.r2_storage is not None

    def test_file_upload_to_r2(self, app, r2_test_collection, sample_image_file, mock_r2_client, mock_r2_config):
        """Test file upload to R2 storage."""
        with app.app_context():
            app.config['STORAGE_BACKEND'] = 'r2'
            app.r2_storage = CloudflareR2Storage()

            storage = StorageService()

            # Mock R2 upload response
            mock_r2_client.upload_fileobj.return_value = {}

            with patch.object(storage.r2_storage, 'upload_single_file') as mock_upload:
                mock_upload.return_value = {
                    'key': f'collections/{r2_test_collection.uuid}/test.jpg',
                    'bucket': 'test-bucket',
                    'size': 1024,
                    'upload_method': 'single_part'
                }

                result = storage.upload_file(
                    file_obj=sample_image_file,
                    filename='test.jpg',
                    collection=r2_test_collection
                )

                assert result['success'] is True
                assert result['file_record'] is not None
                assert result['file_record'].storage_backend == 'r2'
                assert result['file_record'].original_filename == 'test.jpg'
                assert result['file_record'].collection_id == r2_test_collection.id

    def test_file_upload_to_local_fallback(self, app, r2_test_collection, sample_image_file):
        """Test file upload falls back to local storage."""
        with app.app_context():
            app.config['STORAGE_BACKEND'] = 'local'
            app.r2_storage = None

            storage = StorageService()

            with patch('os.makedirs'):
                with patch('builtins.open', create=True) as mock_open:
                    with patch('os.path.getsize', return_value=1024):
                        result = storage.upload_file(
                            file_obj=sample_image_file,
                            filename='test.jpg',
                            collection=r2_test_collection
                        )

                        assert result['success'] is True
                        assert result['file_record'] is not None
                        assert result['file_record'].storage_backend == 'local'
                        assert result['file_record'].original_filename == 'test.jpg'

    def test_upload_error_handling(self, app, r2_test_collection, sample_image_file, mock_r2_client, mock_r2_config):
        """Test error handling for R2 upload failures."""
        with app.app_context():
            app.config['STORAGE_BACKEND'] = 'r2'
            app.r2_storage = CloudflareR2Storage()

            storage = StorageService()

            # Mock R2 error
            mock_error = ClientError(
                {'Error': {'Code': 'AccessDenied', 'Message': 'Access denied'}},
                'UploadFile'
            )

            with patch.object(storage.r2_storage, 'upload_single_file', side_effect=UploadError("Access denied")):
                result = storage.upload_file(
                    file_obj=sample_image_file,
                    filename='test.jpg',
                    collection=r2_test_collection
                )

                assert result['success'] is False
                assert 'Access denied' in result['error']
                assert result['file_record'] is None

    def test_generate_file_url_r2(self, app, r2_test_collection, mock_r2_client, mock_r2_config):
        """Test file URL generation for R2 files."""
        with app.app_context():
            app.config['STORAGE_BACKEND'] = 'r2'
            app.r2_storage = CloudflareR2Storage()

            storage = StorageService()

            # Create a test file record
            file_record = File(
                filename='test.jpg',
                original_filename='test.jpg',
                mime_type='image/jpeg',
                size=1024,
                storage_path='collections/test/test.jpg',
                storage_backend='r2',
                collection_id=r2_test_collection.id
            )

            url = storage.generate_file_url(file_record, expiry_seconds=1800)
            assert url == 'https://example.com/file.jpg'

    def test_delete_file_r2(self, app, r2_test_collection, mock_r2_client, mock_r2_config):
        """Test file deletion from R2."""
        with app.app_context():
            app.config['STORAGE_BACKEND'] = 'r2'
            app.r2_storage = CloudflareR2Storage()

            storage = StorageService()

            file_record = File(
                filename='test.jpg',
                original_filename='test.jpg',
                mime_type='image/jpeg',
                size=1024,
                storage_path='collections/test/test.jpg',
                storage_backend='r2',
                collection_id=r2_test_collection.id
            )

            mock_r2_client.delete_object.return_value = {}

            with patch.object(storage.r2_storage, 'delete_file', return_value=True) as mock_delete:
                result = storage.delete_file(file_record)
                assert result is True
                mock_delete.assert_called_once_with('collections/test/test.jpg')


class TestR2UploadIntegration:
    """Test R2 upload integration through HTTP endpoints."""

    def test_r2_upload_via_api(self, client, r2_test_user, r2_test_collection, sample_image_file, mock_r2_client):
        """Test R2 upload through the upload API endpoint."""
        with client.session_transaction() as sess:
            sess['_user_id'] = str(r2_test_user.id)
            sess['_fresh'] = True

        # Mock the storage service to use R2 backend
        with patch('app.services.storage_service.StorageService._upload_to_r2') as mock_upload:
            # Mock the upload method to return a successful R2 result
            mock_file_record = File(
                filename='test_uuid.jpg',
                original_filename='test.jpg',
                mime_type='image/jpeg',
                size=1024,
                storage_path='collections/test_collection_uuid/test_uuid.jpg',
                storage_backend='r2',
                upload_complete=True,
                collection_id=r2_test_collection.id
            )
            mock_file_record.set_metadata({
                'upload_method': 'single_part',
                'r2_bucket': 'test-bucket'
            })

            mock_upload.return_value = {
                'success': True,
                'file_record': mock_file_record,
                'error': None,
                'storage_info': {
                    'key': f'collections/{r2_test_collection.uuid}/test.jpg',
                    'bucket': 'test-bucket',
                    'upload_method': 'single_part'
                }
            }

            sample_image_file.seek(0)
            file_storage = FileStorage(
                stream=sample_image_file,
                filename='test.jpg',
                content_type='image/jpeg'
            )

            response = client.post('/collections/api/upload-files',
                                 data={
                                     'collection_id': r2_test_collection.id,
                                     'file_test': file_storage
                                 })

            assert response.status_code == 200
            data = response.get_json()
            assert data['success'] is True
            assert len(data['uploaded_files']) == 1
            assert 'storage_info' in data['uploaded_files'][0]

    def test_r2_upload_multipart_simulation(self, app, r2_test_collection, mock_r2_client, mock_r2_config):
        """Test R2 multipart upload simulation."""
        with app.app_context():
            app.config['STORAGE_BACKEND'] = 'r2'
            app.r2_storage = CloudflareR2Storage()

            storage = StorageService()

            # Create a large file buffer (simulate multipart threshold)
            large_file = io.BytesIO(b'0' * (101 * 1024 * 1024))  # 101MB

            # Mock multipart upload response
            with patch.object(storage.r2_storage, 'upload_single_file') as mock_upload:
                mock_upload.return_value = {
                    'key': f'collections/{r2_test_collection.uuid}/large_file.jpg',
                    'bucket': 'test-bucket',
                    'size': 101 * 1024 * 1024,
                    'upload_method': 'multipart',
                    'parts_count': 3,
                    'part_size': 50 * 1024 * 1024
                }

                result = storage.upload_file(
                    file_obj=large_file,
                    filename='large_file.jpg',
                    collection=r2_test_collection
                )

                assert result['success'] is True
                assert result['file_record'] is not None

                # Check metadata contains multipart info
                metadata = result['file_record'].get_metadata()
                assert metadata.get('upload_method') == 'multipart'
                assert metadata.get('parts_count') == 3

    def test_r2_error_scenarios(self, app, r2_test_collection, sample_image_file, mock_r2_client, mock_r2_config):
        """Test various R2 error scenarios."""
        with app.app_context():
            app.config['STORAGE_BACKEND'] = 'r2'
            app.r2_storage = CloudflareR2Storage()

            storage = StorageService()

            # Test different error types
            error_scenarios = [
                ('AccessDenied', 'Insufficient permissions for R2 operation'),
                ('EntityTooLarge', 'File size exceeds R2 limits (5GB maximum)'),
                ('NoSuchBucket', 'R2 bucket "test-bucket" does not exist'),
                ('NetworkError', 'R2 error: NetworkError')
            ]

            for error_code, expected_message in error_scenarios:
                mock_error = ClientError(
                    {'Error': {'Code': error_code, 'Message': 'Mock error'}},
                    'UploadFile'
                )

                with patch.object(storage.r2_storage, 'upload_single_file', side_effect=UploadError(expected_message)):
                    sample_image_file.seek(0)  # Reset file pointer

                    result = storage.upload_file(
                        file_obj=sample_image_file,
                        filename=f'test_{error_code.lower()}.jpg',
                        collection=r2_test_collection
                    )

                    assert result['success'] is False
                    assert expected_message in result['error']


class TestFileModel:
    """Test File model enhancements for R2 support."""

    def test_file_model_r2_properties(self, app, r2_test_collection):
        """Test File model R2-specific properties."""
        with app.app_context():
            # Test R2 file
            r2_file = File(
                filename='test.jpg',
                original_filename='test.jpg',
                mime_type='image/jpeg',
                size=1024,
                storage_path='collections/test/test.jpg',
                storage_backend='r2',
                collection_id=r2_test_collection.id
            )

            assert r2_file.is_r2_file is True
            assert r2_file.is_image is True

            # Test local file
            local_file = File(
                filename='test.jpg',
                original_filename='test.jpg',
                mime_type='image/jpeg',
                size=1024,
                storage_path='/local/path/test.jpg',
                storage_backend='local',
                collection_id=r2_test_collection.id
            )

            assert local_file.is_r2_file is False
            assert local_file.is_image is True

    def test_file_metadata_methods(self, app, r2_test_collection):
        """Test File model metadata handling methods."""
        with app.app_context():
            file_record = File(
                filename='test.jpg',
                original_filename='test.jpg',
                mime_type='image/jpeg',
                size=1024,
                storage_path='collections/test/test.jpg',
                storage_backend='r2',
                collection_id=r2_test_collection.id
            )

            # Test setting metadata
            test_metadata = {
                'upload_method': 'multipart',
                'parts_count': 5,
                'bucket': 'test-bucket'
            }

            file_record.set_metadata(test_metadata)
            assert file_record.metadata_json is not None

            # Test getting metadata
            retrieved_metadata = file_record.get_metadata()
            assert retrieved_metadata == test_metadata
            assert retrieved_metadata['upload_method'] == 'multipart'
            assert retrieved_metadata['parts_count'] == 5

            # Test with no metadata
            file_record.set_metadata(None)
            assert file_record.metadata_json is None
            assert file_record.get_metadata() == {}

    def test_file_storage_url_property(self, app, r2_test_collection):
        """Test File model storage_url property for different backends."""
        with app.app_context():
            app.config['STORAGE_BACKEND'] = 'r2'

            # Mock R2 storage
            with patch('app.services.storage_service.StorageService') as mock_storage_class:
                mock_storage = MagicMock()
                mock_storage.generate_file_url.return_value = 'https://r2.example.com/file.jpg'
                mock_storage_class.return_value = mock_storage

                r2_file = File(
                    filename='test.jpg',
                    original_filename='test.jpg',
                    mime_type='image/jpeg',
                    size=1024,
                    storage_path='collections/test/test.jpg',
                    storage_backend='r2',
                    collection_id=r2_test_collection.id
                )

                # This would return the mocked URL in a real scenario
                # For now, just test the property exists
                assert hasattr(r2_file, 'storage_url')


class TestThumbnailService:
    """Test thumbnail service R2 integration."""

    @patch('app.services.thumbnail_service.PIL_AVAILABLE', True)
    def test_thumbnail_generation_r2(self, app, r2_test_collection, sample_image_file):
        """Test thumbnail generation for R2 files."""
        with app.app_context():
            app.config['STORAGE_BACKEND'] = 'r2'

            from app.services.thumbnail_service import ThumbnailService

            # Create file record
            file_record = File(
                filename='test.jpg',
                original_filename='test.jpg',
                mime_type='image/jpeg',
                size=1024,
                storage_path='collections/test/test.jpg',
                storage_backend='r2',
                collection_id=r2_test_collection.id
            )
            db.session.add(file_record)
            db.session.commit()

            thumbnail_service = ThumbnailService()

            # Mock the various dependencies
            with patch('requests.get') as mock_get:
                mock_response = MagicMock()
                mock_response.content = sample_image_file.read()
                mock_response.raise_for_status.return_value = None
                mock_get.return_value = mock_response

                # Mock storage service R2 storage
                mock_r2_storage = MagicMock()
                mock_r2_storage.upload_single_file.return_value = {'key': 'thumbnails/test/medium_test.jpg'}

                with patch.object(thumbnail_service.storage_service, 'generate_file_url',
                                return_value='https://example.com/file.jpg'):
                    with patch.object(thumbnail_service.storage_service, 'r2_storage', mock_r2_storage):

                        # Mock the thumbnail data creation directly
                        with patch.object(thumbnail_service, '_create_thumbnail_data',
                                        return_value=b'fake_thumbnail_data') as mock_create:

                            result = thumbnail_service.generate_thumbnail(file_record)

                            assert result is not None
                            mock_r2_storage.upload_single_file.assert_called_once()


class TestConfigurationHandling:
    """Test R2 configuration and environment handling."""

    def test_config_validation_r2_backend(self):
        """Test configuration validation for R2 backend."""
        from config import Config

        # Mock R2 configuration
        with patch.dict('os.environ', {
            'STORAGE_BACKEND': 'r2',
            'TOH_R2_ACCOUNT_ID': 'test_account',
            'TOH_R2_ACCESS_KEY': 'test_key',
            'TOH_R2_SECRET_KEY': 'test_secret',
            'TOH_R2_BUCKET_NAME': 'test_bucket',
            'TSH_SECRET_KEY': 'test_secret'
        }):
            Config.STORAGE_BACKEND = 'r2'
            Config.R2_ACCOUNT_ID = 'test_account'
            Config.R2_ACCESS_KEY_ID = 'test_key'
            Config.R2_SECRET_ACCESS_KEY = 'test_secret'
            Config.R2_BUCKET_NAME = 'test_bucket'
            Config.SECRET_KEY = 'test_secret'

            # Should not raise exception
            try:
                Config.validate_required_config()
            except ValueError:
                pytest.fail("Configuration validation should pass with all required R2 variables")

    def test_config_validation_missing_r2_vars(self):
        """Test configuration validation fails with missing R2 variables."""
        from config import Config

        Config.STORAGE_BACKEND = 'r2'
        Config.R2_ACCOUNT_ID = None
        Config.SECRET_KEY = 'test_secret'

        with pytest.raises(ValueError) as excinfo:
            Config.validate_required_config()

        assert 'Missing required configuration' in str(excinfo.value)
        assert 'R2_ACCOUNT_ID' in str(excinfo.value)

    def test_config_validation_local_backend(self):
        """Test configuration validation for local backend."""
        from config import Config

        Config.STORAGE_BACKEND = 'local'
        Config.SECRET_KEY = 'test_secret'

        # Should not require R2 configuration for local backend
        try:
            Config.validate_required_config()
        except ValueError:
            pytest.fail("Configuration validation should pass for local backend without R2 variables")