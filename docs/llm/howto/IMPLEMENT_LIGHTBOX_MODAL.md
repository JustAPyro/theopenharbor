# Lightbox Modal Viewer Implementation Guide

**Status:** Implementation Required
**Priority:** High
**Complexity:** Medium
**Estimated Time:** 4-6 hours
**Target Audience:** Junior Engineer

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Goals & Success Criteria](#goals--success-criteria)
3. [Technical Requirements](#technical-requirements)
4. [Architecture & Design](#architecture--design)
5. [Implementation Plan](#implementation-plan)
6. [Detailed Implementation Steps](#detailed-implementation-steps)
7. [Testing Requirements](#testing-requirements)
8. [Common Mistakes & Pitfalls](#common-mistakes--pitfalls)
9. [Best Practices](#best-practices)
10. [Accessibility Checklist](#accessibility-checklist)
11. [Performance Considerations](#performance-considerations)
12. [Troubleshooting Guide](#troubleshooting-guide)

---

## Project Overview

### What is a Lightbox Modal?

A lightbox modal is an overlay interface that displays images in full size on top of the current page, darkening the background content. Users can:
- View images at full resolution without leaving the page
- Navigate between images using keyboard, mouse, or touch
- Close the lightbox to return to the gallery grid
- Perform actions like download or zoom

### Current State

**File:** `app/views/collections/templates/collections/view.html`

Currently, clicking an image thumbnail's "zoom" button opens the full image in a new browser tab (`target="_blank"`). This:
- ❌ Takes users away from the collection context
- ❌ Requires browser back button to return
- ❌ No way to navigate to next/previous images
- ❌ Poor mobile experience
- ❌ Breaks the browsing flow

### Desired State

After implementation:
- ✅ Click thumbnail opens lightbox overlay
- ✅ Keyboard navigation (arrow keys, Escape)
- ✅ Touch gestures on mobile (swipe)
- ✅ Image metadata display
- ✅ Smooth animations
- ✅ Fully accessible (WCAG 2.1 AA)
- ✅ Works on all modern browsers

---

## Goals & Success Criteria

### Primary Goals

1. **Improve User Experience**: Allow users to view and browse images without leaving the collection page
2. **Maintain Context**: Keep users engaged with the collection, not lost in browser tabs
3. **Enable Easy Navigation**: Quick browsing through multiple images with keyboard/touch
4. **Accessibility**: Ensure all users can access and use the lightbox

### Success Criteria

| Metric | Target |
|--------|--------|
| Time to first image view | < 500ms |
| Keyboard navigation response | Instant (< 100ms) |
| Mobile swipe gesture recognition | < 50ms |
| Accessibility score (aXe/Lighthouse) | 100/100 |
| Browser compatibility | Chrome, Firefox, Safari, Edge (last 2 versions) |
| Works without JavaScript | Graceful fallback (opens in new tab) |

### Non-Goals (Out of Scope)

- ❌ Image editing capabilities
- ❌ Social sharing within lightbox
- ❌ Image comparison/side-by-side view
- ❌ Slideshow auto-advance mode
- ❌ Image filtering/effects

---

## Technical Requirements

### Browser Support

- **Desktop**: Chrome 90+, Firefox 88+, Safari 14+, Edge 90+
- **Mobile**: iOS Safari 14+, Chrome Mobile 90+
- **Feature Detection**: Use Intersection Observer, classList, addEventListener

### Accessibility Requirements (WCAG 2.1 AA)

1. **Keyboard Navigation**:
   - Tab/Shift+Tab: Navigate interactive elements
   - Arrow keys: Previous/Next image
   - Escape: Close lightbox
   - Enter/Space: Activate buttons

2. **Screen Reader Support**:
   - ARIA roles and labels
   - Live region announcements
   - Descriptive alt text
   - Focus management

3. **Visual Requirements**:
   - 4.5:1 contrast ratio for text
   - Focus indicators visible
   - No content behind modals accessible
   - Respects reduced motion preferences

### Performance Requirements

- Lightbox HTML/CSS loaded with page (< 5KB total)
- JavaScript loads asynchronously
- Images lazy-load as needed
- Transitions use GPU acceleration (transform, opacity)
- No layout thrashing or reflows

### Dependencies

**Already Available:**
- Bootstrap 5.3.2 (modals, utilities)
- Bootstrap Icons 1.11.1 (navigation icons)
- jQuery: ❌ **NOT USED** - Use vanilla JavaScript

**To Add:**
- None - Pure vanilla JavaScript implementation

---

## Architecture & Design

### Component Structure

```
Lightbox Modal (Overlay)
├── Backdrop (dimmed background)
├── Close Button (top-right)
├── Previous Button (left side)
├── Next Button (right side)
├── Image Container
│   ├── Loading Spinner
│   └── <img> element
└── Info Bar (bottom)
    ├── Image Counter (1 of 24)
    ├── Filename
    ├── File Size
    ├── Download Button
    └── Dimensions (if available)
```

### Data Flow

```
User Action → Event Handler → State Update → DOM Update

Example: User clicks thumbnail
1. Click event on thumbnail
2. getLightboxData(fileUuid)
3. openLightbox(imageData)
4. Show modal, load image
5. Attach keyboard/touch listeners
6. Focus management (trap focus in modal)
```

### State Management

The lightbox maintains state in a JavaScript object:

```javascript
const lightboxState = {
  isOpen: false,              // Is lightbox currently open?
  currentIndex: 0,            // Index in files array
  files: [],                  // Array of all file objects
  currentFile: null,          // Currently displayed file object
  isLoading: false,           // Is image currently loading?
  keyboardListenerAttached: false,
  touchStartX: 0,             // For swipe detection
  touchEndX: 0
};
```

### File Structure

```
app/views/collections/templates/collections/
├── view.html (MODIFY - Add lightbox HTML, integrate click handlers)
└── static/
    ├── css/
    │   └── lightbox.css (CREATE - Lightbox-specific styles)
    └── js/
        └── lightbox.js (CREATE - Lightbox behavior)
```

**Why Separate Files?**
- **Maintainability**: Easier to find and modify lightbox code
- **Reusability**: Can be used in other gallery pages
- **Performance**: Can be cached separately by browser
- **Testing**: Easier to write unit tests for isolated code

---

## Implementation Plan

### Phase 1: HTML Structure (30 minutes)
1. Add lightbox modal markup to `view.html`
2. Add data attributes to thumbnails for lightbox integration
3. Verify markup is semantic and accessible

### Phase 2: CSS Styling (45 minutes)
1. Create `lightbox.css` with all styles
2. Implement responsive design (mobile, tablet, desktop)
3. Add animations and transitions
4. Handle loading states

### Phase 3: Core JavaScript (2 hours)
1. Create `lightbox.js` with main functionality
2. Implement open/close behavior
3. Add navigation (next/previous)
4. Handle image loading with spinners
5. Integrate with existing thumbnail click handlers

### Phase 4: Keyboard & Touch (1 hour)
1. Add keyboard event listeners
2. Implement swipe gesture detection
3. Add focus trapping
4. Test navigation flow

### Phase 5: Accessibility (1 hour)
1. Add all ARIA attributes
2. Implement focus management
3. Test with screen reader
4. Verify keyboard-only navigation

### Phase 6: Testing & Polish (1 hour)
1. Cross-browser testing
2. Mobile device testing
3. Performance profiling
4. Bug fixes and refinements

---

## Detailed Implementation Steps

### Step 1: Add Lightbox HTML Structure

**File:** `app/views/collections/templates/collections/view.html`

**Location:** Add before the closing `{% endblock %}` tag (around line 334)

**What to add:**

```html
<!-- Lightbox Modal -->
<div id="lightbox" class="lightbox" role="dialog" aria-modal="true" aria-hidden="true" aria-labelledby="lightbox-title">
  <!-- Backdrop - clickable to close -->
  <div class="lightbox-backdrop" aria-hidden="true"></div>

  <!-- Close Button (X) -->
  <button
    class="lightbox-close"
    aria-label="Close lightbox (press Escape)"
    type="button">
    <i class="bi bi-x-lg" aria-hidden="true"></i>
  </button>

  <!-- Main Content Area -->
  <div class="lightbox-content">
    <!-- Previous Button (Left Arrow) -->
    <button
      class="lightbox-nav lightbox-prev"
      aria-label="Previous image (press left arrow)"
      type="button">
      <i class="bi bi-chevron-left" aria-hidden="true"></i>
    </button>

    <!-- Image Container -->
    <div class="lightbox-image-wrapper">
      <!-- Loading Spinner -->
      <div class="lightbox-loader" role="status" aria-live="polite">
        <div class="spinner-border text-light" role="status">
          <span class="visually-hidden">Loading image...</span>
        </div>
      </div>

      <!-- The actual image -->
      <img
        id="lightbox-image"
        class="lightbox-image"
        src=""
        alt=""
        style="display: none;">
    </div>

    <!-- Next Button (Right Arrow) -->
    <button
      class="lightbox-nav lightbox-next"
      aria-label="Next image (press right arrow)"
      type="button">
      <i class="bi bi-chevron-right" aria-hidden="true"></i>
    </button>
  </div>

  <!-- Bottom Info Bar -->
  <div class="lightbox-info">
    <div class="lightbox-info-left">
      <!-- Image counter: "5 of 24" -->
      <span class="lightbox-counter" id="lightbox-counter" aria-live="polite"></span>

      <!-- Filename -->
      <h3 class="lightbox-title" id="lightbox-title"></h3>

      <!-- File metadata -->
      <div class="lightbox-meta">
        <span class="lightbox-size" id="lightbox-size"></span>
        <span class="lightbox-dimensions" id="lightbox-dimensions"></span>
      </div>
    </div>

    <div class="lightbox-info-right">
      <!-- Download button -->
      <a
        id="lightbox-download"
        class="btn btn-light btn-sm"
        download
        href="#">
        <i class="bi bi-download me-1"></i>
        Download
      </a>
    </div>
  </div>

  <!-- Live region for screen reader announcements -->
  <div class="visually-hidden" role="status" aria-live="polite" aria-atomic="true" id="lightbox-status"></div>
</div>
```

**Why this structure?**

1. **`role="dialog"` + `aria-modal="true"`**: Tells screen readers this is a modal dialog
2. **`aria-hidden="true"`**: Initially hidden from assistive tech
3. **Backdrop separate from content**: Allows clicking outside to close
4. **Buttons have `type="button"`**: Prevents form submission if used in forms
5. **Icons have `aria-hidden="true"`**: Icon is decorative, label provides context
6. **Loading spinner with `role="status"`**: Announces loading to screen readers
7. **Live regions**: Announce dynamic changes (image counter, loading states)

**Common Mistakes:**
- ❌ Forgetting `aria-modal="true"` - Screen readers won't trap focus
- ❌ Missing `type="button"` - Buttons might submit forms
- ❌ No loading state - Users see blank screen while image loads
- ❌ Icons without `aria-hidden` - Screen readers read "x large icon"

---

### Step 2: Update Thumbnail Click Handlers

**File:** `app/views/collections/templates/collections/view.html`

**Location:** Lines 73-105 (gallery item)

**Current code (line 73-105):**
```html
<div class="gallery-item">
  <div class="gallery-thumbnail">
    <img
      src="{{ url_for('collections.serve_thumbnail', file_uuid=file.uuid) }}"
      alt="{{ file.original_filename }}"
      class="img-fluid gallery-image"
      loading="lazy"
      onerror="this.onerror=null; this.src='{{ url_for('collections.serve_file', file_uuid=file.uuid) }}';">
  </div>

  <div class="gallery-overlay">
    <div class="overlay-actions">
      <a href="{{ url_for('collections.serve_file', file_uuid=file.uuid) }}"
         target="_blank"
         class="btn btn-light btn-sm"
         title="View full size">
        <i class="bi bi-zoom-in"></i>
      </a>
      <a href="{{ url_for('collections.serve_file', file_uuid=file.uuid) }}"
         download="{{ file.original_filename }}"
         class="btn btn-light btn-sm"
         title="Download">
        <i class="bi bi-download"></i>
      </a>
    </div>
  </div>

  <div class="gallery-info">
    <div class="file-name">{{ file.original_filename }}</div>
    <div class="file-size">{{ file.size_human }}</div>
  </div>
</div>
```

**Replace with:**

```html
<div class="gallery-item"
     data-lightbox-index="{{ loop.index0 }}"
     data-file-uuid="{{ file.uuid }}"
     data-file-name="{{ file.original_filename }}"
     data-file-size="{{ file.size_human }}"
     data-full-url="{{ url_for('collections.serve_file', file_uuid=file.uuid) }}">

  <div class="gallery-thumbnail" role="button" tabindex="0"
       aria-label="View {{ file.original_filename }} in lightbox">
    <img
      src="{{ url_for('collections.serve_thumbnail', file_uuid=file.uuid) }}"
      alt="{{ file.original_filename }}"
      class="img-fluid gallery-image"
      loading="lazy"
      onerror="this.onerror=null; this.src='{{ url_for('collections.serve_file', file_uuid=file.uuid) }}';">
  </div>

  <div class="gallery-overlay">
    <div class="overlay-actions">
      <!-- Modified: Opens lightbox instead of new tab -->
      <button type="button"
              class="btn btn-light btn-sm lightbox-trigger"
              data-file-index="{{ loop.index0 }}"
              title="View full size"
              aria-label="View {{ file.original_filename }} full size">
        <i class="bi bi-zoom-in" aria-hidden="true"></i>
      </button>

      <!-- Download stays the same -->
      <a href="{{ url_for('collections.serve_file', file_uuid=file.uuid) }}"
         download="{{ file.original_filename }}"
         class="btn btn-light btn-sm"
         title="Download"
         aria-label="Download {{ file.original_filename }}">
        <i class="bi bi-download" aria-hidden="true"></i>
      </a>
    </div>
  </div>

  <div class="gallery-info">
    <div class="file-name">{{ file.original_filename }}</div>
    <div class="file-size">{{ file.size_human }}</div>
  </div>
</div>
```

**What changed?**

1. **Added data attributes** to gallery-item:
   - `data-lightbox-index`: Position in array (0-based)
   - `data-file-uuid`: Unique identifier
   - `data-file-name`: Original filename for display
   - `data-file-size`: Human-readable size
   - `data-full-url`: Full image URL

2. **Made thumbnail clickable**:
   - `role="button"`: Tells screen readers it's interactive
   - `tabindex="0"`: Makes it keyboard-focusable
   - `aria-label`: Describes what clicking does

3. **Changed zoom button from `<a>` to `<button>`**:
   - Changed `target="_blank"` link to button
   - Added `lightbox-trigger` class for event binding
   - Added `data-file-index` for quick lookup

4. **Improved accessibility labels**:
   - Each button describes its specific action
   - Icons marked `aria-hidden="true"`

**Why data attributes?**

Data attributes store information in HTML that JavaScript can read:
```javascript
// JavaScript can access like this:
const item = document.querySelector('.gallery-item');
const fileName = item.dataset.fileName;  // Gets data-file-name
const index = item.dataset.lightboxIndex; // Gets data-lightbox-index
```

This is better than:
- ❌ Storing in JavaScript arrays (requires keeping HTML and JS in sync)
- ❌ Parsing HTML content (fragile, breaks easily)
- ❌ Global variables (memory leaks, naming conflicts)

---

### Step 3: Create Lightbox CSS

**File:** `app/views/collections/static/css/lightbox.css` (CREATE NEW FILE)

**Full CSS code:**

```css
/* ===================================================================
   LIGHTBOX MODAL STYLES

   Purpose: Styles for full-screen image lightbox modal
   Dependencies: Bootstrap 5 base styles, Bootstrap Icons
   Browser Support: Chrome 90+, Firefox 88+, Safari 14+, Edge 90+
   =================================================================== */

/* ===================================================================
   BASE LIGHTBOX CONTAINER
   =================================================================== */

.lightbox {
  /* Positioning: Full-screen overlay */
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 9999; /* Above everything else */

  /* Layout */
  display: none; /* Hidden by default */
  align-items: center;
  justify-content: center;

  /* Prevent scrolling of body content behind modal */
  overflow: hidden;

  /* Performance: GPU acceleration */
  will-change: opacity;

  /* Animation */
  opacity: 0;
  transition: opacity 300ms ease-in-out;
}

/* When lightbox is open */
.lightbox.active {
  display: flex;
  opacity: 1;
}

/* Respect user's motion preferences */
@media (prefers-reduced-motion: reduce) {
  .lightbox {
    transition: none;
  }
}

/* ===================================================================
   BACKDROP (Dimmed Background)
   =================================================================== */

.lightbox-backdrop {
  /* Positioning: Full screen behind content */
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;

  /* Visual: Dark semi-transparent overlay */
  background-color: rgba(0, 0, 0, 0.95);

  /* Interaction: Clickable to close */
  cursor: pointer;

  /* Layering: Behind content, above page */
  z-index: 1;
}

/* ===================================================================
   CLOSE BUTTON (Top-Right X)
   =================================================================== */

.lightbox-close {
  /* Positioning: Fixed to top-right corner */
  position: absolute;
  top: 20px;
  right: 20px;
  z-index: 10; /* Above content */

  /* Visual */
  width: 44px;
  height: 44px;
  background-color: rgba(0, 0, 0, 0.5);
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-radius: 50%; /* Circular button */
  color: white;
  font-size: 24px;

  /* Remove default button styles */
  padding: 0;

  /* Interaction */
  cursor: pointer;
  transition: all 200ms ease;
}

.lightbox-close:hover,
.lightbox-close:focus {
  background-color: rgba(255, 255, 255, 0.2);
  border-color: rgba(255, 255, 255, 0.6);
  transform: scale(1.1);
}

/* Focus indicator for keyboard users */
.lightbox-close:focus {
  outline: 3px solid #4A90E2;
  outline-offset: 2px;
}

.lightbox-close:active {
  transform: scale(0.95);
}

/* Mobile: Larger touch target */
@media (max-width: 768px) {
  .lightbox-close {
    width: 50px;
    height: 50px;
    top: 10px;
    right: 10px;
  }
}

/* ===================================================================
   CONTENT AREA (Image + Navigation)
   =================================================================== */

.lightbox-content {
  /* Positioning: Centered content */
  position: relative;
  z-index: 5; /* Above backdrop */

  /* Layout: Flexbox for centering */
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 20px;

  /* Sizing: Most of screen, leave room for info bar */
  width: 100%;
  max-width: 95vw;
  height: calc(100vh - 120px); /* Leave 120px for info bar */

  /* Padding for breathing room */
  padding: 20px;
}

@media (max-width: 768px) {
  .lightbox-content {
    height: calc(100vh - 160px); /* More room for info on mobile */
    padding: 10px;
    gap: 10px;
  }
}

/* ===================================================================
   IMAGE WRAPPER & IMAGE
   =================================================================== */

.lightbox-image-wrapper {
  /* Positioning */
  position: relative;

  /* Layout: Flexbox for centering */
  display: flex;
  align-items: center;
  justify-content: center;

  /* Sizing: Flexible, constrained by container */
  flex: 1;
  max-width: 100%;
  max-height: 100%;

  /* Ensure wrapper doesn't exceed image */
  overflow: hidden;
}

.lightbox-image {
  /* Sizing: Fit within container, maintain aspect ratio */
  max-width: 100%;
  max-height: 100%;
  width: auto;
  height: auto;

  /* Display */
  display: block;

  /* Visual: Subtle shadow */
  box-shadow: 0 10px 50px rgba(0, 0, 0, 0.5);

  /* Animation: Fade in when loaded */
  opacity: 0;
  transition: opacity 300ms ease-in-out;

  /* Performance: GPU acceleration */
  will-change: opacity;
}

.lightbox-image.loaded {
  opacity: 1;
}

/* Prevent image dragging (interferes with touch gestures) */
.lightbox-image {
  -webkit-user-drag: none;
  -khtml-user-drag: none;
  -moz-user-drag: none;
  -o-user-drag: none;
  user-drag: none;
}

/* ===================================================================
   LOADING SPINNER
   =================================================================== */

.lightbox-loader {
  /* Positioning: Centered over image area */
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  z-index: 10;

  /* Display: Hidden by default */
  display: none;
}

.lightbox-loader.active {
  display: block;
}

/* Bootstrap spinner customization */
.lightbox-loader .spinner-border {
  width: 3rem;
  height: 3rem;
  border-width: 0.3rem;
}

/* ===================================================================
   NAVIGATION BUTTONS (Previous/Next)
   =================================================================== */

.lightbox-nav {
  /* Positioning */
  position: relative;
  z-index: 10;

  /* Sizing */
  width: 50px;
  height: 50px;
  flex-shrink: 0; /* Don't shrink with content */

  /* Visual */
  background-color: rgba(0, 0, 0, 0.5);
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-radius: 50%;
  color: white;
  font-size: 28px;

  /* Remove default button styles */
  padding: 0;

  /* Interaction */
  cursor: pointer;
  transition: all 200ms ease;
}

.lightbox-nav:hover,
.lightbox-nav:focus {
  background-color: rgba(255, 255, 255, 0.2);
  border-color: rgba(255, 255, 255, 0.6);
  transform: scale(1.1);
}

.lightbox-nav:focus {
  outline: 3px solid #4A90E2;
  outline-offset: 2px;
}

.lightbox-nav:active {
  transform: scale(0.95);
}

/* Disabled state (e.g., first/last image) */
.lightbox-nav:disabled {
  opacity: 0.3;
  cursor: not-allowed;
  pointer-events: none;
}

/* Mobile: Position over image (saves horizontal space) */
@media (max-width: 768px) {
  .lightbox-nav {
    position: absolute;
    width: 44px;
    height: 44px;
    font-size: 24px;
  }

  .lightbox-prev {
    left: 10px;
  }

  .lightbox-next {
    right: 10px;
  }
}

/* Tablet: Slightly smaller */
@media (min-width: 769px) and (max-width: 1024px) {
  .lightbox-nav {
    width: 46px;
    height: 46px;
  }
}

/* ===================================================================
   INFO BAR (Bottom)
   =================================================================== */

.lightbox-info {
  /* Positioning: Fixed to bottom */
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  z-index: 10;

  /* Layout: Flexbox for left/right sections */
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;

  /* Sizing */
  padding: 20px 30px;
  min-height: 80px;

  /* Visual */
  background: linear-gradient(
    to top,
    rgba(0, 0, 0, 0.9) 0%,
    rgba(0, 0, 0, 0.7) 70%,
    transparent 100%
  );
  color: white;
}

.lightbox-info-left {
  flex: 1;
  min-width: 0; /* Allow text truncation */
}

.lightbox-info-right {
  flex-shrink: 0;
}

/* Mobile: Stack vertically */
@media (max-width: 768px) {
  .lightbox-info {
    flex-direction: column;
    align-items: flex-start;
    gap: 10px;
    padding: 15px;
    min-height: 120px;
  }

  .lightbox-info-right {
    width: 100%;
  }

  .lightbox-info-right .btn {
    width: 100%;
  }
}

/* ===================================================================
   INFO BAR CONTENT
   =================================================================== */

/* Image counter: "5 of 24" */
.lightbox-counter {
  display: inline-block;
  padding: 4px 12px;
  background-color: rgba(255, 255, 255, 0.2);
  border-radius: 12px;
  font-size: 0.85rem;
  font-weight: 600;
  margin-bottom: 8px;
}

/* Filename */
.lightbox-title {
  font-size: 1.1rem;
  font-weight: 600;
  margin: 0 0 6px 0;

  /* Truncate long filenames */
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* Metadata (size, dimensions) */
.lightbox-meta {
  display: flex;
  gap: 15px;
  font-size: 0.9rem;
  color: rgba(255, 255, 255, 0.8);
}

.lightbox-meta span:not(:last-child)::after {
  content: "•";
  margin-left: 15px;
  color: rgba(255, 255, 255, 0.5);
}

/* Mobile: Stack metadata */
@media (max-width: 480px) {
  .lightbox-meta {
    flex-direction: column;
    gap: 4px;
  }

  .lightbox-meta span::after {
    display: none;
  }
}

/* ===================================================================
   BODY CLASS (Prevent scrolling when lightbox open)
   =================================================================== */

body.lightbox-open {
  overflow: hidden;
  /* Prevent width shift when scrollbar disappears */
  padding-right: var(--scrollbar-width, 0);
}

/* ===================================================================
   ACCESSIBILITY UTILITIES
   =================================================================== */

/* Visually hidden but accessible to screen readers */
.visually-hidden {
  position: absolute !important;
  width: 1px !important;
  height: 1px !important;
  padding: 0 !important;
  margin: -1px !important;
  overflow: hidden !important;
  clip: rect(0, 0, 0, 0) !important;
  white-space: nowrap !important;
  border: 0 !important;
}

/* ===================================================================
   PRINT STYLES (Hide lightbox when printing)
   =================================================================== */

@media print {
  .lightbox {
    display: none !important;
  }
}

/* ===================================================================
   HIGH CONTRAST MODE (Windows High Contrast)
   =================================================================== */

@media (prefers-contrast: high) {
  .lightbox-backdrop {
    background-color: black;
  }

  .lightbox-nav,
  .lightbox-close {
    border-width: 3px;
    border-color: white;
  }
}
```

**Key CSS Concepts Explained:**

1. **`z-index` layering**:
   - Backdrop: 1 (bottom)
   - Content: 5 (middle)
   - Buttons: 10 (top)
   - Lightbox container: 9999 (above everything)

2. **Flexbox for centering**:
   ```css
   display: flex;
   align-items: center;      /* Vertical center */
   justify-content: center;  /* Horizontal center */
   ```

3. **`will-change` for performance**:
   Tells browser to optimize for changes to specific properties
   ```css
   will-change: opacity; /* GPU accelerates opacity changes */
   ```

4. **`calc()` for dynamic sizing**:
   ```css
   height: calc(100vh - 120px); /* Viewport height minus 120px */
   ```

5. **Responsive design breakpoints**:
   - Mobile: `max-width: 768px`
   - Tablet: `min-width: 769px and max-width: 1024px`
   - Desktop: `min-width: 1025px` (implicit)

**Common CSS Mistakes:**

- ❌ Forgetting `z-index` - Elements overlap incorrectly
- ❌ Not preventing body scroll - Page scrolls behind modal
- ❌ Fixed pixel sizes on mobile - Buttons too small to tap
- ❌ Missing `:focus` styles - Keyboard users can't see focus
- ❌ Forgetting `will-change` - Janky animations
- ❌ Not using `transform` for animations - Forces repaints

---

### Step 4: Link CSS File

**File:** `app/views/collections/templates/collections/view.html`

**Location:** After line 274 (after the `</style>` tag, before `<script>`)

**Add:**

```html
</style>

<!-- Lightbox CSS -->
<link rel="stylesheet" href="{{ url_for('collections.static', filename='css/lightbox.css') }}">

<script>
```

**Why after inline styles?**
- External CSS has higher specificity than inline when loaded later
- Allows overriding collection-specific styles if needed
- Browser can cache the external file

---

### Step 5: Create Lightbox JavaScript

**File:** `app/views/collections/static/js/lightbox.js` (CREATE NEW FILE)

**Full JavaScript code:**

```javascript
/**
 * LIGHTBOX MODAL VIEWER
 *
 * Purpose: Full-screen image viewer with keyboard/touch navigation
 * Dependencies: None (vanilla JavaScript)
 * Browser Support: Chrome 90+, Firefox 88+, Safari 14+, Edge 90+
 *
 * Features:
 * - Click thumbnail to open full-size image
 * - Navigate with arrow keys or prev/next buttons
 * - Swipe on mobile to navigate
 * - Escape key or click backdrop to close
 * - Focus trapping for accessibility
 * - Loading states with spinner
 * - Image metadata display
 *
 * @author The Open Harbor Team
 * @version 1.0.0
 */

// =============================================================================
// STATE MANAGEMENT
// =============================================================================

/**
 * Lightbox state object - single source of truth
 */
const LightboxState = {
  isOpen: false,
  currentIndex: 0,
  files: [],
  currentFile: null,
  isLoading: false,

  // Event listener cleanup
  keyboardHandler: null,
  backdropHandler: null,

  // Touch gesture tracking
  touchStartX: 0,
  touchEndX: 0,

  // Focus trap
  focusableElements: [],
  firstFocusable: null,
  lastFocusable: null,
  previousFocus: null,

  // Scrollbar width (to prevent layout shift)
  scrollbarWidth: 0
};

// =============================================================================
// DOM ELEMENT REFERENCES (cached for performance)
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

/**
 * Initialize lightbox when DOM is ready
 * Sets up event listeners and caches DOM references
 */
function initLightbox() {
  // Wait for DOM to be fully loaded
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initLightbox);
    return;
  }

  // Cache all DOM element references
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

  // Verify required elements exist
  if (!DOM.lightbox || !DOM.image) {
    console.error('Lightbox: Required DOM elements not found');
    return;
  }

  // Calculate scrollbar width (for body padding when modal opens)
  LightboxState.scrollbarWidth = calculateScrollbarWidth();

  // Build file list from gallery items
  buildFileList();

  // Attach event listeners
  attachEventListeners();

  console.log('Lightbox initialized with', LightboxState.files.length, 'images');
}

/**
 * Calculate browser scrollbar width
 * Used to prevent layout shift when hiding body overflow
 *
 * @returns {number} Scrollbar width in pixels
 */
function calculateScrollbarWidth() {
  // Create temporary div with scrollbar
  const outer = document.createElement('div');
  outer.style.visibility = 'hidden';
  outer.style.overflow = 'scroll';
  outer.style.width = '100px';
  document.body.appendChild(outer);

  // Create inner div
  const inner = document.createElement('div');
  inner.style.width = '100%';
  outer.appendChild(inner);

  // Calculate difference
  const scrollbarWidth = outer.offsetWidth - inner.offsetWidth;

  // Clean up
  document.body.removeChild(outer);

  return scrollbarWidth;
}

/**
 * Build array of file objects from gallery items
 * Reads data attributes from HTML
 */
function buildFileList() {
  const galleryItems = document.querySelectorAll('.gallery-item');

  LightboxState.files = Array.from(galleryItems).map((item, index) => ({
    index: index,
    uuid: item.dataset.fileUuid,
    name: item.dataset.fileName,
    size: item.dataset.fileSize,
    url: item.dataset.fullUrl,
    thumbnail: item.querySelector('img')?.src || ''
  }));
}

/**
 * Attach all event listeners
 */
function attachEventListeners() {
  // Thumbnail clicks - open lightbox
  document.querySelectorAll('.gallery-thumbnail').forEach(thumbnail => {
    thumbnail.addEventListener('click', handleThumbnailClick);
    thumbnail.addEventListener('keydown', handleThumbnailKeydown);
  });

  // Lightbox trigger buttons (zoom icons)
  document.querySelectorAll('.lightbox-trigger').forEach(trigger => {
    trigger.addEventListener('click', handleTriggerClick);
  });

  // Close button
  DOM.closeBtn?.addEventListener('click', closeLightbox);

  // Backdrop click (close)
  DOM.backdrop?.addEventListener('click', closeLightbox);

  // Navigation buttons
  DOM.prevBtn?.addEventListener('click', showPreviousImage);
  DOM.nextBtn?.addEventListener('click', showNextImage);

  // Image load events
  DOM.image?.addEventListener('load', handleImageLoad);
  DOM.image?.addEventListener('error', handleImageError);

  // Touch gestures (mobile swipe)
  DOM.lightbox?.addEventListener('touchstart', handleTouchStart, { passive: true });
  DOM.lightbox?.addEventListener('touchend', handleTouchEnd, { passive: true });
}

// =============================================================================
// OPEN/CLOSE LIGHTBOX
// =============================================================================

/**
 * Open lightbox and display image at given index
 *
 * @param {number} index - Index of image to display (0-based)
 */
function openLightbox(index) {
  // Validate index
  if (index < 0 || index >= LightboxState.files.length) {
    console.error('Lightbox: Invalid index', index);
    return;
  }

  // Update state
  LightboxState.isOpen = true;
  LightboxState.currentIndex = index;
  LightboxState.currentFile = LightboxState.files[index];

  // Store current focus to restore later
  LightboxState.previousFocus = document.activeElement;

  // Prevent body scroll
  document.body.classList.add('lightbox-open');
  document.body.style.setProperty('--scrollbar-width', `${LightboxState.scrollbarWidth}px`);

  // Show lightbox
  DOM.lightbox.classList.add('active');
  DOM.lightbox.setAttribute('aria-hidden', 'false');

  // Load and display image
  loadImage(LightboxState.currentFile);

  // Update UI
  updateLightboxUI();

  // Attach keyboard listener
  attachKeyboardListener();

  // Setup focus trap
  setupFocusTrap();

  // Focus close button initially
  DOM.closeBtn?.focus();

  // Announce to screen readers
  announceToScreenReader(`Opened lightbox. Image ${index + 1} of ${LightboxState.files.length}`);
}

/**
 * Close lightbox and return to gallery
 */
function closeLightbox() {
  // Update state
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

  // Restore focus to trigger element
  if (LightboxState.previousFocus) {
    LightboxState.previousFocus.focus();
    LightboxState.previousFocus = null;
  }

  // Announce to screen readers
  announceToScreenReader('Closed lightbox. Returned to gallery.');
}

// =============================================================================
// IMAGE LOADING
// =============================================================================

/**
 * Load image and show loading state
 *
 * @param {Object} file - File object with url property
 */
function loadImage(file) {
  if (!file || !file.url) {
    console.error('Lightbox: Invalid file object', file);
    return;
  }

  // Update state
  LightboxState.isLoading = true;

  // Show loader
  DOM.loader?.classList.add('active');
  DOM.image.style.display = 'none';
  DOM.image.classList.remove('loaded');

  // Start loading image
  DOM.image.src = file.url;

  // Update download button
  if (DOM.downloadBtn) {
    DOM.downloadBtn.href = file.url;
    DOM.downloadBtn.download = file.name;
  }

  // Announce loading to screen readers
  announceToScreenReader(`Loading ${file.name}`);
}

/**
 * Handle successful image load
 */
function handleImageLoad() {
  // Update state
  LightboxState.isLoading = false;

  // Hide loader
  DOM.loader?.classList.remove('active');

  // Show image with fade-in
  DOM.image.style.display = 'block';

  // Trigger reflow to ensure transition works
  DOM.image.offsetHeight;

  // Add loaded class (triggers fade-in via CSS)
  DOM.image.classList.add('loaded');

  // Get actual image dimensions
  const width = DOM.image.naturalWidth;
  const height = DOM.image.naturalHeight;

  // Update dimensions display
  if (DOM.dimensions && width && height) {
    DOM.dimensions.textContent = `${width} × ${height}`;
  }

  // Announce to screen readers
  announceToScreenReader(`Image loaded: ${LightboxState.currentFile.name}`);
}

/**
 * Handle image load error
 */
function handleImageError() {
  // Update state
  LightboxState.isLoading = false;

  // Hide loader
  DOM.loader?.classList.remove('active');

  // Show error message
  console.error('Lightbox: Failed to load image', LightboxState.currentFile.url);

  // Announce to screen readers
  announceToScreenReader('Error: Failed to load image. Please try again.');

  // TODO: Show user-friendly error message in lightbox
  // For now, keep lightbox open so user can try next/previous
}

// =============================================================================
// NAVIGATION
// =============================================================================

/**
 * Show previous image in collection
 */
function showPreviousImage() {
  if (LightboxState.currentIndex > 0) {
    openLightbox(LightboxState.currentIndex - 1);
  }
}

/**
 * Show next image in collection
 */
function showNextImage() {
  if (LightboxState.currentIndex < LightboxState.files.length - 1) {
    openLightbox(LightboxState.currentIndex + 1);
  }
}

/**
 * Update lightbox UI (counter, buttons, metadata)
 */
function updateLightboxUI() {
  const current = LightboxState.currentIndex + 1;
  const total = LightboxState.files.length;
  const file = LightboxState.currentFile;

  // Update counter: "5 of 24"
  if (DOM.counter) {
    DOM.counter.textContent = `${current} of ${total}`;
  }

  // Update title
  if (DOM.title) {
    DOM.title.textContent = file.name;
  }

  // Update file size
  if (DOM.size) {
    DOM.size.textContent = file.size;
  }

  // Update image alt text
  if (DOM.image) {
    DOM.image.alt = file.name;
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

/**
 * Handle thumbnail click - open lightbox
 */
function handleThumbnailClick(event) {
  const galleryItem = event.currentTarget.closest('.gallery-item');
  if (!galleryItem) return;

  const index = parseInt(galleryItem.dataset.lightboxIndex, 10);
  openLightbox(index);
}

/**
 * Handle thumbnail keyboard interaction (Enter/Space)
 */
function handleThumbnailKeydown(event) {
  if (event.key === 'Enter' || event.key === ' ') {
    event.preventDefault();
    handleThumbnailClick(event);
  }
}

/**
 * Handle trigger button click (zoom icon)
 */
function handleTriggerClick(event) {
  event.preventDefault();
  event.stopPropagation();

  const button = event.currentTarget;
  const index = parseInt(button.dataset.fileIndex, 10);
  openLightbox(index);
}

/**
 * Handle keyboard events (arrow keys, Escape)
 */
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
      // Focus trap - handled by handleFocusTrap
      handleFocusTrap(event);
      break;
  }
}

/**
 * Attach keyboard event listener
 */
function attachKeyboardListener() {
  if (!LightboxState.keyboardHandler) {
    LightboxState.keyboardHandler = handleKeyboard;
    document.addEventListener('keydown', LightboxState.keyboardHandler);
  }
}

/**
 * Detach keyboard event listener
 */
function detachKeyboardListener() {
  if (LightboxState.keyboardHandler) {
    document.removeEventListener('keydown', LightboxState.keyboardHandler);
    LightboxState.keyboardHandler = null;
  }
}

/**
 * Handle touch start (for swipe gestures)
 */
function handleTouchStart(event) {
  if (!LightboxState.isOpen) return;

  LightboxState.touchStartX = event.changedTouches[0].screenX;
}

/**
 * Handle touch end (detect swipe direction)
 */
function handleTouchEnd(event) {
  if (!LightboxState.isOpen) return;

  LightboxState.touchEndX = event.changedTouches[0].screenX;
  handleSwipeGesture();
}

/**
 * Detect swipe direction and navigate
 * Swipe right = previous, Swipe left = next
 */
function handleSwipeGesture() {
  const SWIPE_THRESHOLD = 50; // Minimum distance for swipe

  const diff = LightboxState.touchStartX - LightboxState.touchEndX;

  if (Math.abs(diff) < SWIPE_THRESHOLD) {
    return; // Not a swipe, too short
  }

  if (diff > 0) {
    // Swiped left - show next
    showNextImage();
  } else {
    // Swiped right - show previous
    showPreviousImage();
  }
}

// =============================================================================
// ACCESSIBILITY - FOCUS TRAP
// =============================================================================

/**
 * Setup focus trap - keep focus within lightbox
 */
function setupFocusTrap() {
  // Get all focusable elements in lightbox
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

/**
 * Handle focus trap on Tab key
 */
function handleFocusTrap(event) {
  // If only one focusable element, prevent tabbing
  if (LightboxState.focusableElements.length === 1) {
    event.preventDefault();
    return;
  }

  // If shift+tab on first element, go to last
  if (event.shiftKey) {
    if (document.activeElement === LightboxState.firstFocusable) {
      event.preventDefault();
      LightboxState.lastFocusable?.focus();
    }
  }
  // If tab on last element, go to first
  else {
    if (document.activeElement === LightboxState.lastFocusable) {
      event.preventDefault();
      LightboxState.firstFocusable?.focus();
    }
  }
}

/**
 * Announce message to screen readers via live region
 *
 * @param {string} message - Message to announce
 */
function announceToScreenReader(message) {
  if (!DOM.statusRegion) return;

  // Clear first (some screen readers need this)
  DOM.statusRegion.textContent = '';

  // Small delay ensures screen reader picks up change
  setTimeout(() => {
    DOM.statusRegion.textContent = message;
  }, 100);
}

// =============================================================================
// INITIALIZATION - Start when script loads
// =============================================================================

initLightbox();
```

**Key JavaScript Concepts Explained:**

1. **State Management**:
   - Single `LightboxState` object holds all state
   - Prevents global variable pollution
   - Easy to debug (inspect one object)

2. **DOM Caching**:
   ```javascript
   const DOM = { lightbox: null, ... };
   // Query once, reuse many times
   DOM.lightbox = document.getElementById('lightbox');
   ```
   Better than:
   ```javascript
   // ❌ Queries DOM every time
   document.getElementById('lightbox').classList.add('active');
   ```

3. **Event Listener Cleanup**:
   ```javascript
   // Store reference
   LightboxState.keyboardHandler = handleKeyboard;
   // Attach
   document.addEventListener('keydown', LightboxState.keyboardHandler);
   // Detach later
   document.removeEventListener('keydown', LightboxState.keyboardHandler);
   ```

4. **Focus Trap** (Accessibility):
   - Finds all focusable elements
   - Tab on last element → focus first
   - Shift+Tab on first → focus last
   - Prevents tabbing out of modal

5. **Touch Gestures**:
   - Record touch start position
   - Record touch end position
   - Calculate difference
   - If > threshold → trigger navigation

6. **ARIA Live Regions**:
   ```javascript
   announceToScreenReader('Image loaded');
   // Updates hidden div with aria-live="polite"
   // Screen reader announces to user
   ```

**Common JavaScript Mistakes:**

- ❌ Not caching DOM queries (performance)
- ❌ Not removing event listeners (memory leaks)
- ❌ Using `innerHTML` for user data (XSS vulnerability)
- ❌ Not handling image load errors
- ❌ Forgetting to restore focus when closing
- ❌ Not preventing body scroll (page scrolls behind)
- ❌ Missing null checks (`DOM.lightbox?.classList`)

---

### Step 6: Link JavaScript File

**File:** `app/views/collections/templates/collections/view.html`

**Location:** After the existing `<script>` block (around line 333)

**Add:**

```html
</script>

<!-- Lightbox JavaScript -->
<script src="{{ url_for('collections.static', filename='js/lightbox.js') }}" defer></script>

{% endblock %}
```

**Why `defer` attribute?**
- Script loads asynchronously (doesn't block page render)
- Executes after DOM is ready
- Maintains order with other deferred scripts
- Modern best practice for non-critical scripts

**Alternative: `async`**
```html
<!-- ❌ Don't use async for this -->
<script src="..." async></script>
```
- `async`: Load and execute ASAP (order not guaranteed)
- `defer`: Load async, execute in order after DOM ready
- Use `defer` when script depends on DOM elements

---

### Step 7: Create Static File Directories (if needed)

If the directories don't exist, create them:

```bash
# From project root
mkdir -p app/views/collections/static/css
mkdir -p app/views/collections/static/js
```

Then create the files:
```bash
touch app/views/collections/static/css/lightbox.css
touch app/views/collections/static/js/lightbox.js
```

**File permissions:**
```bash
chmod 644 app/views/collections/static/css/lightbox.css
chmod 644 app/views/collections/static/js/lightbox.js
```

**Verify Flask can serve static files:**

Flask blueprints serve static files from the `static` folder within the blueprint directory. The URL pattern is:
```
/collections/static/<path:filename>
```

This is configured in: `app/views/collections/__init__.py`

---

## Testing Requirements

### Manual Testing Checklist

#### Basic Functionality
- [ ] Click thumbnail opens lightbox
- [ ] Click zoom icon opens lightbox
- [ ] Close button closes lightbox
- [ ] Click backdrop closes lightbox
- [ ] Previous button shows previous image
- [ ] Next button shows next image
- [ ] Previous disabled on first image
- [ ] Next disabled on last image
- [ ] Image counter updates correctly ("3 of 10")
- [ ] Filename displays correctly
- [ ] File size displays correctly
- [ ] Download button works

#### Keyboard Navigation
- [ ] Escape closes lightbox
- [ ] Left arrow shows previous image
- [ ] Right arrow shows next image
- [ ] Tab cycles through buttons
- [ ] Tab wraps from last to first button
- [ ] Shift+Tab cycles backward
- [ ] Enter on thumbnail opens lightbox
- [ ] Space on thumbnail opens lightbox

#### Mobile/Touch
- [ ] Tap thumbnail opens lightbox
- [ ] Tap backdrop closes lightbox
- [ ] Swipe left shows next image
- [ ] Swipe right shows previous image
- [ ] Pinch zoom works on image (browser native)
- [ ] Touch targets are large enough (44x44px minimum)

#### Visual/UI
- [ ] Loading spinner appears while image loads
- [ ] Image fades in smoothly when loaded
- [ ] Buttons have hover effects
- [ ] Buttons have focus indicators
- [ ] Layout responsive on mobile
- [ ] Layout responsive on tablet
- [ ] Layout responsive on desktop
- [ ] No layout shift when opening/closing

#### Accessibility
- [ ] Screen reader announces image count
- [ ] Screen reader announces loading state
- [ ] Screen reader announces navigation
- [ ] Focus moves to close button when opened
- [ ] Focus returns to trigger when closed
- [ ] All buttons have aria-labels
- [ ] Color contrast meets WCAG AA
- [ ] Works with keyboard only (no mouse)
- [ ] Focus trap keeps focus in modal

#### Error Handling
- [ ] Broken image shows error (doesn't crash)
- [ ] Can navigate away from broken image
- [ ] Empty collection doesn't break
- [ ] Missing data attributes handled gracefully

#### Browser Compatibility
- [ ] Chrome (latest)
- [ ] Firefox (latest)
- [ ] Safari (latest)
- [ ] Edge (latest)
- [ ] Chrome Mobile (Android)
- [ ] Safari Mobile (iOS)

### Automated Testing

**Test file location:** `tests/views/test_lightbox.py` (CREATE)

```python
"""
Tests for lightbox modal functionality.
"""

import pytest
from flask import url_for
from app.models import Collection, File, db


class TestLightboxMarkup:
    """Test that lightbox HTML is present and correct."""

    def test_lightbox_container_exists(self, client, test_collection_with_files):
        """Test lightbox container is in page."""
        collection, files = test_collection_with_files

        response = client.get(url_for('collections.view', uuid=collection.uuid))
        assert response.status_code == 200

        # Check for lightbox container
        assert b'id="lightbox"' in response.data
        assert b'role="dialog"' in response.data
        assert b'aria-modal="true"' in response.data

    def test_lightbox_buttons_present(self, client, test_collection_with_files):
        """Test navigation buttons are present."""
        collection, files = test_collection_with_files

        response = client.get(url_for('collections.view', uuid=collection.uuid))

        # Check for buttons
        assert b'lightbox-close' in response.data
        assert b'lightbox-prev' in response.data
        assert b'lightbox-next' in response.data

    def test_gallery_items_have_data_attributes(self, client, test_collection_with_files):
        """Test gallery items have required data attributes."""
        collection, files = test_collection_with_files

        response = client.get(url_for('collections.view', uuid=collection.uuid))
        html = response.data.decode('utf-8')

        # Check for data attributes on gallery items
        assert 'data-lightbox-index' in html
        assert 'data-file-uuid' in html
        assert 'data-file-name' in html
        assert 'data-full-url' in html

    def test_thumbnails_have_lightbox_trigger(self, client, test_collection_with_files):
        """Test thumbnails have role=button for lightbox."""
        collection, files = test_collection_with_files

        response = client.get(url_for('collections.view', uuid=collection.uuid))
        html = response.data.decode('utf-8')

        # Gallery thumbnail should be clickable
        assert 'role="button"' in html
        assert 'tabindex="0"' in html


class TestLightboxAccessibility:
    """Test accessibility features."""

    def test_aria_labels_present(self, client, test_collection_with_files):
        """Test ARIA labels on interactive elements."""
        collection, files = test_collection_with_files

        response = client.get(url_for('collections.view', uuid=collection.uuid))
        html = response.data.decode('utf-8')

        # Check for ARIA labels
        assert 'aria-label="Close lightbox' in html
        assert 'aria-label="Previous image' in html
        assert 'aria-label="Next image' in html

    def test_live_region_exists(self, client, test_collection_with_files):
        """Test live region for screen reader announcements."""
        collection, files = test_collection_with_files

        response = client.get(url_for('collections.view', uuid=collection.uuid))
        html = response.data.decode('utf-8')

        # Check for ARIA live region
        assert 'aria-live="polite"' in html
        assert 'id="lightbox-status"' in html


class TestLightboxIntegration:
    """Test lightbox integrates with collection view."""

    def test_empty_collection_has_no_lightbox_triggers(self, client, test_collection):
        """Test empty collections don't have lightbox triggers."""
        response = client.get(url_for('collections.view', uuid=test_collection.uuid))
        html = response.data.decode('utf-8')

        # Should have lightbox container (always present)
        assert 'id="lightbox"' in html

        # But no gallery items to trigger it
        assert 'gallery-item' not in html
        assert 'lightbox-trigger' not in html

    def test_single_image_collection(self, client, test_collection_with_one_file):
        """Test collection with single image."""
        collection, file = test_collection_with_one_file

        response = client.get(url_for('collections.view', uuid=collection.uuid))
        html = response.data.decode('utf-8')

        # Should have one gallery item
        assert html.count('data-lightbox-index="0"') == 1

        # Counter should show "1 of 1"
        assert 'lightbox-counter' in html

    def test_css_loaded(self, client, test_collection):
        """Test lightbox CSS is linked."""
        response = client.get(url_for('collections.view', uuid=test_collection.uuid))
        html = response.data.decode('utf-8')

        # Check for CSS link
        assert 'lightbox.css' in html

    def test_javascript_loaded(self, client, test_collection):
        """Test lightbox JS is linked."""
        response = client.get(url_for('collections.view', uuid=test_collection.uuid))
        html = response.data.decode('utf-8')

        # Check for JS link
        assert 'lightbox.js' in html
        assert 'defer' in html


class TestLightboxFileUrls:
    """Test that file URLs are correct."""

    def test_full_image_urls_generated(self, client, test_collection_with_files):
        """Test full image URLs use correct endpoint."""
        collection, files = test_collection_with_files

        response = client.get(url_for('collections.view', uuid=collection.uuid))
        html = response.data.decode('utf-8')

        # Check that full URLs use serve_file endpoint
        for file in files:
            expected_url = url_for('collections.serve_file', file_uuid=file.uuid)
            assert expected_url in html
```

**Run tests:**
```bash
# Run lightbox tests only
.venv/bin/python -m pytest tests/views/test_lightbox.py -v

# Run all collection tests
.venv/bin/python -m pytest tests/collections/ -v

# Run with coverage
.venv/bin/python -m pytest tests/views/test_lightbox.py --cov=app/views/collections
```

---

## Common Mistakes & Pitfalls

### 1. Focus Management

**❌ WRONG:**
```javascript
function openLightbox() {
  DOM.lightbox.classList.add('active');
  // Forgot to move focus!
}
```

**✅ CORRECT:**
```javascript
function openLightbox() {
  LightboxState.previousFocus = document.activeElement; // Save
  DOM.lightbox.classList.add('active');
  DOM.closeBtn.focus(); // Move focus to lightbox
}

function closeLightbox() {
  DOM.lightbox.classList.remove('active');
  LightboxState.previousFocus?.focus(); // Restore
}
```

**Why?**
- Keyboard users lose their place without focus management
- Screen reader users don't know lightbox opened
- WCAG 2.1 requirement

---

### 2. Body Scroll Lock

**❌ WRONG:**
```css
/* Just hiding overflow */
body.lightbox-open {
  overflow: hidden;
}
```

**Problem:** Page content shifts when scrollbar disappears

**✅ CORRECT:**
```css
body.lightbox-open {
  overflow: hidden;
  padding-right: var(--scrollbar-width, 0);
}
```

```javascript
// Calculate and set scrollbar width
const scrollbarWidth = calculateScrollbarWidth();
document.body.style.setProperty('--scrollbar-width', `${scrollbarWidth}px`);
```

---

### 3. Event Listener Leaks

**❌ WRONG:**
```javascript
function openLightbox() {
  document.addEventListener('keydown', handleKeyboard);
}

function closeLightbox() {
  // Forgot to remove! Listener persists, causes bugs
}
```

**✅ CORRECT:**
```javascript
let keyboardHandler = null;

function openLightbox() {
  keyboardHandler = (e) => handleKeyboard(e);
  document.addEventListener('keydown', keyboardHandler);
}

function closeLightbox() {
  if (keyboardHandler) {
    document.removeEventListener('keydown', keyboardHandler);
    keyboardHandler = null;
  }
}
```

---

### 4. Image Loading Race Condition

**❌ WRONG:**
```javascript
function loadImage(url) {
  DOM.image.src = url; // Start loading
  DOM.image.style.display = 'block'; // Show immediately
  // Image might not be loaded yet! Broken image icon appears
}
```

**✅ CORRECT:**
```javascript
function loadImage(url) {
  DOM.loader.classList.add('active'); // Show spinner
  DOM.image.style.display = 'none'; // Hide until loaded
  DOM.image.src = url; // Start loading
}

DOM.image.addEventListener('load', () => {
  DOM.loader.classList.remove('active'); // Hide spinner
  DOM.image.style.display = 'block'; // Show image
  DOM.image.classList.add('loaded'); // Trigger fade-in
});
```

---

### 5. Touch Event Conflicts

**❌ WRONG:**
```javascript
element.addEventListener('click', handleClick);
element.addEventListener('touchend', handleTouch);
// Both fire on mobile! Double-triggers
```

**✅ CORRECT:**
```javascript
// Let click handle both desktop and mobile
element.addEventListener('click', handleClick);

// Use touch only for gestures (swipe)
element.addEventListener('touchstart', handleTouchStart, { passive: true });
element.addEventListener('touchend', handleTouchEnd, { passive: true });
```

---

### 6. CSS Z-Index Stacking Issues

**❌ WRONG:**
```css
.lightbox {
  z-index: 100;
}
.navbar {
  z-index: 1000; /* Higher! Appears on top of lightbox */
}
```

**✅ CORRECT:**
```css
/* Use very high z-index for modals */
.lightbox {
  z-index: 9999;
}

/* Or use CSS stacking context */
.lightbox {
  position: fixed;
  isolation: isolate; /* Creates new stacking context */
  z-index: 1000;
}
```

---

### 7. Not Handling Broken Images

**❌ WRONG:**
```javascript
// No error handler, broken images crash lightbox
DOM.image.src = url;
```

**✅ CORRECT:**
```javascript
DOM.image.addEventListener('error', () => {
  DOM.loader.classList.remove('active');
  console.error('Failed to load image:', url);
  announceToScreenReader('Failed to load image');
  // Keep lightbox open so user can navigate away
});

DOM.image.src = url;
```

---

### 8. Hardcoding URLs Instead of Using `url_for()`

**❌ WRONG:**
```html
<img data-full-url="/collections/files/{{ file.uuid }}">
```

**✅ CORRECT:**
```html
<img data-full-url="{{ url_for('collections.serve_file', file_uuid=file.uuid) }}">
```

**Why?**
- `url_for()` respects Flask blueprints and URL prefixes
- Routes might change, hardcoded URLs break
- Works correctly in different deployment environments

---

### 9. Missing Null Checks

**❌ WRONG:**
```javascript
DOM.counter.textContent = `${current} of ${total}`;
// Crashes if counter element doesn't exist
```

**✅ CORRECT:**
```javascript
if (DOM.counter) {
  DOM.counter.textContent = `${current} of ${total}`;
}

// Or use optional chaining
DOM.counter?.textContent = `${current} of ${total}`;
```

---

### 10. Not Testing with Real Images

**❌ WRONG:**
Testing with only small, fast-loading images

**✅ CORRECT:**
Test with:
- Large images (5MB+) to test loading states
- Slow network (Chrome DevTools throttling)
- Broken URLs to test error handling
- Different aspect ratios (portrait, landscape, square)
- Various formats (JPG, PNG, WEBP)

---

## Best Practices

### Code Organization

1. **Separate Concerns**:
   - HTML: Structure only
   - CSS: Presentation only
   - JavaScript: Behavior only

2. **Use Constants**:
   ```javascript
   const SWIPE_THRESHOLD = 50;
   const ANIMATION_DURATION = 300;
   const KEY_CODES = { ESCAPE: 'Escape', ARROW_LEFT: 'ArrowLeft' };
   ```

3. **Comment Complex Logic**:
   ```javascript
   // Calculate swipe direction
   // Negative diff = swipe right = previous image
   // Positive diff = swipe left = next image
   const diff = touchStartX - touchEndX;
   ```

4. **Use Meaningful Names**:
   - ❌ `function f1()`, `let x`, `const tmp`
   - ✅ `function openLightbox()`, `let currentIndex`, `const scrollbarWidth`

### Performance

1. **Cache DOM Queries**:
   ```javascript
   // ❌ Bad: Query every time
   function update() {
     document.getElementById('counter').textContent = '5 of 10';
     document.getElementById('counter').style.display = 'block';
   }

   // ✅ Good: Query once
   const counter = document.getElementById('counter');
   function update() {
     counter.textContent = '5 of 10';
     counter.style.display = 'block';
   }
   ```

2. **Use CSS Transitions Instead of JavaScript**:
   ```css
   /* ✅ Good: GPU accelerated */
   .lightbox {
     opacity: 0;
     transition: opacity 300ms;
   }
   .lightbox.active {
     opacity: 1;
   }

   /* ❌ Bad: JavaScript animation */
   ```

3. **Debounce Expensive Operations**:
   ```javascript
   // If handling resize events
   let resizeTimeout;
   window.addEventListener('resize', () => {
     clearTimeout(resizeTimeout);
     resizeTimeout = setTimeout(handleResize, 250);
   });
   ```

### Accessibility

1. **Always Provide Text Alternatives**:
   - Buttons: `aria-label`
   - Icons: `aria-hidden="true"` (decorative)
   - Images: `alt` attribute
   - Dynamic changes: `aria-live` regions

2. **Keyboard Navigation First**:
   - Build with keyboard, add mouse later
   - Test with Tab, Arrow keys, Enter, Escape
   - Ensure all actions have keyboard equivalents

3. **Focus Indicators**:
   - Never `outline: none` without replacement
   - Use `:focus-visible` for better UX
   - Ensure 3:1 contrast ratio for focus indicators

4. **Test with Screen Reader**:
   - NVDA (Windows, free)
   - JAWS (Windows, paid)
   - VoiceOver (Mac, built-in)
   - TalkBack (Android, built-in)

### Security

1. **Escape User Content**:
   ```javascript
   // Jinja2 auto-escapes, but if building HTML in JS:
   function escapeHtml(text) {
     const div = document.createElement('div');
     div.textContent = text;
     return div.innerHTML;
   }
   ```

2. **Validate Data Attributes**:
   ```javascript
   const index = parseInt(element.dataset.index, 10);
   if (isNaN(index) || index < 0) {
     console.error('Invalid index');
     return;
   }
   ```

3. **Don't Trust Client Data**:
   - Server-side permission checks (already implemented)
   - Client-side is for UX only, not security

---

## Accessibility Checklist

### WCAG 2.1 Level AA Requirements

- [ ] **1.1.1 Non-text Content**: All images have alt text
- [ ] **1.3.1 Info and Relationships**: Semantic HTML (role, aria-label)
- [ ] **1.4.3 Contrast**: 4.5:1 for text, 3:1 for UI components
- [ ] **1.4.11 Non-text Contrast**: Buttons, focus indicators visible
- [ ] **2.1.1 Keyboard**: All functionality keyboard accessible
- [ ] **2.1.2 No Keyboard Trap**: Can exit lightbox with Escape
- [ ] **2.4.3 Focus Order**: Logical focus order (close, prev, next, download)
- [ ] **2.4.7 Focus Visible**: Focus indicator always visible
- [ ] **3.2.2 On Input**: No unexpected behavior on interaction
- [ ] **4.1.2 Name, Role, Value**: All UI components have accessible names
- [ ] **4.1.3 Status Messages**: Loading/navigation announced

### Additional Accessibility Tests

- [ ] Works with Windows High Contrast Mode
- [ ] Works with browser zoom (200%)
- [ ] Works with screen magnifier
- [ ] Respects `prefers-reduced-motion`
- [ ] Works with voice control (Dragon NaturallySpeaking)

---

## Performance Considerations

### Load Time Optimization

1. **Inline Critical CSS** (Optional):
   ```html
   <style>
   /* Only critical lightbox styles */
   .lightbox { display: none; position: fixed; }
   </style>
   <link rel="stylesheet" href="lightbox.css">
   ```

2. **Lazy Load JavaScript**:
   ```html
   <script src="lightbox.js" defer></script>
   ```

3. **Preload First Image** (Advanced):
   ```html
   <link rel="preload"
         href="{{ url_for('collections.serve_file', file_uuid=first_file.uuid) }}"
         as="image">
   ```

### Runtime Performance

1. **Use CSS Transforms** (GPU accelerated):
   ```css
   /* ✅ Fast */
   transform: translateX(10px);
   opacity: 0.5;

   /* ❌ Slow */
   left: 10px;
   display: none/block;
   ```

2. **Avoid Layout Thrashing**:
   ```javascript
   // ❌ Bad: Read-write-read-write causes multiple reflows
   element1.style.width = element2.offsetWidth + 'px';
   element3.style.height = element4.offsetHeight + 'px';

   // ✅ Good: Batch reads, then batch writes
   const width = element2.offsetWidth;
   const height = element4.offsetHeight;
   element1.style.width = width + 'px';
   element3.style.height = height + 'px';
   ```

3. **Use `will-change` Sparingly**:
   ```css
   /* Only on elements that will animate */
   .lightbox-image {
     will-change: opacity;
   }

   /* Remove after animation */
   .lightbox-image.loaded {
     will-change: auto;
   }
   ```

### Metrics to Monitor

- **Time to Interactive (TTI)**: < 5 seconds
- **First Contentful Paint (FCP)**: < 1.8 seconds
- **Largest Contentful Paint (LCP)**: < 2.5 seconds
- **Cumulative Layout Shift (CLS)**: < 0.1
- **Interaction to Next Paint (INP)**: < 200ms

Use Chrome DevTools Lighthouse to measure:
```bash
# Open collection page in Chrome
# F12 → Lighthouse tab → Analyze page load
```

---

## Troubleshooting Guide

### Issue: Lightbox doesn't open when clicking thumbnail

**Possible causes:**

1. **JavaScript not loaded**:
   ```javascript
   // Check console for errors
   // Verify: View Page Source → search for "lightbox.js"
   ```

2. **Event listeners not attached**:
   ```javascript
   // Add debug logging to initLightbox()
   console.log('Lightbox initialized with', LightboxState.files.length, 'images');
   ```

3. **Data attributes missing**:
   ```html
   <!-- Check HTML has: -->
   <div class="gallery-item"
        data-lightbox-index="0"
        data-file-uuid="..."
        data-full-url="...">
   ```

4. **JavaScript errors**:
   - Open browser console (F12)
   - Look for red error messages
   - Fix syntax errors or missing semicolons

**Solution:**
- Check browser console for errors
- Verify JavaScript file is linked correctly
- Inspect HTML to confirm data attributes present
- Test in different browser to rule out browser-specific bug

---

### Issue: Keyboard navigation doesn't work

**Possible causes:**

1. **Event listener not attached**:
   ```javascript
   // Check if keyboardHandler exists
   console.log('Keyboard handler:', LightboxState.keyboardHandler);
   ```

2. **Focus not on lightbox**:
   - Click inside lightbox first
   - Or ensure close button receives focus

3. **Event propagation stopped**:
   - Check for `event.stopPropagation()` calls
   - Ensure keyboard events bubble up

**Solution:**
```javascript
// Debug: Log all keyboard events
document.addEventListener('keydown', (e) => {
  console.log('Key pressed:', e.key, 'Lightbox open:', LightboxState.isOpen);
});
```

---

### Issue: Images don't load / show broken icon

**Possible causes:**

1. **Incorrect URL**:
   ```javascript
   // Check console for 404 errors
   // Verify URL format: /collections/files/<uuid>
   console.log('Loading URL:', file.url);
   ```

2. **Permissions issue**:
   - Check Flask logs for 403 Forbidden
   - Verify password-protected collection access
   - Confirm user session

3. **CORS issue** (if using CDN):
   - Check browser console for CORS errors
   - Verify server sends correct CORS headers

**Solution:**
- Inspect Network tab in DevTools
- Click on failed image request
- Check Response headers and status code
- Verify URL matches Flask route

---

### Issue: Lightbox appears behind other elements

**Cause:** Z-index stacking context issue

**Solution:**
```css
.lightbox {
  z-index: 9999; /* Very high value */
  position: fixed; /* Required for z-index */
  isolation: isolate; /* Creates new stacking context */
}
```

---

### Issue: Body scrolling still works with lightbox open

**Cause:** `overflow: hidden` not applied or insufficient

**Solution:**
```css
body.lightbox-open {
  overflow: hidden;
  position: fixed; /* More aggressive */
  width: 100%;
  height: 100%;
}
```

---

### Issue: Focus trap not working

**Possible causes:**

1. **Focusable elements not found**:
   ```javascript
   console.log('Focusable:', LightboxState.focusableElements.length);
   ```

2. **Tab handler not called**:
   ```javascript
   // Add debug logging
   function handleFocusTrap(event) {
     console.log('Trap triggered', event.target);
     // ...
   }
   ```

**Solution:**
- Ensure buttons aren't disabled
- Check `tabindex` attributes
- Verify keyboard handler attached

---

### Issue: Mobile swipe gestures not working

**Possible causes:**

1. **Touch events not firing**:
   ```javascript
   // Add debug logging
   function handleTouchStart(e) {
     console.log('Touch start:', e.changedTouches[0].screenX);
     // ...
   }
   ```

2. **Swipe threshold too high**:
   ```javascript
   const SWIPE_THRESHOLD = 50; // Try lowering to 30
   ```

3. **Browser native gestures interfering**:
   ```css
   .lightbox-image {
     touch-action: pan-y; /* Allow vertical scroll, block horizontal */
   }
   ```

**Solution:**
- Test on actual device (not desktop emulation)
- Check if events logged in console
- Verify no `event.preventDefault()` blocking touches

---

## Summary & Next Steps

### What You've Built

A fully-functional, accessible lightbox modal viewer with:
- ✅ Click-to-open full-size images
- ✅ Keyboard navigation (arrows, Escape)
- ✅ Touch gestures (swipe)
- ✅ Loading states
- ✅ Image metadata display
- ✅ WCAG 2.1 AA compliant
- ✅ Mobile responsive
- ✅ Cross-browser compatible

### Files Created/Modified

**Created:**
- `app/views/collections/static/css/lightbox.css`
- `app/views/collections/static/js/lightbox.js`
- `tests/views/test_lightbox.py`

**Modified:**
- `app/views/collections/templates/collections/view.html`

### Testing Your Implementation

1. **Visual test**: Open collection, click thumbnails
2. **Keyboard test**: Navigate with arrow keys
3. **Mobile test**: Swipe on phone/tablet
4. **Accessibility test**: Use screen reader, keyboard-only
5. **Automated test**: Run pytest suite

### Deployment Checklist

- [ ] CSS file created with all styles
- [ ] JavaScript file created with all functionality
- [ ] HTML template updated with lightbox markup
- [ ] Data attributes added to gallery items
- [ ] CSS file linked in template
- [ ] JavaScript file linked with `defer`
- [ ] Manual testing completed
- [ ] Automated tests pass
- [ ] Accessibility verified
- [ ] Mobile testing completed
- [ ] Cross-browser testing completed
- [ ] Code reviewed
- [ ] Git committed with descriptive message

### Future Enhancements (Out of Scope for Now)

1. **Image zoom**: Pinch-to-zoom, double-click zoom
2. **Slideshow mode**: Auto-advance with timer
3. **Thumbnails strip**: Show all thumbs at bottom for quick navigation
4. **Sharing**: Share individual images, not just collection
5. **Keyboard shortcuts**: Number keys to jump to image
6. **History API**: Update URL when navigating images
7. **Fullscreen mode**: Truly fullscreen (no browser UI)
8. **EXIF data display**: Camera settings, GPS, etc.
9. **Image comparison**: Side-by-side view
10. **Bulk actions from lightbox**: Delete, download multiple

### Getting Help

If stuck:
1. Check browser console for errors
2. Review Troubleshooting Guide above
3. Test in different browser to isolate issue
4. Simplify code: Comment out sections to find problem
5. Add `console.log()` statements to trace execution
6. Check Network tab for failed requests
7. Use debugger: Add `debugger;` statement and step through code

---

**Document Version:** 1.0
**Last Updated:** 2025-09-29
**Author:** The Open Harbor Team
**Reviewer:** [Pending Senior Developer Review]