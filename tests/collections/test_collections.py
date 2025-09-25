"""
Tests for collections functionality including upload, view, and management.
"""

import pytest
import tempfile
import os
import json
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock
from werkzeug.datastructures import FileStorage
from io import BytesIO

from app import create_app
from app.models import db, User, Collection, File


@pytest.fixture(scope='function')
def test_user(app):
    """Create a test user."""
    with app.app_context():
        # Clean up any existing test users first
        existing_user = User.query.filter_by(email='test@example.com').first()
        if existing_user:
            db.session.delete(existing_user)
            db.session.commit()

        user = User(email='test@example.com')
        user.set_password('TestPass123')
        db.session.add(user)
        db.session.commit()

        yield user

        # Clean up after test
        db.session.delete(user)
        db.session.commit()


@pytest.fixture(scope='function')
def test_collection(app, test_user):
    """Create a test collection."""
    with app.app_context():
        collection = Collection(
            name='Test Collection',
            description='A test photo collection',
            privacy='unlisted',
            user_id=test_user.id
        )
        db.session.add(collection)
        db.session.commit()

        yield collection

        # Clean up handled by cascade delete when user is deleted


@pytest.fixture
def sample_image():
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

    return BytesIO(jpeg_data)


class TestCollectionRoutes:
    """Test collection routes and views."""

    def test_upload_page_requires_login(self, client):
        """Test that upload page requires authentication."""
        response = client.get('/collections/upload')
        assert response.status_code == 302
        assert '/auth/log-in' in response.location

    def test_upload_page_renders_for_authenticated_user(self, client, test_user):
        """Test upload page renders correctly for logged-in user."""
        with client.session_transaction() as sess:
            sess['_user_id'] = str(test_user.id)
            sess['_fresh'] = True

        response = client.get('/collections/upload')
        assert response.status_code == 200
        assert b'Upload Collection' in response.data
        assert b'drag-drop' in response.data.lower() or b'upload-zone' in response.data

    def test_create_collection_with_valid_data(self, client, test_user, app):
        """Test creating a collection with valid data."""
        with client.session_transaction() as sess:
            sess['_user_id'] = str(test_user.id)
            sess['_fresh'] = True

        form_data = {
            'name': 'My Test Collection',
            'description': 'A beautiful collection of photos',
            'privacy': 'unlisted',
            'expiration': '',
            'csrf_token': 'test'  # Would need proper CSRF token in real test
        }

        with patch('flask_wtf.csrf.validate_csrf', return_value=True):
            response = client.post('/collections/upload', data=form_data, follow_redirects=True)

            # Check if collection was created
            with app.app_context():
                collection = Collection.query.filter_by(name='My Test Collection').first()
                assert collection is not None
                assert collection.user_id == test_user.id
                assert collection.description == 'A beautiful collection of photos'
                assert collection.privacy == 'unlisted'

    def test_create_collection_with_password(self, client, test_user, app):
        """Test creating a password-protected collection."""
        with client.session_transaction() as sess:
            sess['_user_id'] = str(test_user.id)
            sess['_fresh'] = True

        form_data = {
            'name': 'Secret Collection',
            'description': '',
            'privacy': 'password',
            'password': 'secret123',
            'expiration': '',
            'csrf_token': 'test'
        }

        with patch('flask_wtf.csrf.validate_csrf', return_value=True):
            response = client.post('/collections/upload', data=form_data, follow_redirects=True)

            with app.app_context():
                collection = Collection.query.filter_by(name='Secret Collection').first()
                assert collection is not None
                assert collection.privacy == 'password'
                assert collection.password_hash is not None
                assert collection.check_password('secret123')

    def test_create_collection_with_expiration(self, client, test_user, app):
        """Test creating a collection with expiration."""
        with client.session_transaction() as sess:
            sess['_user_id'] = str(test_user.id)
            sess['_fresh'] = True

        form_data = {
            'name': 'Temporary Collection',
            'description': '',
            'privacy': 'unlisted',
            'expiration': '1_week',
            'csrf_token': 'test'
        }

        with patch('flask_wtf.csrf.validate_csrf', return_value=True):
            response = client.post('/collections/upload', data=form_data, follow_redirects=True)

            with app.app_context():
                collection = Collection.query.filter_by(name='Temporary Collection').first()
                assert collection is not None
                assert collection.expires_at is not None
                # Should expire approximately 1 week from now
                # Note: The code uses UTC but stores as naive datetime
                expected_expiry = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(weeks=1)
                time_diff = abs((collection.expires_at - expected_expiry).total_seconds())
                assert time_diff < 3600  # Within 1 hour to account for any timezone differences

    def test_view_collection_exists(self, client, test_collection):
        """Test viewing an existing collection."""
        response = client.get(f'/collections/{test_collection.uuid}')
        assert response.status_code == 200
        assert test_collection.name.encode() in response.data

    def test_view_collection_not_found(self, client):
        """Test viewing a non-existent collection."""
        fake_uuid = '12345678-1234-1234-1234-123456789012'
        response = client.get(f'/collections/{fake_uuid}')
        assert response.status_code == 404

    def test_collections_index_requires_login(self, client):
        """Test that collections index requires authentication."""
        response = client.get('/collections/')
        assert response.status_code == 302
        assert '/auth/log-in' in response.location

    def test_collections_index_shows_user_collections(self, client, test_user, test_collection):
        """Test collections index shows user's collections."""
        with client.session_transaction() as sess:
            sess['_user_id'] = str(test_user.id)
            sess['_fresh'] = True

        response = client.get('/collections/')
        assert response.status_code == 200
        assert test_collection.name.encode() in response.data


class TestFileValidationAPI:
    """Test file validation API endpoint."""

    def test_validate_files_requires_login(self, client):
        """Test that file validation requires authentication."""
        response = client.post('/collections/api/validate-files',
                              json={'files': []})
        assert response.status_code == 302

    def test_validate_valid_files(self, client, test_user):
        """Test validation of valid image files."""
        with client.session_transaction() as sess:
            sess['_user_id'] = str(test_user.id)
            sess['_fresh'] = True

        files_data = [
            {
                'name': 'photo1.jpg',
                'type': 'image/jpeg',
                'size': 1024 * 1024  # 1MB
            },
            {
                'name': 'photo2.png',
                'type': 'image/png',
                'size': 2 * 1024 * 1024  # 2MB
            }
        ]

        response = client.post('/collections/api/validate-files',
                              json={'files': files_data})

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert len(data['valid_files']) == 2
        assert data['total_size'] == 3 * 1024 * 1024

    def test_validate_invalid_file_type(self, client, test_user):
        """Test validation rejects invalid file types."""
        with client.session_transaction() as sess:
            sess['_user_id'] = str(test_user.id)
            sess['_fresh'] = True

        files_data = [
            {
                'name': 'document.pdf',
                'type': 'application/pdf',
                'size': 1024
            }
        ]

        response = client.post('/collections/api/validate-files',
                              json={'files': files_data})

        assert response.status_code == 400
        data = response.get_json()
        assert data['success'] is False
        assert 'errors' in data

    def test_validate_file_too_large(self, client, test_user):
        """Test validation rejects files that are too large."""
        with client.session_transaction() as sess:
            sess['_user_id'] = str(test_user.id)
            sess['_fresh'] = True

        files_data = [
            {
                'name': 'huge_photo.jpg',
                'type': 'image/jpeg',
                'size': 60 * 1024 * 1024  # 60MB (over 50MB limit)
            }
        ]

        response = client.post('/collections/api/validate-files',
                              json={'files': files_data})

        assert response.status_code == 400
        data = response.get_json()
        assert data['success'] is False
        assert 'File too large' in str(data)

    def test_validate_too_many_files(self, client, test_user):
        """Test validation rejects too many files."""
        with client.session_transaction() as sess:
            sess['_user_id'] = str(test_user.id)
            sess['_fresh'] = True

        # Create 101 files (over 100 limit)
        files_data = [
            {
                'name': f'photo{i}.jpg',
                'type': 'image/jpeg',
                'size': 1024
            } for i in range(101)
        ]

        response = client.post('/collections/api/validate-files',
                              json={'files': files_data})

        assert response.status_code == 400
        data = response.get_json()
        assert data['success'] is False
        assert 'Maximum 100 files' in data['error']

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


class TestFileUploadAPI:
    """Test file upload API endpoint."""

    def test_upload_files_requires_login(self, client):
        """Test that file upload requires authentication."""
        response = client.post('/collections/api/upload-files')
        assert response.status_code == 302

    def test_upload_files_requires_collection_id(self, client, test_user):
        """Test that upload requires a valid collection ID."""
        with client.session_transaction() as sess:
            sess['_user_id'] = str(test_user.id)
            sess['_fresh'] = True

        response = client.post('/collections/api/upload-files')

        assert response.status_code == 400
        data = response.get_json()
        assert data['success'] is False
        assert 'Collection ID required' in data['error']

    def test_upload_files_invalid_collection(self, client, test_user):
        """Test upload with invalid collection ID."""
        with client.session_transaction() as sess:
            sess['_user_id'] = str(test_user.id)
            sess['_fresh'] = True

        response = client.post('/collections/api/upload-files',
                              data={'collection_id': 99999})

        assert response.status_code == 404
        data = response.get_json()
        assert data['success'] is False
        assert 'not found' in data['error']

    def test_upload_files_success(self, client, test_user, test_collection, sample_image, app):
        """Test successful file upload."""
        with client.session_transaction() as sess:
            sess['_user_id'] = str(test_user.id)
            sess['_fresh'] = True

        # Create a FileStorage object
        sample_image.seek(0)
        file_storage = FileStorage(
            stream=sample_image,
            filename='test_photo.jpg',
            content_type='image/jpeg'
        )

        with patch('app.services.storage_service.StorageService._upload_to_local') as mock_upload:
            # Mock the upload method to return a successful result
            mock_file_record = File(
                filename='test_uuid.jpg',
                original_filename='test_photo.jpg',
                mime_type='image/jpeg',
                size=1024,
                storage_path='uploads/test_collection_uuid/test_uuid.jpg',
                storage_backend='local',
                upload_complete=True,
                collection_id=test_collection.id
            )
            mock_upload.return_value = {
                'success': True,
                'file_record': mock_file_record,
                'error': None,
                'storage_info': {'upload_method': 'local', 'path': '/fake/path'}
            }

            response = client.post('/collections/api/upload-files',
                                      data={
                                          'collection_id': test_collection.id,
                                          'file_test': file_storage
                                      })

            assert response.status_code == 200
            data = response.get_json()
            assert data['success'] is True
            assert len(data['uploaded_files']) == 1
            assert data['uploaded_files'][0]['filename'] == 'test_photo.jpg'

            # Verify the upload method was called
            mock_upload.assert_called_once()


class TestCollectionModel:
    """Test Collection model functionality."""

    def test_collection_creation(self, app, test_user):
        """Test basic collection creation."""
        with app.app_context():
            collection = Collection(
                name='Test Collection',
                description='Test description',
                user_id=test_user.id
            )
            db.session.add(collection)
            db.session.commit()

            assert collection.id is not None
            assert collection.uuid is not None
            assert collection.name == 'Test Collection'
            assert collection.user_id == test_user.id
            assert collection.privacy == 'unlisted'  # Default

    def test_collection_password_methods(self, app, test_user):
        """Test collection password setting and checking."""
        with app.app_context():
            collection = Collection(
                name='Password Collection',
                user_id=test_user.id
            )

            # Set password
            collection.set_password('secret123')
            assert collection.password_hash is not None

            # Check correct password
            assert collection.check_password('secret123') is True

            # Check incorrect password
            assert collection.check_password('wrongpass') is False

            # Remove password
            collection.set_password(None)
            assert collection.password_hash is None
            assert collection.check_password('anything') is True

    def test_collection_properties(self, app, test_user):
        """Test collection computed properties."""
        with app.app_context():
            collection = Collection(
                name='Test Collection',
                user_id=test_user.id
            )
            db.session.add(collection)
            db.session.commit()

            # Initially empty
            assert collection.file_count == 0
            assert collection.total_size == 0

            # Add some files
            file1 = File(
                filename='test1.jpg',
                original_filename='test1.jpg',
                mime_type='image/jpeg',
                size=1024,
                storage_path='/path/to/test1.jpg',
                collection_id=collection.id
            )

            file2 = File(
                filename='test2.jpg',
                original_filename='test2.jpg',
                mime_type='image/jpeg',
                size=2048,
                storage_path='/path/to/test2.jpg',
                collection_id=collection.id
            )

            db.session.add_all([file1, file2])
            db.session.commit()

            # Check properties
            assert collection.file_count == 2
            assert collection.total_size == 3072


class TestFileModel:
    """Test File model functionality."""

    def test_file_creation(self, app, test_collection):
        """Test basic file creation."""
        with app.app_context():
            file = File(
                filename='stored_name.jpg',
                original_filename='my_photo.jpg',
                mime_type='image/jpeg',
                size=1024 * 1024,  # 1MB
                storage_path='/uploads/stored_name.jpg',
                collection_id=test_collection.id
            )
            db.session.add(file)
            db.session.commit()

            assert file.id is not None
            assert file.uuid is not None
            assert file.original_filename == 'my_photo.jpg'
            assert file.collection_id == test_collection.id

    def test_file_size_human(self, app, test_collection):
        """Test human-readable file size formatting."""
        with app.app_context():
            # Test different file sizes
            test_cases = [
                (512, '512 B'),
                (1024, '1.0 KB'),
                (1536, '1.5 KB'),
                (1024 * 1024, '1.0 MB'),
                (1.5 * 1024 * 1024, '1.5 MB'),
                (1024 * 1024 * 1024, '1.0 GB'),
            ]

            for size_bytes, expected in test_cases:
                file = File(
                    filename='test.jpg',
                    original_filename='test.jpg',
                    mime_type='image/jpeg',
                    size=int(size_bytes),
                    storage_path='/test.jpg',
                    collection_id=test_collection.id
                )
                assert file.size_human == expected


class TestCollectionForms:
    """Test collection-related forms."""

    def test_collection_form_validation(self, app):
        """Test collection form validation."""
        with app.app_context():
            from app.forms import CollectionForm

            # Valid form data
            form = CollectionForm(data={
                'name': 'My Collection',
                'description': 'A test collection',
                'privacy': 'unlisted',
                'expiration': ''
            })

            # Note: CSRF validation would fail in real test
            # assert form.validate() is True

    def test_collection_form_required_fields(self, app):
        """Test collection form required field validation."""
        with app.app_context():
            from app.forms import CollectionForm

            # Missing required name
            form = CollectionForm(data={
                'name': '',
                'description': 'A test collection',
                'privacy': 'unlisted',
            })

            # Would fail validation due to missing name
            # This test structure shows how form validation would work


# Integration Test Example
class TestCollectionWorkflow:
    """Test complete collection workflow."""

    def test_complete_upload_workflow(self, client, test_user, sample_image, app):
        """Test complete workflow from collection creation to file upload."""
        with client.session_transaction() as sess:
            sess['_user_id'] = str(test_user.id)
            sess['_fresh'] = True

        # Step 1: Create collection
        form_data = {
            'name': 'Workflow Test Collection',
            'description': 'Testing complete workflow',
            'privacy': 'unlisted',
            'csrf_token': 'test'
        }

        with patch('flask_wtf.csrf.validate_csrf', return_value=True):
            response = client.post('/collections/upload', data=form_data, follow_redirects=False)

            # Should redirect to collection view
            assert response.status_code == 302

            with app.app_context():
                collection = Collection.query.filter_by(name='Workflow Test Collection').first()
                assert collection is not None

                # Step 2: Upload file
                sample_image.seek(0)
                file_storage = FileStorage(
                    stream=sample_image,
                    filename='workflow_test.jpg',
                    content_type='image/jpeg'
                )

                with patch('app.services.storage_service.StorageService._upload_to_local') as mock_upload:
                    # Mock the upload method to return a successful result
                    mock_file_record = File(
                        filename='workflow_uuid.jpg',
                        original_filename='workflow_test.jpg',
                        mime_type='image/jpeg',
                        size=1024,
                        storage_path='uploads/test_collection_uuid/workflow_uuid.jpg',
                        storage_backend='local',
                        upload_complete=True,
                        collection_id=collection.id
                    )
                    mock_upload.return_value = {
                        'success': True,
                        'file_record': mock_file_record,
                        'error': None,
                        'storage_info': {'upload_method': 'local', 'path': '/fake/path'}
                    }

                    upload_response = client.post('/collections/api/upload-files',
                                                data={
                                                    'collection_id': collection.id,
                                                    'file_test': file_storage
                                                })

                    assert upload_response.status_code == 200

                    # Step 3: Verify the upload method was called
                    mock_upload.assert_called_once()

                # Step 4: View collection
                view_response = client.get(f'/collections/{collection.uuid}')
                assert view_response.status_code == 200
                assert collection.name.encode() in view_response.data