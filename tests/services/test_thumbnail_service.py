"""
Tests for thumbnail generation service.
"""

import pytest
import io
import os
from unittest.mock import patch, MagicMock, Mock
from PIL import Image

from app import create_app
from app.models import db, User, Collection, File
from app.services.thumbnail_service import ThumbnailService


@pytest.fixture(scope='function')
def thumbnail_test_user(app):
    """Create a test user for thumbnail tests."""
    with app.app_context():
        existing_user = User.query.filter_by(email='thumbnail@example.com').first()
        if existing_user:
            db.session.delete(existing_user)
            db.session.commit()

        user = User(email='thumbnail@example.com')
        user.set_password('TestPass123')
        db.session.add(user)
        db.session.commit()

        yield user

        db.session.delete(user)
        db.session.commit()


@pytest.fixture(scope='function')
def thumbnail_test_collection(app, thumbnail_test_user):
    """Create a test collection for thumbnail tests."""
    with app.app_context():
        collection = Collection(
            name='Thumbnail Test Collection',
            description='Testing thumbnail generation',
            privacy='unlisted',
            user_id=thumbnail_test_user.id
        )
        db.session.add(collection)
        db.session.commit()

        yield collection


@pytest.fixture
def sample_jpeg():
    """Create a small sample JPEG for testing."""
    # Create a 10x10 red square JPEG
    img = Image.new('RGB', (10, 10), color='red')
    buffer = io.BytesIO()
    img.save(buffer, format='JPEG')
    return buffer.getvalue()


class TestThumbnailService:
    """Test thumbnail generation service."""

    def test_thumbnail_service_initialization(self, app):
        """Test thumbnail service initializes correctly."""
        with app.app_context():
            thumbnail_service = ThumbnailService()
            assert thumbnail_service.storage_service is not None
            assert hasattr(thumbnail_service, 'THUMBNAIL_SIZES')
            assert 'medium' in thumbnail_service.THUMBNAIL_SIZES

    @patch('app.services.thumbnail_service.PIL_AVAILABLE', True)
    def test_generate_thumbnail_success_local(self, app, thumbnail_test_collection, sample_jpeg):
        """Test successful thumbnail generation with local storage."""
        with app.app_context():
            app.config['STORAGE_BACKEND'] = 'local'

            # Create file record
            file_record = File(
                filename='test.jpg',
                original_filename='test.jpg',
                mime_type='image/jpeg',
                size=len(sample_jpeg),
                storage_path='test/path/test.jpg',
                storage_backend='local',
                collection_id=thumbnail_test_collection.id
            )
            db.session.add(file_record)
            db.session.commit()

            thumbnail_service = ThumbnailService()

            # Mock the _get_file_data method directly to avoid open() conflicts
            with patch.object(thumbnail_service, '_get_file_data', return_value=sample_jpeg):
                # Mock thumbnail directory creation and saving
                with patch('os.makedirs'):
                    with patch('builtins.open', create=True) as mock_thumb_save:
                        result = thumbnail_service.generate_thumbnail(file_record, 'medium')

                        assert result is not None
                        assert result.startswith('thumbnails/')
                        assert file_record.collection.uuid in result

    @patch('app.services.thumbnail_service.PIL_AVAILABLE', True)
    def test_generate_thumbnail_success_r2(self, app, thumbnail_test_collection, sample_jpeg):
        """Test successful thumbnail generation with R2 storage."""
        with app.app_context():
            app.config['STORAGE_BACKEND'] = 'r2'

            # Create file record
            file_record = File(
                filename='test.jpg',
                original_filename='test.jpg',
                mime_type='image/jpeg',
                size=len(sample_jpeg),
                storage_path='collections/test/test.jpg',
                storage_backend='r2',
                collection_id=thumbnail_test_collection.id
            )
            db.session.add(file_record)
            db.session.commit()

            thumbnail_service = ThumbnailService()

            # Mock R2 file download
            with patch('requests.get') as mock_get:
                mock_response = MagicMock()
                mock_response.content = sample_jpeg
                mock_response.raise_for_status.return_value = None
                mock_get.return_value = mock_response

                # Mock storage service R2 storage
                mock_r2_storage = MagicMock()
                mock_r2_storage.upload_single_file.return_value = {'key': f'thumbnails/{file_record.collection.uuid}/medium_test.jpg'}

                with patch.object(thumbnail_service.storage_service, 'generate_file_url',
                                return_value='https://example.com/test.jpg'):
                    with patch.object(thumbnail_service.storage_service, 'r2_storage', mock_r2_storage):

                        result = thumbnail_service.generate_thumbnail(file_record, 'medium')

                        assert result == f'thumbnails/{file_record.collection.uuid}/medium_test.jpg'
                        mock_r2_storage.upload_single_file.assert_called_once()

                        # Verify upload was called with correct parameters
                        call_args = mock_r2_storage.upload_single_file.call_args
                        assert call_args[1]['key'] == f'thumbnails/{file_record.collection.uuid}/medium_test.jpg'
                        assert 'metadata' in call_args[1]

    @patch('app.services.thumbnail_service.PIL_AVAILABLE', False)
    def test_generate_thumbnail_no_pil(self, app, thumbnail_test_collection):
        """Test thumbnail generation when PIL is not available."""
        with app.app_context():
            file_record = File(
                filename='test.jpg',
                original_filename='test.jpg',
                mime_type='image/jpeg',
                size=1024,
                storage_path='test/path/test.jpg',
                collection_id=thumbnail_test_collection.id
            )

            thumbnail_service = ThumbnailService()
            result = thumbnail_service.generate_thumbnail(file_record)

            assert result is None

    def test_generate_thumbnail_non_image(self, app, thumbnail_test_collection):
        """Test thumbnail generation for non-image files."""
        with app.app_context():
            file_record = File(
                filename='document.pdf',
                original_filename='document.pdf',
                mime_type='application/pdf',
                size=1024,
                storage_path='test/path/document.pdf',
                collection_id=thumbnail_test_collection.id
            )

            thumbnail_service = ThumbnailService()
            result = thumbnail_service.generate_thumbnail(file_record)

            assert result is None

    def test_generate_thumbnail_invalid_size(self, app, thumbnail_test_collection):
        """Test thumbnail generation with invalid size."""
        with app.app_context():
            file_record = File(
                filename='test.jpg',
                original_filename='test.jpg',
                mime_type='image/jpeg',
                size=1024,
                storage_path='test/path/test.jpg',
                collection_id=thumbnail_test_collection.id
            )

            thumbnail_service = ThumbnailService()

            with pytest.raises(ValueError) as excinfo:
                thumbnail_service.generate_thumbnail(file_record, 'invalid_size')

            assert 'Invalid thumbnail size' in str(excinfo.value)

    @patch('app.services.thumbnail_service.PIL_AVAILABLE', True)
    def test_generate_thumbnail_file_not_found(self, app, thumbnail_test_collection):
        """Test thumbnail generation when original file is not found."""
        with app.app_context():
            app.config['STORAGE_BACKEND'] = 'local'

            file_record = File(
                filename='test.jpg',
                original_filename='test.jpg',
                mime_type='image/jpeg',
                size=1024,
                storage_path='nonexistent/path/test.jpg',
                storage_backend='local',
                collection_id=thumbnail_test_collection.id
            )

            thumbnail_service = ThumbnailService()

            # Mock file not existing
            with patch('os.path.exists', return_value=False):
                result = thumbnail_service.generate_thumbnail(file_record)
                assert result is None

    @patch('app.services.thumbnail_service.PIL_AVAILABLE', True)
    def test_batch_generate_thumbnails(self, app, thumbnail_test_collection, sample_jpeg):
        """Test batch thumbnail generation."""
        with app.app_context():
            app.config['STORAGE_BACKEND'] = 'local'

            # Create multiple file records
            files = []
            for i in range(3):
                file_record = File(
                    filename=f'test{i}.jpg',
                    original_filename=f'test{i}.jpg',
                    mime_type='image/jpeg',
                    size=len(sample_jpeg),
                    storage_path=f'test/path/test{i}.jpg',
                    storage_backend='local',
                    collection_id=thumbnail_test_collection.id
                )
                db.session.add(file_record)
                files.append(file_record)

            db.session.commit()

            thumbnail_service = ThumbnailService()

            # Mock the _get_file_data method directly to avoid open() conflicts
            with patch.object(thumbnail_service, '_get_file_data', return_value=sample_jpeg):
                with patch('os.makedirs'):
                    with patch('builtins.open', create=True):
                        results = thumbnail_service.batch_generate_thumbnails(files, 'medium')

                        assert len(results) == 3
                        for file_id, thumbnail_path in results.items():
                            assert thumbnail_path.startswith('thumbnails/')

    def test_get_file_data_r2_error(self, app, thumbnail_test_collection):
        """Test _get_file_data method handles R2 errors gracefully."""
        with app.app_context():
            app.config['STORAGE_BACKEND'] = 'r2'

            file_record = File(
                filename='test.jpg',
                original_filename='test.jpg',
                mime_type='image/jpeg',
                size=1024,
                storage_path='collections/test/test.jpg',
                storage_backend='r2',
                collection_id=thumbnail_test_collection.id
            )

            thumbnail_service = ThumbnailService()

            # Mock storage service to raise exception
            with patch.object(thumbnail_service.storage_service, 'generate_file_url',
                            side_effect=Exception("R2 error")):
                result = thumbnail_service._get_file_data(file_record)
                assert result is None

    @patch('app.services.thumbnail_service.PIL_AVAILABLE', True)
    def test_create_thumbnail_data_corrupted_image(self, app):
        """Test _create_thumbnail_data method handles corrupted images."""
        thumbnail_service = ThumbnailService()

        # Create invalid image data
        corrupted_data = b'not an image'

        result = thumbnail_service._create_thumbnail_data(corrupted_data, 'medium')
        assert result is None

    @patch('app.services.thumbnail_service.PIL_AVAILABLE', True)
    def test_create_thumbnail_data_different_formats(self, app, sample_jpeg):
        """Test _create_thumbnail_data method handles different image formats."""
        thumbnail_service = ThumbnailService()

        # Test with JPEG data
        result = thumbnail_service._create_thumbnail_data(sample_jpeg, 'medium')
        assert result is not None
        assert isinstance(result, bytes)

        # Test size constraints
        assert 'medium' in thumbnail_service.THUMBNAIL_SIZES
        medium_size = thumbnail_service.THUMBNAIL_SIZES['medium']
        assert medium_size == (300, 300)

        # Test all available sizes
        for size_name, dimensions in thumbnail_service.THUMBNAIL_SIZES.items():
            result = thumbnail_service._create_thumbnail_data(sample_jpeg, size_name)
            assert result is not None, f"Failed to create thumbnail for size {size_name}"

    @patch('app.services.thumbnail_service.PIL_AVAILABLE', True)
    def test_thumbnail_rgba_conversion(self, app):
        """Test thumbnail generation handles RGBA images correctly."""
        # Create a RGBA image with transparency
        img = Image.new('RGBA', (100, 100), color=(255, 0, 0, 128))  # Semi-transparent red
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        rgba_data = buffer.getvalue()

        thumbnail_service = ThumbnailService()
        result = thumbnail_service._create_thumbnail_data(rgba_data, 'medium')

        assert result is not None
        # The result should be JPEG (no transparency)
        assert result.startswith(b'\xff\xd8')  # JPEG magic bytes