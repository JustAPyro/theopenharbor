/**
 * LIGHTBOX MODAL VIEWER
 *
 * Purpose: Full-screen image viewer with keyboard/touch navigation
 * Dependencies: None (vanilla JavaScript)
 * Browser Support: Modern browsers (ES6+)
 *
 * Features:
 * - Click thumbnail to open full-size image
 * - Navigate with arrow keys or prev/next buttons
 * - Swipe on mobile to navigate
 * - Escape key or click backdrop to close
 * - Focus trapping for accessibility
 * - Loading states with spinner
 * - Image metadata display
 */

// =============================================================================
// STATE MANAGEMENT
// =============================================================================

const LightboxState = {
  isOpen: false,
  currentIndex: 0,
  files: [],
  currentFile: null,
  isLoading: false,
  keyboardHandler: null,
  touchStartX: 0,
  touchEndX: 0,
  focusableElements: [],
  firstFocusable: null,
  lastFocusable: null,
  previousFocus: null,
  scrollbarWidth: 0,
  imageCache: new Map(), // Cache loaded images
  preloadCache: new Set() // Track preloaded images
};

// =============================================================================
// DOM ELEMENT REFERENCES
// =============================================================================

const DOM = {
  lightbox: null,
  backdrop: null,
  closeBtn: null,
  prevBtn: null,
  nextBtn: null,
  image: null,
  loader: null,
  counter: null,
  title: null,
  size: null,
  dimensions: null,
  downloadBtn: null,
  statusRegion: null
};

// =============================================================================
// INITIALIZATION
// =============================================================================

function initLightbox() {
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initLightbox);
    return;
  }

  // Cache DOM references
  DOM.lightbox = document.getElementById('lightbox');
  DOM.backdrop = DOM.lightbox?.querySelector('.lightbox-backdrop');
  DOM.closeBtn = DOM.lightbox?.querySelector('.lightbox-close');
  DOM.prevBtn = DOM.lightbox?.querySelector('.lightbox-prev');
  DOM.nextBtn = DOM.lightbox?.querySelector('.lightbox-next');
  DOM.image = document.getElementById('lightbox-image');
  DOM.loader = DOM.lightbox?.querySelector('.lightbox-loader');
  DOM.counter = document.getElementById('lightbox-counter');
  DOM.title = document.getElementById('lightbox-title');
  DOM.size = document.getElementById('lightbox-size');
  DOM.dimensions = document.getElementById('lightbox-dimensions');
  DOM.downloadBtn = document.getElementById('lightbox-download');
  DOM.statusRegion = document.getElementById('lightbox-status');

  if (!DOM.lightbox || !DOM.image) {
    console.error('Lightbox: Required DOM elements not found');
    return;
  }

  // Calculate scrollbar width
  LightboxState.scrollbarWidth = calculateScrollbarWidth();

  // Build file list
  buildFileList();

  // Attach event listeners
  attachEventListeners();

  console.log('Lightbox initialized with', LightboxState.files.length, 'images');
}

function calculateScrollbarWidth() {
  const outer = document.createElement('div');
  outer.style.visibility = 'hidden';
  outer.style.overflow = 'scroll';
  outer.style.width = '100px';
  document.body.appendChild(outer);

  const inner = document.createElement('div');
  inner.style.width = '100%';
  outer.appendChild(inner);

  const scrollbarWidth = outer.offsetWidth - inner.offsetWidth;
  document.body.removeChild(outer);

  return scrollbarWidth;
}

function buildFileList() {
  const galleryItems = document.querySelectorAll('.gallery-item');

  LightboxState.files = Array.from(galleryItems).map((item, index) => ({
    index: index,
    uuid: item.dataset.fileUuid,
    name: item.dataset.fileName,
    size: item.dataset.fileSize,
    url: item.dataset.fullUrl,
    previewUrl: item.dataset.previewUrl || item.dataset.fullUrl, // Medium preview or fallback to full
    thumbnail: item.querySelector('img')?.src || ''
  }));
}

function attachEventListeners() {
  // Thumbnail clicks
  document.querySelectorAll('.gallery-thumbnail').forEach(thumbnail => {
    thumbnail.addEventListener('click', handleThumbnailClick);
    thumbnail.addEventListener('keydown', handleThumbnailKeydown);
  });

  // Lightbox trigger buttons
  document.querySelectorAll('.lightbox-trigger').forEach(trigger => {
    trigger.addEventListener('click', handleTriggerClick);
  });

  // Close button and backdrop
  DOM.closeBtn?.addEventListener('click', closeLightbox);
  DOM.backdrop?.addEventListener('click', closeLightbox);

  // Navigation buttons
  DOM.prevBtn?.addEventListener('click', showPreviousImage);
  DOM.nextBtn?.addEventListener('click', showNextImage);

  // Image events
  DOM.image?.addEventListener('load', handleImageLoad);
  DOM.image?.addEventListener('error', handleImageError);

  // Touch gestures
  DOM.lightbox?.addEventListener('touchstart', handleTouchStart, { passive: true });
  DOM.lightbox?.addEventListener('touchend', handleTouchEnd, { passive: true });
}

// =============================================================================
// OPEN/CLOSE LIGHTBOX
// =============================================================================

function openLightbox(index) {
  if (index < 0 || index >= LightboxState.files.length) {
    console.error('Lightbox: Invalid index', index);
    return;
  }

  LightboxState.isOpen = true;
  LightboxState.currentIndex = index;
  LightboxState.currentFile = LightboxState.files[index];

  // Store current focus
  LightboxState.previousFocus = document.activeElement;

  // Prevent body scroll
  document.body.classList.add('lightbox-open');
  document.body.style.setProperty('--scrollbar-width', `${LightboxState.scrollbarWidth}px`);

  // Show lightbox
  DOM.lightbox.classList.add('active');
  DOM.lightbox.setAttribute('aria-hidden', 'false');

  // Load image
  loadImage(LightboxState.currentFile);

  // Update UI
  updateLightboxUI();

  // Attach keyboard listener
  attachKeyboardListener();

  // Setup focus trap
  setupFocusTrap();

  // Focus close button
  DOM.closeBtn?.focus();

  // Announce to screen readers
  announceToScreenReader(`Opened lightbox. Image ${index + 1} of ${LightboxState.files.length}`);
}

function closeLightbox() {
  LightboxState.isOpen = false;

  // Hide lightbox
  DOM.lightbox.classList.remove('active');
  DOM.lightbox.setAttribute('aria-hidden', 'true');

  // Re-enable body scroll
  document.body.classList.remove('lightbox-open');
  document.body.style.removeProperty('--scrollbar-width');

  // Clear image
  DOM.image.src = '';
  DOM.image.style.display = 'none';

  // Remove keyboard listener
  detachKeyboardListener();

  // Restore focus
  if (LightboxState.previousFocus) {
    LightboxState.previousFocus.focus();
    LightboxState.previousFocus = null;
  }

  announceToScreenReader('Closed lightbox. Returned to gallery.');
}

// =============================================================================
// IMAGE LOADING
// =============================================================================

/**
 * Load image with progressive loading strategy:
 * 1. Show thumbnail immediately (instant)
 * 2. Load medium preview for lightbox viewing (fast, ~200KB)
 * 3. Optionally cache full-size for download
 * 4. Preload adjacent images for faster navigation
 */
function loadImage(file) {
  if (!file?.previewUrl && !file?.url) {
    console.error('Lightbox: Invalid file object', file);
    return;
  }

  LightboxState.isLoading = true;

  // Show loader
  DOM.loader?.classList.add('active');

  // STEP 1: Show thumbnail immediately for instant feedback
  if (file.thumbnail) {
    DOM.image.src = file.thumbnail;
    DOM.image.alt = file.name;
    DOM.image.style.display = 'block';
    DOM.image.classList.add('loaded');
    // Add a class to indicate this is thumbnail quality
    DOM.image.classList.add('thumbnail-quality');
  } else {
    DOM.image.style.display = 'none';
    DOM.image.classList.remove('loaded');
  }

  // Update download button with original full-quality URL
  if (DOM.downloadBtn) {
    DOM.downloadBtn.href = file.url;
    DOM.downloadBtn.download = file.name;
  }

  announceToScreenReader(`Loading ${file.name}`);

  // STEP 2: Load medium-quality preview for lightbox display
  loadPreviewImage(file);
}

/**
 * Load medium-quality preview and swap when ready
 */
function loadPreviewImage(file) {
  const previewUrl = file.previewUrl || file.url;

  // Check if already cached
  if (LightboxState.imageCache.has(previewUrl)) {
    const cachedImg = LightboxState.imageCache.get(previewUrl);
    swapToFullImage(cachedImg, file);
    return;
  }

  // Create new image element to load preview in background
  const previewImg = new Image();

  previewImg.onload = () => {
    // Cache the loaded preview
    LightboxState.imageCache.set(previewUrl, previewImg);

    // Only swap if we're still viewing this image
    if (LightboxState.currentFile?.previewUrl === file.previewUrl) {
      swapToFullImage(previewImg, file);
    }

    // Preload adjacent images for faster navigation
    preloadAdjacentImages();
  };

  previewImg.onerror = () => {
    // Only show error if we're still viewing this image
    if (LightboxState.currentFile?.previewUrl === file.previewUrl) {
      handleImageError(file);
    }
  };

  // Start loading preview image
  previewImg.src = previewUrl;
}

/**
 * Swap from thumbnail to full-size image
 */
function swapToFullImage(fullImg, file) {
  LightboxState.isLoading = false;

  // Hide loader
  DOM.loader?.classList.remove('active');

  // Swap to full-size image
  DOM.image.src = fullImg.src;
  DOM.image.classList.remove('thumbnail-quality');
  DOM.image.classList.add('loaded');
  DOM.image.style.display = 'block';

  // Get dimensions from full image
  const width = fullImg.naturalWidth;
  const height = fullImg.naturalHeight;

  if (DOM.dimensions && width && height) {
    DOM.dimensions.textContent = `${width} × ${height}`;
  }

  announceToScreenReader(`Image loaded: ${file.name}`);
}

/**
 * Preload adjacent images for instant navigation
 */
function preloadAdjacentImages() {
  const currentIdx = LightboxState.currentIndex;
  const files = LightboxState.files;

  // Preload next image
  if (currentIdx < files.length - 1) {
    preloadImage(files[currentIdx + 1]);
  }

  // Preload previous image
  if (currentIdx > 0) {
    preloadImage(files[currentIdx - 1]);
  }
}

/**
 * Preload a single image (preview version for performance)
 */
function preloadImage(file) {
  const previewUrl = file?.previewUrl || file?.url;
  if (!previewUrl) return;

  // Skip if already cached or preloading
  if (LightboxState.imageCache.has(previewUrl) || LightboxState.preloadCache.has(previewUrl)) {
    return;
  }

  LightboxState.preloadCache.add(previewUrl);

  const img = new Image();
  img.onload = () => {
    LightboxState.imageCache.set(previewUrl, img);
  };
  img.onerror = () => {
    console.warn('Failed to preload:', previewUrl);
  };
  img.src = previewUrl;
}

function handleImageLoad() {
  // This handler is now primarily for the initial thumbnail display
  // Full image loading is handled by loadFullSizeImage
}

function handleImageError(file) {
  LightboxState.isLoading = false;
  DOM.loader?.classList.remove('active');

  // If thumbnail failed, hide image
  DOM.image.style.display = 'none';
  DOM.image.classList.remove('loaded', 'thumbnail-quality');

  console.error('Lightbox: Failed to load image', file?.url || 'unknown');
  announceToScreenReader('Error: Failed to load image. Please try again.');
}

// =============================================================================
// NAVIGATION
// =============================================================================

function showPreviousImage() {
  if (LightboxState.currentIndex > 0) {
    openLightbox(LightboxState.currentIndex - 1);
  }
}

function showNextImage() {
  if (LightboxState.currentIndex < LightboxState.files.length - 1) {
    openLightbox(LightboxState.currentIndex + 1);
  }
}

function updateLightboxUI() {
  const current = LightboxState.currentIndex + 1;
  const total = LightboxState.files.length;
  const file = LightboxState.currentFile;

  // Update counter
  if (DOM.counter) {
    DOM.counter.textContent = `${current} of ${total}`;
  }

  // Update title
  if (DOM.title) {
    DOM.title.textContent = file.name;
  }

  // Update size
  if (DOM.size) {
    DOM.size.textContent = file.size;
  }

  // Enable/disable navigation buttons
  if (DOM.prevBtn) {
    DOM.prevBtn.disabled = (LightboxState.currentIndex === 0);
  }

  if (DOM.nextBtn) {
    DOM.nextBtn.disabled = (LightboxState.currentIndex === total - 1);
  }
}

// =============================================================================
// EVENT HANDLERS
// =============================================================================

function handleThumbnailClick(event) {
  const galleryItem = event.currentTarget.closest('.gallery-item');
  if (!galleryItem) return;

  const index = parseInt(galleryItem.dataset.lightboxIndex, 10);
  if (!isNaN(index)) {
    openLightbox(index);
  }
}

function handleThumbnailKeydown(event) {
  if (event.key === 'Enter' || event.key === ' ') {
    event.preventDefault();
    handleThumbnailClick(event);
  }
}

function handleTriggerClick(event) {
  event.preventDefault();
  event.stopPropagation();

  const button = event.currentTarget;
  const index = parseInt(button.dataset.fileIndex, 10);
  if (!isNaN(index)) {
    openLightbox(index);
  }
}

function handleKeyboard(event) {
  if (!LightboxState.isOpen) return;

  switch (event.key) {
    case 'Escape':
      closeLightbox();
      break;

    case 'ArrowLeft':
      event.preventDefault();
      showPreviousImage();
      break;

    case 'ArrowRight':
      event.preventDefault();
      showNextImage();
      break;

    case 'Tab':
      handleFocusTrap(event);
      break;
  }
}

function attachKeyboardListener() {
  if (!LightboxState.keyboardHandler) {
    LightboxState.keyboardHandler = handleKeyboard;
    document.addEventListener('keydown', LightboxState.keyboardHandler);
  }
}

function detachKeyboardListener() {
  if (LightboxState.keyboardHandler) {
    document.removeEventListener('keydown', LightboxState.keyboardHandler);
    LightboxState.keyboardHandler = null;
  }
}

function handleTouchStart(event) {
  if (!LightboxState.isOpen) return;
  LightboxState.touchStartX = event.changedTouches[0].screenX;
}

function handleTouchEnd(event) {
  if (!LightboxState.isOpen) return;
  LightboxState.touchEndX = event.changedTouches[0].screenX;
  handleSwipeGesture();
}

function handleSwipeGesture() {
  const SWIPE_THRESHOLD = 50;
  const diff = LightboxState.touchStartX - LightboxState.touchEndX;

  if (Math.abs(diff) < SWIPE_THRESHOLD) {
    return;
  }

  if (diff > 0) {
    showNextImage();
  } else {
    showPreviousImage();
  }
}

// =============================================================================
// ACCESSIBILITY - FOCUS TRAP
// =============================================================================

function setupFocusTrap() {
  const focusableSelectors = [
    'button:not([disabled])',
    'a[href]',
    'input:not([disabled])',
    'select:not([disabled])',
    'textarea:not([disabled])',
    '[tabindex]:not([tabindex="-1"])'
  ].join(', ');

  LightboxState.focusableElements = Array.from(
    DOM.lightbox.querySelectorAll(focusableSelectors)
  );

  LightboxState.firstFocusable = LightboxState.focusableElements[0];
  LightboxState.lastFocusable = LightboxState.focusableElements[
    LightboxState.focusableElements.length - 1
  ];
}

function handleFocusTrap(event) {
  if (LightboxState.focusableElements.length === 1) {
    event.preventDefault();
    return;
  }

  if (event.shiftKey) {
    if (document.activeElement === LightboxState.firstFocusable) {
      event.preventDefault();
      LightboxState.lastFocusable?.focus();
    }
  } else {
    if (document.activeElement === LightboxState.lastFocusable) {
      event.preventDefault();
      LightboxState.firstFocusable?.focus();
    }
  }
}

function announceToScreenReader(message) {
  if (!DOM.statusRegion) return;

  DOM.statusRegion.textContent = '';

  setTimeout(() => {
    DOM.statusRegion.textContent = message;
  }, 100);
}

// =============================================================================
// INITIALIZATION
// =============================================================================

initLightbox();