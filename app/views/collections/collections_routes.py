"""
Routes for collection management including upload functionality.
"""

from flask import render_template, request, redirect, url_for, flash, jsonify, current_app, session, abort, send_file
from flask_login import login_required, current_user
from datetime import datetime, timedelta, timezone
import os

from app.views.collections import collections
from app.models import db, Collection, File, User
from app.forms import CollectionForm


@collections.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    """Display the collection upload page."""
    form = CollectionForm()

    if form.validate_on_submit():
        # Create new collection
        collection = Collection(
            name=form.name.data,
            description=form.description.data or None,
            privacy=form.privacy.data,
            user_id=current_user.id
        )

        # Handle password for protected collections
        if form.privacy.data == 'password' and form.password.data:
            collection.set_password(form.password.data)

        # Handle expiration
        if form.expiration.data:
            if form.expiration.data == '1_week':
                collection.expires_at = datetime.now(timezone.utc) + timedelta(weeks=1)
            elif form.expiration.data == '1_month':
                collection.expires_at = datetime.now(timezone.utc) + timedelta(days=30)
            elif form.expiration.data == '3_months':
                collection.expires_at = datetime.now(timezone.utc) + timedelta(days=90)
            elif form.expiration.data == '1_year':
                collection.expires_at = datetime.now(timezone.utc) + timedelta(days=365)

        try:
            db.session.add(collection)
            db.session.commit()
            flash('Collection created successfully!', 'success')

            # Return JSON response for AJAX requests
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': True, 'id': collection.id, 'uuid': collection.uuid})

            return redirect(url_for('collections.view', uuid=collection.uuid))
        except Exception as e:
            db.session.rollback()
            flash('Error creating collection. Please try again.', 'error')
            current_app.logger.error(f"Collection creation error: {str(e)}")

            # Return JSON error for AJAX requests
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'error': 'Error creating collection'});

    return render_template('collections/upload.html', form=form)


@collections.route('/api/validate-files', methods=['POST'])
@login_required
def validate_files():
    """API endpoint to validate uploaded files."""
    try:
        files = request.get_json().get('files', [])
        valid_files = []
        errors = []

        # File type validation
        ALLOWED_TYPES = [
            'image/jpeg', 'image/jpg', 'image/png',
            'image/heic', 'image/heif', 'image/tiff',
            'image/webp', 'image/x-adobe-dng'
        ]

        MAX_FILE_SIZE = current_app.config.get('MAX_FILE_SIZE', 50 * 1024 * 1024)
        MAX_TOTAL_SIZE = current_app.config.get('MAX_TOTAL_SIZE', 10 * 1024 * 1024 * 1024)
        MAX_BATCH_FILES = current_app.config.get('MAX_BATCH_FILES', 100)

        # Check file count limit
        if len(files) > MAX_BATCH_FILES:
            return jsonify({
                'success': False,
                'error': f'Too many files. Maximum {MAX_BATCH_FILES} files per batch.'
            }), 400

        total_size = 0

        for file_info in files:
            file_errors = []

            # Validate file type
            if file_info.get('type') not in ALLOWED_TYPES:
                file_errors.append('Unsupported file type. Use JPG, PNG, HEIC, TIFF, or RAW files.')

            # Validate file size
            file_size = file_info.get('size', 0)
            if file_size > MAX_FILE_SIZE:
                file_errors.append('File too large. Maximum size is 50MB per file.')

            total_size += file_size

            if file_errors:
                errors.append({
                    'filename': file_info.get('name', 'Unknown'),
                    'errors': file_errors
                })
            else:
                valid_files.append(file_info)

        # Check total size
        if total_size > MAX_TOTAL_SIZE:
            return jsonify({
                'success': False,
                'error': 'Total upload size too large. Maximum 10GB per collection.'
            }), 400

        if errors:
            return jsonify({
                'success': False,
                'errors': errors,
                'valid_files': valid_files
            }), 400

        return jsonify({
            'success': True,
            'valid_files': valid_files,
            'total_size': total_size
        })

    except Exception as e:
        current_app.logger.error(f"File validation error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Server error during file validation'
        }), 500


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

        from app.services.storage_service import StorageService
        storage_service = StorageService()
        uploaded_files = []
        upload_errors = []

        def progress_callback(file_key, bytes_uploaded, total_bytes):
            """Progress callback for individual file uploads."""
            # This could be extended to use WebSocket for real-time updates
            # Note: Logging removed to avoid Flask application context issues
            pass

        for file_key in request.files:
            file = request.files[file_key]
            if file and file.filename:
                try:
                    # Create progress callback for this specific file
                    file_progress = lambda uploaded, total: progress_callback(
                        file.filename, uploaded, total
                    )

                    # Reset file stream position
                    file.stream.seek(0)

                    current_app.logger.info(
                        f"Attempting upload: {file.filename}, size: {file.stream.seek(0, 2)}, backend: {storage_service.backend}"
                    )
                    file.stream.seek(0)

                    # Upload file using storage service
                    result = storage_service.upload_file(
                        file_obj=file.stream,
                        filename=file.filename,
                        collection=collection,
                        progress_callback=file_progress
                    )

                    current_app.logger.info(f"Upload result for {file.filename}: {result}")

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

        # Commit successful uploads to database
        if uploaded_files:
            try:
                db.session.commit()
                current_app.logger.info(
                    f"Uploaded {len(uploaded_files)} files to collection {collection_id}"
                )

                # Generate image variants after successful upload
                # Note: This is non-blocking and won't fail the upload if it errors
                try:
                    from app.services.thumbnail_service import ThumbnailService

                    # Get file records for uploaded files
                    file_records = [
                        File.query.filter_by(uuid=f['uuid']).first()
                        for f in uploaded_files
                    ]

                    # Filter to only image files
                    image_files = [f for f in file_records if f and f.is_image]

                    if image_files:
                        thumbnail_service = ThumbnailService()

                        # Generate all variants (thumb + medium) in batch
                        variant_results = thumbnail_service.batch_generate_variants(
                            image_files,
                            max_workers=3  # Limit concurrency for CPU-bound work
                        )

                        current_app.logger.info(
                            f"Variant generation: {variant_results['successful']}/{variant_results['total']} successful"
                        )
                except Exception as e:
                    # Don't fail the upload if variant generation fails
                    current_app.logger.error(f"Variant generation error: {str(e)}")

            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f"Database commit failed: {str(e)}")
                return jsonify({
                    'success': False,
                    'error': 'Database error: Could not save file records'
                }), 500

        # Determine overall success based on results
        total_files = len(uploaded_files) + len(upload_errors)
        overall_success = len(uploaded_files) > 0

        response_data = {
            'success': overall_success,
            'uploaded_files': uploaded_files,
            'errors': upload_errors,
            'summary': {
                'total_files': total_files,
                'successful': len(uploaded_files),
                'failed': len(upload_errors)
            }
        }

        # Add collection URL only if some files were uploaded
        if uploaded_files:
            response_data['collection_url'] = url_for('collections.view', uuid=collection.uuid)

        # Return appropriate status code
        if upload_errors and not uploaded_files:
            # All files failed
            return jsonify(response_data), 400
        elif upload_errors:
            # Partial failure
            return jsonify(response_data), 207  # Multi-Status
        else:
            # All files succeeded
            return jsonify(response_data), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"File upload error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Server error during upload'
        }), 500


@collections.route('/<uuid:uuid>')
def view(uuid):
    """View a collection."""
    collection = Collection.query.filter_by(uuid=str(uuid)).first_or_404()
    return render_template('collections/view.html', collection=collection)


@collections.route('/')
@login_required
def index():
    """List user's collections."""
    collections = Collection.query.filter_by(user_id=current_user.id).order_by(Collection.created_at.desc()).all()
    return render_template('collections/index.html', collections=collections)


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
        from app.services.storage_service import StorageService
        storage_service = StorageService()

        if storage_service.backend == 'r2' and storage_service.r2_storage:
            # Generate presigned URL for R2 files
            file_url = storage_service.generate_file_url(file_record, expiry_seconds=3600)
            # Redirect to presigned URL for direct R2 access
            # This reduces server load and provides better performance
            return redirect(file_url)
        else:
            # Serve local files directly
            file_path = os.path.join(current_app.instance_path, file_record.storage_path)
            if os.path.exists(file_path):
                return send_file(
                    file_path,
                    as_attachment=True,
                    download_name=file_record.original_filename,
                    mimetype=file_record.mime_type
                )
            else:
                abort(404)

    except Exception as e:
        current_app.logger.error(f"Failed to serve file {file_uuid}: {e}")
        abort(500)


@collections.route('/files/<uuid:file_uuid>/thumbnail')
def serve_thumbnail(file_uuid):
    """Serve small thumbnail for grid display."""
    file_record = File.query.filter_by(uuid=str(file_uuid)).first_or_404()

    # Check access permissions
    collection = file_record.collection

    if collection.privacy == 'password':
        session_key = f'collection_access_{collection.uuid}'
        if session_key not in session:
            return redirect(url_for('collections.password_required', uuid=collection.uuid))

    if collection.expires_at and collection.expires_at < datetime.now(timezone.utc):
        abort(410)

    # Try to serve thumb_path (new variant system) first
    variant_path = file_record.thumb_path or file_record.thumbnail_path

    if variant_path:
        try:
            from app.services.storage_service import StorageService
            storage_service = StorageService()

            if storage_service.backend == 'r2' and storage_service.r2_storage:
                thumbnail_url = storage_service.r2_storage.generate_presigned_url(
                    variant_path,
                    expiry_seconds=7200  # 2 hour cache for thumbnails
                )
                return redirect(thumbnail_url)
            else:
                # Serve local thumbnail
                thumbnail_path = os.path.join(current_app.instance_path, variant_path)
                if os.path.exists(thumbnail_path):
                    return send_file(
                        thumbnail_path,
                        mimetype='image/jpeg'
                    )
                else:
                    abort(404)

        except Exception as e:
            current_app.logger.error(f"Failed to serve thumbnail for {file_uuid}: {e}")
            abort(500)
    else:
        # Generate thumbnail on-demand if not exists
        return redirect(url_for('collections.generate_thumbnail', file_uuid=file_uuid))


@collections.route('/files/<uuid:file_uuid>/preview')
def serve_preview(file_uuid):
    """Serve medium-quality preview optimized for lightbox viewing."""
    file_record = File.query.filter_by(uuid=str(file_uuid)).first_or_404()

    # Check access permissions
    collection = file_record.collection

    if collection.privacy == 'password':
        session_key = f'collection_access_{collection.uuid}'
        if session_key not in session:
            return redirect(url_for('collections.password_required', uuid=collection.uuid))

    if collection.expires_at and collection.expires_at < datetime.now(timezone.utc):
        abort(410)

    # Serve medium variant if available
    if file_record.medium_path:
        try:
            from app.services.storage_service import StorageService
            storage_service = StorageService()

            if storage_service.backend == 'r2' and storage_service.r2_storage:
                preview_url = storage_service.r2_storage.generate_presigned_url(
                    file_record.medium_path,
                    expiry_seconds=7200  # 2 hour cache
                )
                return redirect(preview_url)
            else:
                # Serve local preview
                preview_path = os.path.join(current_app.instance_path, file_record.medium_path)
                if os.path.exists(preview_path):
                    return send_file(
                        preview_path,
                        mimetype='image/jpeg'
                    )

        except Exception as e:
            current_app.logger.error(f"Failed to serve preview for {file_uuid}: {e}")

    # Fallback: serve original file if preview not available
    return redirect(url_for('collections.serve_file', file_uuid=file_uuid))


@collections.route('/files/<uuid:file_uuid>/generate-thumbnail')
def generate_thumbnail(file_uuid):
    """Generate thumbnail for a file on-demand."""
    file_record = File.query.filter_by(uuid=str(file_uuid)).first_or_404()

    try:
        # Import thumbnail service (we'll create this next)
        from app.services.thumbnail_service import ThumbnailService
        thumbnail_service = ThumbnailService()

        thumbnail_path = thumbnail_service.generate_thumbnail(file_record)

        if thumbnail_path:
            # Update file record with thumbnail path
            file_record.thumbnail_path = thumbnail_path
            db.session.commit()

            # Redirect to serve the generated thumbnail
            return redirect(url_for('collections.serve_thumbnail', file_uuid=file_uuid))
        else:
            # Failed to generate thumbnail, serve placeholder or original file
            return redirect(url_for('collections.serve_file', file_uuid=file_uuid))

    except Exception as e:
        current_app.logger.error(f"Failed to generate thumbnail for {file_uuid}: {e}")
        return redirect(url_for('collections.serve_file', file_uuid=file_uuid))


@collections.route('/<uuid:uuid>/password', methods=['GET', 'POST'])
def password_required(uuid):
    """Handle password-protected collection access."""
    collection = Collection.query.filter_by(uuid=str(uuid)).first_or_404()

    if collection.privacy != 'password':
        return redirect(url_for('collections.view', uuid=uuid))

    if request.method == 'POST':
        password = request.form.get('password')
        if password and collection.check_password(password):
            session[f'collection_access_{collection.uuid}'] = True
            return redirect(url_for('collections.view', uuid=uuid))
        else:
            flash('Incorrect password. Please try again.', 'error')

    return render_template('collections/password.html', collection=collection)
