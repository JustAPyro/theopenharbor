/**
 * Collection Upload Page JavaScript
 * Handles drag-and-drop, file validation, thumbnails, and upload progress
 * The Open Harbor - Photographer-focused file sharing platform
 */

console.log('Upload.js file loaded successfully');

class CollectionUploader {
    constructor() {
        this.files = new Map(); // Map<fileId, FileObject>
        this.totalSize = 0;
        this.validFiles = 0;
        this.currentUpload = null;
        this.isUploading = false;

        // Configuration
        this.config = {
            maxFileSize: 50 * 1024 * 1024, // 50MB
            maxTotalSize: 10 * 1024 * 1024 * 1024, // 10GB - realistic for photo shoots
            maxFiles: null, // No arbitrary limit - let storage/bandwidth be the constraint
            allowedTypes: [
                'image/jpeg', 'image/jpg', 'image/png',
                'image/heic', 'image/heif', 'image/tiff',
                'image/webp', 'image/x-adobe-dng'
            ],
            thumbnailSize: 150,
            thumbnailQuality: 0.85,
            // Performance optimizations for large file sets
            batchSize: 50, // Process thumbnails in batches to prevent UI blocking
            maxConcurrentUploads: 5 // Increased from 3 for faster large uploads
        };

        // DOM elements
        this.elements = {
            uploadZone: document.getElementById('uploadZone'),
            fileInput: document.getElementById('fileInput'),
            browseButton: document.getElementById('browseButton'),
            filePreviewSection: document.getElementById('filePreviewSection'),
            filePreviewGrid: document.getElementById('filePreviewGrid'),
            fileCardTemplate: document.getElementById('fileCardTemplate'),
            clearAllButton: document.getElementById('clearAllButton'),
            collectionSettings: document.getElementById('collectionSettings'),
            collectionForm: document.getElementById('collectionForm'),
            actionButtons: document.getElementById('actionButtons'),
            startUploadButton: document.getElementById('startUploadButton'),
            cancelUploadButton: document.getElementById('cancelUploadButton'),
            uploadProgressSection: document.getElementById('uploadProgressSection'),
            uploadProgressBar: document.getElementById('uploadProgressBar'),
            progressText: document.getElementById('progressText'),
            progressPercent: document.getElementById('progressPercent'),
            uploadStatus: document.getElementById('uploadStatus'),
            errorAlert: document.getElementById('errorAlert'),
            errorMessage: document.getElementById('errorMessage'),
            successAlert: document.getElementById('successAlert'),
            successMessage: document.getElementById('successMessage'),
            fileCount: document.getElementById('fileCount'),
            totalSizeEl: document.getElementById('totalSize'),
            validFilesEl: document.getElementById('validFiles'),
            nameCounter: document.getElementById('nameCounter'),
            descriptionCounter: document.getElementById('descriptionCounter'),
            privacySelect: document.getElementById('privacySelect'),
            passwordField: document.getElementById('passwordField'),
            // Loading overlay elements
            loadingOverlay: document.getElementById('uploadLoadingOverlay'),
            loadingTitle: document.getElementById('loadingTitle'),
            loadingSubtitle: document.getElementById('loadingSubtitle'),
            loadingProgressFill: document.getElementById('loadingProgressFill'),
            loadingProgressText: document.getElementById('loadingProgressText'),
            loadingProgressPercent: document.getElementById('loadingProgressPercent'),
            loadingFilesCompleted: document.getElementById('loadingFilesCompleted'),
            loadingFilesTotal: document.getElementById('loadingFilesTotal'),
            loadingDataUploaded: document.getElementById('loadingDataUploaded'),
            loadingTimeRemaining: document.getElementById('loadingTimeRemaining'),
            currentFileName: document.getElementById('currentFileName')
        };

        this.init();
    }

    init() {
        console.log('CollectionUploader initializing...');
        console.log('Upload zone element:', this.elements.uploadZone);
        console.log('File input element:', this.elements.fileInput);

        this.setupEventListeners();
        this.setupFormValidation();
        this.hideAllSections();

        console.log('CollectionUploader initialized successfully');
    }

    setupEventListeners() {
        // Upload zone events
        this.elements.uploadZone.addEventListener('click', this.handleZoneClick.bind(this));
        this.elements.uploadZone.addEventListener('keydown', this.handleZoneKeydown.bind(this));
        this.elements.uploadZone.addEventListener('dragover', this.handleDragOver.bind(this));
        this.elements.uploadZone.addEventListener('dragleave', this.handleDragLeave.bind(this));
        this.elements.uploadZone.addEventListener('drop', this.handleDrop.bind(this));

        // Browse button
        this.elements.browseButton.addEventListener('click', (e) => {
            e.stopPropagation();
            this.elements.fileInput.click();
        });

        // File input
        this.elements.fileInput.addEventListener('change', this.handleFileSelect.bind(this));

        // Clear all button
        this.elements.clearAllButton.addEventListener('click', this.clearAllFiles.bind(this));

        // Upload buttons
        this.elements.startUploadButton.addEventListener('click', this.startUpload.bind(this));
        this.elements.cancelUploadButton.addEventListener('click', this.cancelUpload.bind(this));

        // Privacy select
        this.elements.privacySelect.addEventListener('change', this.handlePrivacyChange.bind(this));

        // Prevent default drag behaviors on document
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            document.addEventListener(eventName, (e) => {
                e.preventDefault();
                e.stopPropagation();
            });
        });

        // Global drag enter/leave for body highlighting
        document.addEventListener('dragenter', this.handleGlobalDragEnter.bind(this));
        document.addEventListener('dragleave', this.handleGlobalDragLeave.bind(this));
    }

    setupFormValidation() {
        // Character counters
        const nameField = document.querySelector('input[name="name"]');
        const descField = document.querySelector('textarea[name="description"]');

        if (nameField) {
            nameField.addEventListener('input', () => {
                this.updateCharacterCounter(nameField, this.elements.nameCounter, 100);
            });
        }

        if (descField) {
            descField.addEventListener('input', () => {
                this.updateCharacterCounter(descField, this.elements.descriptionCounter, 500);
            });
        }
    }

    hideAllSections() {
        this.elements.filePreviewSection.style.display = 'none';
        this.elements.collectionSettings.style.display = 'none';
        this.elements.uploadProgressSection.style.display = 'none';
        this.elements.actionButtons.style.display = 'none';
        this.elements.errorAlert.style.display = 'none';
        this.elements.successAlert.style.display = 'none';
    }

    // Event Handlers
    handleZoneClick(e) {
        if (e.target === this.elements.browseButton || this.elements.browseButton.contains(e.target)) {
            return; // Let the browse button handle its own click
        }
        this.elements.fileInput.click();
    }

    handleZoneKeydown(e) {
        if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            this.elements.fileInput.click();
        }
    }

    handleDragOver(e) {
        e.preventDefault();
        this.elements.uploadZone.classList.add('upload-zone--active');
    }

    handleDragLeave(e) {
        e.preventDefault();
        // Only remove active state if leaving the zone entirely
        if (!this.elements.uploadZone.contains(e.relatedTarget)) {
            this.elements.uploadZone.classList.remove('upload-zone--active');
        }
    }

    handleDrop(e) {
        e.preventDefault();
        this.elements.uploadZone.classList.remove('upload-zone--active');

        const files = Array.from(e.dataTransfer.files);
        this.processFiles(files);
    }

    handleGlobalDragEnter(e) {
        if (e.dataTransfer.types.includes('Files')) {
            document.body.classList.add('dragging-files');
        }
    }

    handleGlobalDragLeave(e) {
        // Check if we're leaving the document
        if (!e.relatedTarget || e.relatedTarget === document.documentElement) {
            document.body.classList.remove('dragging-files');
        }
    }

    handleFileSelect(e) {
        const files = Array.from(e.target.files);
        console.log('Files selected:', files.length, files.map(f => f.name));
        this.processFiles(files);
        // Clear the input for next selection
        e.target.value = '';
    }

    handlePrivacyChange(e) {
        const isPassword = e.target.value === 'password';
        this.elements.passwordField.style.display = isPassword ? 'block' : 'none';

        if (isPassword) {
            this.elements.passwordField.querySelector('input').setAttribute('required', '');
        } else {
            this.elements.passwordField.querySelector('input').removeAttribute('required');
        }
    }

    // File Processing
    async processFiles(files) {
        if (!files || files.length === 0) {
            console.log('No files to process');
            return;
        }

        console.log('Processing files:', files.length);
        this.hideErrors();

        // Show validation loading screen immediately for responsive feedback
        if (files.length > 10) {
            this.showValidationLoadingScreen(files.length);
        }

        // No arbitrary file count limit - photographers need flexibility

        const newFiles = [];

        for (const file of files) {
            const fileId = this.generateFileId();
            const fileObj = {
                id: fileId,
                file: file,
                name: file.name,
                size: file.size,
                type: file.type,
                lastModified: file.lastModified,
                status: 'pending', // pending, validating, valid, invalid, uploading, uploaded, error
                errors: [],
                thumbnail: null,
                progress: 0
            };

            newFiles.push(fileObj);
        }

        // Validate files in batches to prevent UI blocking
        await this.validateFilesBatched(newFiles);

        // Add valid files to collection
        for (const fileObj of newFiles) {
            if (fileObj.status === 'valid' || fileObj.status === 'pending') {
                this.files.set(fileObj.id, fileObj);
            }
        }

        // Update UI
        console.log('Files after validation:', this.files.size);

        // Hide validation loading screen if it was shown
        if (newFiles.length > 10) {
            this.hideLoadingOverlay();
        }

        // Reset upload title if we showed processing message
        const uploadTitle = this.elements.uploadZone.querySelector('.upload-title');
        if (uploadTitle) {
            uploadTitle.textContent = 'Drag photos here or click to browse';
        }

        this.updateFileCounts();
        this.renderFileCards();
        this.showRelevantSections();
    }

    async validateFile(fileObj) {
        console.log('Validating file:', fileObj.name, fileObj.type, fileObj.size);
        fileObj.status = 'validating';
        fileObj.errors = [];

        // Check file type
        if (!this.config.allowedTypes.includes(fileObj.type.toLowerCase())) {
            console.log('File type not allowed:', fileObj.type);
            fileObj.errors.push('Unsupported file type. Use JPG, PNG, HEIC, TIFF, or RAW files.');
        }

        // Check file size
        if (fileObj.size > this.config.maxFileSize) {
            fileObj.errors.push('File too large. Maximum size is 50MB per file.');
        }

        // Check total size
        const potentialTotalSize = this.totalSize + fileObj.size;
        if (potentialTotalSize > this.config.maxTotalSize) {
            fileObj.errors.push('Total upload size would exceed 10GB limit.');
        }

        // Check for duplicates (by name and size)
        const isDuplicate = Array.from(this.files.values()).some(existing =>
            existing.name === fileObj.name && existing.size === fileObj.size
        );

        if (isDuplicate) {
            fileObj.errors.push('Duplicate file detected.');
        }

        // Generate thumbnail for valid image files
        if (fileObj.errors.length === 0) {
            try {
                fileObj.thumbnail = await this.generateThumbnail(fileObj.file);
                fileObj.status = 'valid';
            } catch (error) {
                console.warn('Thumbnail generation failed:', error);
                fileObj.status = 'valid'; // Still valid even without thumbnail
            }
        } else {
            fileObj.status = 'invalid';
        }

        console.log('File validation complete:', fileObj.name, 'status:', fileObj.status, 'errors:', fileObj.errors);
    }

    async validateFilesBatched(files) {
        const batchSize = this.config.batchSize;

        for (let i = 0; i < files.length; i += batchSize) {
            const batch = files.slice(i, i + batchSize);

            // Process batch concurrently
            await Promise.all(batch.map(fileObj => this.validateFile(fileObj)));

            // Yield control to prevent UI blocking
            await new Promise(resolve => setTimeout(resolve, 0));

            // Show progress for any upload with loading screen
            if (files.length > 10) {
                const processed = Math.min(i + batchSize, files.length);
                console.log(`Processed ${processed} of ${files.length} files...`);

                // Update validation progress on loading screen
                this.updateValidationProgress(processed, files.length);
            }
        }
    }

    showValidationProgress(processed, total) {
        // For large file sets, show validation progress
        const percent = (processed / total) * 100;

        // You could add a validation progress indicator here
        // For now, just update the upload zone with progress info
        const uploadTitle = this.elements.uploadZone.querySelector('.upload-title');
        if (uploadTitle && total > 100) {
            uploadTitle.textContent = `Processing ${processed} of ${total} files...`;
        }
    }

    async generateThumbnail(file) {
        return new Promise((resolve, reject) => {
            const canvas = document.createElement('canvas');
            const ctx = canvas.getContext('2d');
            const img = new Image();

            img.onload = () => {
                const { width, height } = img;
                const size = this.config.thumbnailSize;

                // Calculate dimensions maintaining aspect ratio
                let drawWidth, drawHeight;
                if (width > height) {
                    drawWidth = size;
                    drawHeight = (height / width) * size;
                } else {
                    drawHeight = size;
                    drawWidth = (width / height) * size;
                }

                canvas.width = size;
                canvas.height = size;

                // Fill background
                ctx.fillStyle = '#F9F7F3';
                ctx.fillRect(0, 0, size, size);

                // Center the image
                const x = (size - drawWidth) / 2;
                const y = (size - drawHeight) / 2;

                ctx.drawImage(img, x, y, drawWidth, drawHeight);

                // Convert to blob
                canvas.toBlob(resolve, 'image/jpeg', this.config.thumbnailQuality);
            };

            img.onerror = reject;

            // Create object URL for the image
            const url = URL.createObjectURL(file);
            img.src = url;

            // Clean up URL after load or error
            img.addEventListener('load', () => URL.revokeObjectURL(url));
            img.addEventListener('error', () => URL.revokeObjectURL(url));
        });
    }

    // UI Updates
    updateFileCounts() {
        const totalFiles = this.files.size;
        this.validFiles = Array.from(this.files.values()).filter(f => f.status === 'valid').length;
        this.totalSize = Array.from(this.files.values())
            .filter(f => f.status === 'valid')
            .reduce((sum, f) => sum + f.size, 0);

        this.elements.fileCount.textContent = totalFiles;
        this.elements.validFilesEl.textContent = this.validFiles;
        this.elements.totalSizeEl.textContent = this.formatFileSize(this.totalSize);

        // Update upload button state
        this.elements.startUploadButton.disabled = this.validFiles === 0 || this.isUploading;
    }

    renderFileCards() {
        // Clear existing cards
        this.elements.filePreviewGrid.innerHTML = '';

        // Sort files by status (valid first) then by name
        const sortedFiles = Array.from(this.files.values()).sort((a, b) => {
            if (a.status === 'valid' && b.status !== 'valid') return -1;
            if (a.status !== 'valid' && b.status === 'valid') return 1;
            return a.name.localeCompare(b.name);
        });

        for (const fileObj of sortedFiles) {
            this.createFileCard(fileObj);
        }
    }

    createFileCard(fileObj) {
        const template = this.elements.fileCardTemplate;
        const card = template.content.cloneNode(true);
        const cardElement = card.querySelector('.file-card');

        // Set data attributes
        cardElement.dataset.fileId = fileObj.id;

        // Set file info
        card.querySelector('.file-name').textContent = fileObj.name;
        card.querySelector('.file-size').textContent = this.formatFileSize(fileObj.size);

        // Set thumbnail
        const img = card.querySelector('.thumbnail-img');
        if (fileObj.thumbnail) {
            const url = URL.createObjectURL(fileObj.thumbnail);
            img.src = url;
            img.alt = `Thumbnail of ${fileObj.name}`;

            // Clean up URL when card is removed
            cardElement.addEventListener('removed', () => URL.revokeObjectURL(url));
        } else {
            // Use a default icon or placeholder
            img.src = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNDgiIGhlaWdodD0iNDgiIGZpbGw9IiNBM0M5RTIiIHZpZXdCb3g9IjAgMCAyNCAyNCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cGF0aCBkPSJtNC41IDloM3YtM2gtM3ptNC41IDBoM3YtM2gtM3ptNC41IDBoM3YtM2gtM3ptLTkgNGgzdi0zaDNzbTQuNSAwaDN2LTNoLTN6bTQuNSAwaDN2LTNoLTN6bS05IDRoM3YtM2gtM3ptNC41IDBoM3YtM2gtM3ptNC41IDBoM3YtM2gtM3oiLz48L3N2Zz4=';
            img.alt = `File icon for ${fileObj.name}`;
        }

        // Set card status
        this.updateCardStatus(cardElement, fileObj);

        // Set up remove button
        const removeBtn = card.querySelector('.file-remove');
        removeBtn.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            this.removeFile(fileObj.id);
        });

        removeBtn.setAttribute('aria-label', `Remove ${fileObj.name}`);
        removeBtn.setAttribute('title', `Remove ${fileObj.name}`);

        // Add to grid
        this.elements.filePreviewGrid.appendChild(card);
    }

    updateCardStatus(cardElement, fileObj) {
        // cardElement should be the .file-card element itself
        const card = cardElement.classList.contains('file-card') ? cardElement : cardElement.querySelector('.file-card');

        if (!card) {
            console.error('Card element not found for file:', fileObj.name);
            return;
        }

        const statusIcons = card.querySelectorAll('.file-status i, .file-status .spinner-border');

        // Hide all status icons
        statusIcons.forEach(icon => icon.style.display = 'none');

        // Remove status classes
        card.classList.remove('file-card--error', 'file-card--success', 'file-card--uploading');

        // Set appropriate status
        const checkIcon = card.querySelector('.bi-check-circle');
        const errorIcon = card.querySelector('.bi-exclamation-triangle');
        const spinner = card.querySelector('.spinner-border');

        switch (fileObj.status) {
            case 'valid':
                card.classList.add('file-card--success');
                if (checkIcon) checkIcon.style.display = 'inline';
                break;
            case 'invalid':
                card.classList.add('file-card--error');
                if (errorIcon) errorIcon.style.display = 'inline';
                // Add title with error messages
                card.title = fileObj.errors.join(', ');
                break;
            case 'uploading':
                card.classList.add('file-card--uploading');
                if (spinner) spinner.style.display = 'inline';
                break;
            case 'uploaded':
                card.classList.add('file-card--success');
                if (checkIcon) checkIcon.style.display = 'inline';
                break;
            case 'error':
                card.classList.add('file-card--error');
                if (errorIcon) errorIcon.style.display = 'inline';
                card.title = fileObj.errors.join(', ');
                break;
        }

        // Update progress bar
        const progressBar = card.querySelector('.file-progress-bar');
        if (fileObj.progress > 0) {
            card.querySelector('.file-progress').style.display = 'block';
            progressBar.style.width = `${fileObj.progress}%`;
        } else {
            card.querySelector('.file-progress').style.display = 'none';
        }
    }

    showRelevantSections() {
        console.log('showRelevantSections called, files.size:', this.files.size);
        if (this.files.size > 0) {
            console.log('Showing sections...');
            this.elements.filePreviewSection.style.display = 'block';
            this.elements.collectionSettings.style.display = 'block';
            this.elements.actionButtons.style.display = 'block';
        }
    }

    removeFile(fileId) {
        const fileObj = this.files.get(fileId);
        if (!fileObj) return;

        // Remove from files map
        this.files.delete(fileId);

        // Remove card from DOM
        const cardElement = document.querySelector(`[data-file-id="${fileId}"]`);
        if (cardElement) {
            // Trigger cleanup event
            cardElement.dispatchEvent(new CustomEvent('removed'));
            cardElement.remove();
        }

        // Update counts
        this.updateFileCounts();

        // Hide sections if no files
        if (this.files.size === 0) {
            this.hideAllSections();
        }

        this.announceToScreenReader(`Removed ${fileObj.name}`);
    }

    clearAllFiles() {
        // Clean up thumbnails
        this.files.forEach(fileObj => {
            const cardElement = document.querySelector(`[data-file-id="${fileObj.id}"]`);
            if (cardElement) {
                cardElement.dispatchEvent(new CustomEvent('removed'));
            }
        });

        this.files.clear();
        this.updateFileCounts();
        this.hideAllSections();
        this.announceToScreenReader('All files cleared');
    }

    // Upload Logic
    async startUpload() {
        if (this.validFiles === 0 || this.isUploading) return;

        // Validate collection form
        const formData = new FormData(this.elements.collectionForm);
        const collectionName = formData.get('name');

        if (!collectionName || collectionName.trim().length === 0) {
            this.showError('Collection name is required');
            this.elements.collectionForm.querySelector('input[name="name"]').focus();
            return;
        }

        // Check privacy/password validation
        const privacy = formData.get('privacy');
        const password = formData.get('password');

        if (privacy === 'password' && (!password || password.trim().length < 4)) {
            this.showError('Password is required and must be at least 4 characters long');
            this.elements.collectionForm.querySelector('input[name="password"]').focus();
            return;
        }

        this.isUploading = true;
        this.elements.startUploadButton.disabled = true;
        this.elements.cancelUploadButton.style.display = 'inline-block';
        this.elements.uploadProgressSection.style.display = 'block';

        // Show loading overlay
        this.showLoadingOverlay(this.validFiles);

        try {
            // First, create the collection
            const collectionResponse = await this.createCollection(formData);

            if (!collectionResponse.ok) {
                throw new Error('Failed to create collection');
            }

            const collection = await collectionResponse.json();

            // Then upload files
            await this.uploadFiles(collection.id);

            // Hide loading overlay and show success
            this.hideLoadingOverlay();
            this.showSuccess(`Collection "${collectionName}" created successfully with ${this.validFiles} files!`);

            // Redirect after a short delay
            setTimeout(() => {
                window.location.href = `/collections/${collection.uuid}`;
            }, 2000);

        } catch (error) {
            console.error('Upload failed:', error);
            this.hideLoadingOverlay();
            this.showError('Upload failed. Please try again.');
            this.resetUploadState();
        }
    }

    async createCollection(formData) {
        const url = this.elements.collectionForm.action || '/collections/upload';
        console.log('Creating collection with URL:', url);

        const response = await fetch(url, {
            method: 'POST',
            body: formData,
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        });

        console.log('Collection creation response:', response.status, response.statusText);
        return response;
    }

    async uploadFiles(collectionId) {
        const validFiles = Array.from(this.files.values()).filter(f => f.status === 'valid');
        const totalFiles = validFiles.length;
        let completedFiles = 0;

        this.updateProgress(0, `Uploading files...`);

        // Upload files in parallel (increased for large photo sets)
        const concurrentUploads = this.config.maxConcurrentUploads;
        const uploadPromises = [];

        for (let i = 0; i < validFiles.length; i += concurrentUploads) {
            const batch = validFiles.slice(i, i + concurrentUploads);

            const batchPromises = batch.map(async (fileObj) => {
                try {
                    fileObj.status = 'uploading';
                    this.updateFileCardStatus(fileObj);

                    // Update loading screen with current file
                    this.updateLoadingProgress(completedFiles, totalFiles, fileObj.name);

                    const uploadFormData = new FormData();
                    uploadFormData.append('collection_id', collectionId);
                    uploadFormData.append(`file_${fileObj.id}`, fileObj.file, fileObj.name);

                    const response = await fetch('/collections/api/upload-files', {
                        method: 'POST',
                        body: uploadFormData
                    });

                    if (!response.ok) {
                        throw new Error(`Upload failed: ${response.statusText}`);
                    }

                    const result = await response.json();

                    if (result.success) {
                        fileObj.status = 'uploaded';
                        fileObj.progress = 100;
                        this.uploadedBytes += fileObj.size;
                        this.addStatusMessage(`✓ ${fileObj.name} uploaded successfully`, 'success');
                    } else {
                        throw new Error(result.error || 'Upload failed');
                    }

                } catch (error) {
                    fileObj.status = 'error';
                    fileObj.errors = [error.message];
                    this.addStatusMessage(`✗ ${fileObj.name} failed: ${error.message}`, 'error');
                }

                completedFiles++;
                const progress = (completedFiles / totalFiles) * 100;
                this.updateProgress(progress, `Uploaded ${completedFiles} of ${totalFiles} files`);
                this.updateLoadingProgress(completedFiles, totalFiles);
                this.updateFileCardStatus(fileObj);
            });

            uploadPromises.push(...batchPromises);

            // Wait for this batch to complete before starting the next
            await Promise.all(batchPromises);
        }

        await Promise.all(uploadPromises);
    }

    cancelUpload() {
        if (this.currentUpload) {
            this.currentUpload.abort();
        }

        this.resetUploadState();
        this.addStatusMessage('Upload cancelled by user', 'info');
    }

    resetUploadState() {
        this.isUploading = false;
        this.currentUpload = null;
        this.elements.startUploadButton.disabled = this.validFiles === 0;
        this.elements.cancelUploadButton.style.display = 'none';

        // Update button text
        this.elements.startUploadButton.querySelector('.button-text').textContent = 'Start Upload';
    }

    // Progress Updates
    updateProgress(percent, text) {
        this.elements.uploadProgressBar.style.width = `${percent}%`;
        this.elements.progressPercent.textContent = `${Math.round(percent)}%`;
        this.elements.progressText.textContent = text;

        // Update ARIA attributes
        const progressElement = this.elements.uploadProgressSection.querySelector('[role="progressbar"]');
        progressElement.setAttribute('aria-valuenow', Math.round(percent));

        this.announceToScreenReader(text, 'polite');
    }

    updateFileCardStatus(fileObj) {
        const cardElement = document.querySelector(`[data-file-id="${fileObj.id}"]`);
        if (cardElement) {
            this.updateCardStatus(cardElement, fileObj);
        }
    }

    addStatusMessage(message, type) {
        const statusItem = document.createElement('div');
        statusItem.className = `status-item status-item--${type}`;
        statusItem.innerHTML = `
            <i class="bi bi-${this.getStatusIcon(type)}" aria-hidden="true"></i>
            <span>${message}</span>
        `;

        this.elements.uploadStatus.appendChild(statusItem);
        this.elements.uploadStatus.scrollTop = this.elements.uploadStatus.scrollHeight;
    }

    getStatusIcon(type) {
        const icons = {
            success: 'check-circle',
            error: 'exclamation-triangle',
            info: 'info-circle'
        };
        return icons[type] || 'info-circle';
    }

    // Utility Functions
    generateFileId() {
        return `file_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }

    formatFileSize(bytes) {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
    }

    updateCharacterCounter(input, counterElement, maxLength) {
        const currentLength = input.value.length;
        counterElement.textContent = currentLength;

        // Update counter styling
        counterElement.classList.remove('character-counter--warning', 'character-counter--error');

        if (currentLength > maxLength * 0.8) {
            counterElement.classList.add('character-counter--warning');
        }
        if (currentLength > maxLength) {
            counterElement.classList.add('character-counter--error');
        }
    }

    showError(message) {
        this.elements.errorMessage.textContent = message;
        this.elements.errorAlert.style.display = 'block';
        this.elements.successAlert.style.display = 'none';
        this.elements.errorAlert.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        this.announceToScreenReader(`Error: ${message}`, 'assertive');
    }

    showSuccess(message) {
        this.elements.successMessage.textContent = message;
        this.elements.successAlert.style.display = 'block';
        this.elements.errorAlert.style.display = 'none';
        this.elements.successAlert.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        this.announceToScreenReader(`Success: ${message}`, 'polite');
    }

    hideErrors() {
        this.elements.errorAlert.style.display = 'none';
        this.elements.successAlert.style.display = 'none';
    }

    announceToScreenReader(message, priority = 'polite') {
        const announcer = document.createElement('div');
        announcer.setAttribute('aria-live', priority);
        announcer.setAttribute('aria-atomic', 'true');
        announcer.className = 'sr-only';
        announcer.textContent = message;

        document.body.appendChild(announcer);

        // Remove after announcement
        setTimeout(() => {
            document.body.removeChild(announcer);
        }, 1000);
    }

    // Validation Loading Screen Methods
    showValidationLoadingScreen(totalFiles) {
        // Show overlay immediately with validation-specific content
        this.elements.loadingTitle.textContent = 'Processing Your Photos';
        this.elements.loadingSubtitle.textContent = 'Validating files and generating thumbnails...';

        // Set initial values for validation
        this.elements.loadingFilesCompleted.textContent = '0';
        this.elements.loadingFilesTotal.textContent = totalFiles;
        this.elements.loadingDataUploaded.textContent = '0 files';
        this.elements.loadingTimeRemaining.textContent = '--';
        this.elements.currentFileName.textContent = 'Starting validation...';

        // Reset progress
        this.elements.loadingProgressFill.style.width = '0%';
        this.elements.loadingProgressText.textContent = 'Processing files...';
        this.elements.loadingProgressPercent.textContent = '0%';

        // Show overlay immediately
        this.elements.loadingOverlay.style.display = 'flex';
        document.body.classList.add('upload-in-progress');

        // Announce to screen readers
        this.announceToScreenReader(`Processing ${totalFiles} files. Please wait...`, 'assertive');
    }

    updateValidationProgress(processed, total) {
        const percent = total > 0 ? (processed / total) * 100 : 0;

        // Update progress bar
        this.elements.loadingProgressFill.style.width = `${percent}%`;
        this.elements.loadingProgressPercent.textContent = `${Math.round(percent)}%`;

        // Update file count
        this.elements.loadingFilesCompleted.textContent = processed;
        this.elements.loadingDataUploaded.textContent = `${processed} files`;

        // Update progress text
        if (processed === total) {
            this.elements.loadingProgressText.textContent = 'Validation complete!';
            this.elements.currentFileName.textContent = 'Preparing interface...';
        } else {
            this.elements.loadingProgressText.textContent = `Processing ${processed} of ${total} files`;
            this.elements.currentFileName.textContent = 'Validating files and creating thumbnails...';
        }
    }

    // Upload Loading Screen Methods
    showLoadingOverlay(totalFiles) {
        // Switch to upload mode
        this.elements.loadingTitle.textContent = 'Uploading Your Photos';
        this.elements.loadingSubtitle.textContent = 'Please don\'t close this window while your files are uploading';

        // Initialize upload-specific stats
        this.uploadStartTime = Date.now();
        this.totalUploadBytes = Array.from(this.files.values())
            .filter(f => f.status === 'valid')
            .reduce((sum, f) => sum + f.size, 0);
        this.uploadedBytes = 0;

        // Set initial values for upload
        this.elements.loadingFilesCompleted.textContent = '0';
        this.elements.loadingFilesTotal.textContent = totalFiles;
        this.elements.loadingDataUploaded.textContent = '0 MB';
        this.elements.loadingTimeRemaining.textContent = '--';
        this.elements.currentFileName.textContent = '--';

        // Reset progress
        this.elements.loadingProgressFill.style.width = '0%';
        this.elements.loadingProgressText.textContent = 'Preparing upload...';
        this.elements.loadingProgressPercent.textContent = '0%';

        // Show overlay if not already shown
        if (this.elements.loadingOverlay.style.display !== 'flex') {
            this.elements.loadingOverlay.style.display = 'flex';
            document.body.classList.add('upload-in-progress');
        }

        // Announce to screen readers
        this.announceToScreenReader('Upload started. Please wait while your files are being uploaded.', 'assertive');
    }

    hideLoadingOverlay() {
        // Hide overlay
        this.elements.loadingOverlay.style.display = 'none';
        document.body.classList.remove('upload-in-progress');
    }

    updateLoadingProgress(completedFiles, totalFiles, currentFileName = null) {
        const percent = totalFiles > 0 ? (completedFiles / totalFiles) * 100 : 0;

        // Update progress bar
        this.elements.loadingProgressFill.style.width = `${percent}%`;
        this.elements.loadingProgressPercent.textContent = `${Math.round(percent)}%`;

        // Update file count
        this.elements.loadingFilesCompleted.textContent = completedFiles;

        // Update data uploaded
        this.elements.loadingDataUploaded.textContent = this.formatFileSize(this.uploadedBytes);

        // Update current file
        if (currentFileName) {
            this.elements.currentFileName.textContent = currentFileName;
        }

        // Calculate time remaining
        if (completedFiles > 0 && this.uploadStartTime) {
            const elapsed = (Date.now() - this.uploadStartTime) / 1000; // seconds
            const rate = completedFiles / elapsed; // files per second
            const remaining = Math.max(0, totalFiles - completedFiles);
            const timeRemaining = remaining / rate;

            if (timeRemaining > 60) {
                this.elements.loadingTimeRemaining.textContent = `${Math.round(timeRemaining / 60)}m`;
            } else {
                this.elements.loadingTimeRemaining.textContent = `${Math.round(timeRemaining)}s`;
            }
        }

        // Update progress text
        if (completedFiles === totalFiles) {
            this.elements.loadingProgressText.textContent = 'Upload complete!';
            this.elements.currentFileName.textContent = 'Finalizing collection...';
        } else {
            this.elements.loadingProgressText.textContent = `Uploading ${completedFiles} of ${totalFiles} files`;
        }
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.collectionUploader = new CollectionUploader();
});

// Handle page unload
window.addEventListener('beforeunload', (e) => {
    if (window.collectionUploader && window.collectionUploader.isUploading) {
        e.preventDefault();
        e.returnValue = 'Upload in progress. Are you sure you want to leave?';
        return e.returnValue;
    }
});