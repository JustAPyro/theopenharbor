"""
Routes for collection management including upload functionality.
"""

from flask import render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_login import login_required, current_user
from datetime import datetime, timedelta, timezone
import os
import uuid

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

        MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
        MAX_TOTAL_SIZE = 10 * 1024 * 1024 * 1024  # 10GB - more realistic for photo shoots
        # No arbitrary file count limit - let storage/bandwidth be the constraint

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
    """API endpoint to handle file uploads."""
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

        uploaded_files = []
        upload_errors = []

        for file_key in request.files:
            file = request.files[file_key]
            if file and file.filename:
                try:
                    # Generate unique filename
                    file_uuid = str(uuid.uuid4())
                    file_extension = os.path.splitext(file.filename)[1].lower()
                    storage_filename = f"{file_uuid}{file_extension}"

                    # For now, we'll simulate storage by saving to a local directory
                    # In production, this would upload to R2 storage
                    upload_dir = os.path.join(current_app.instance_path, 'uploads', str(collection.uuid))
                    os.makedirs(upload_dir, exist_ok=True)

                    storage_path = os.path.join(upload_dir, storage_filename)
                    file.save(storage_path)

                    # Create file record
                    file_record = File(
                        filename=storage_filename,
                        original_filename=file.filename,
                        mime_type=file.mimetype or 'application/octet-stream',
                        size=os.path.getsize(storage_path),
                        storage_path=f"uploads/{collection.uuid}/{storage_filename}",
                        upload_complete=True,
                        collection_id=collection.id
                    )

                    db.session.add(file_record)
                    uploaded_files.append({
                        'filename': file.filename,
                        'size': file_record.size,
                        'uuid': file_record.uuid
                    })

                except Exception as e:
                    upload_errors.append({
                        'filename': file.filename,
                        'error': str(e)
                    })

        if uploaded_files:
            db.session.commit()

        return jsonify({
            'success': True,
            'uploaded_files': uploaded_files,
            'errors': upload_errors
        })

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
