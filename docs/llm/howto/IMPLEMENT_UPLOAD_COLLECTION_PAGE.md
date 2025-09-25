# Technical Requirements: Collection Upload Page

## Overview & Context

This document outlines the technical requirements for implementing a "Collection Upload" page for The Open Harbor - a photographer-focused file sharing platform. The page allows users to upload batches of photos to create shareable galleries.

**Target Users**: Professional photographers, creatives, small studios
**Backend**: Cloudflare R2 storage with multipart upload support
**Brand**: Minimal, sleek design prioritizing user experience
**Skill Level**: Document written for junior developer implementation

---

## Page Architecture & Layout

### Route & Navigation
- **Route**: `/collections/upload` or `/upload/collection`
- **Page Title**: "Upload Collection"
- **Breadcrumb**: Home > Upload Collection
- **Authentication**: Requires logged-in user

### Overall Page Structure
```
[Header/Navigation]
[Upload Zone - Primary Focus]
[Collection Settings Panel]
[Upload Progress Area]
[Action Buttons]
[Footer]
```

---

## Design System Integration

### Colors (Exact Brand Compliance)
```css
:root {
  --color-primary: #1E5F74;    /* Harbor Trust - primary actions */
  --color-beacon: #F4A259;     /* Beacon Light - secondary CTAs */
  --color-anchor: #2E2E2E;     /* Text and icons */
  --color-bg: #F9F7F3;         /* Page background */
  --color-horizon: #A3C9E2;    /* Subtle highlights */
  --color-white: #FFFFFF;      /* Cards and input backgrounds */
}
```

### Typography
- **Headers**: Poppins (600 weight)
- **Body Text**: Inter (400 weight)
- **Labels**: Inter (500 weight)
- **Error Text**: Inter (400 weight)

### Spacing System (8px Grid)
- Base unit: `8px`
- Scale: `4px, 8px, 16px, 24px, 32px, 48px, 64px`
- Component padding: `16px` (forms), `24px` (cards)
- Section margins: `48px` (mobile), `64px` (desktop)

---

## Component Requirements

### 1. Upload Zone (Primary Component)

**Visual Design**:
```css
.upload-zone {
  min-height: 320px;
  border: 2px dashed var(--color-horizon);
  border-radius: 12px;
  background: var(--color-white);
  padding: 48px 24px;
  text-align: center;
  transition: all 200ms ease;
  cursor: pointer;
}

.upload-zone--active {
  border-color: var(--color-primary);
  background: rgba(30, 95, 116, 0.02);
  transform: scale(1.01);
}

.upload-zone--error {
  border-color: #DC2626;
  background: rgba(220, 38, 38, 0.02);
}
```

**States & Behavior**:
1. **Default State**: Dashed border, upload icon, "Drag photos here or click to browse"
2. **Hover State**: Subtle lift effect (`translateY(-2px)`)
3. **Drag Active**: Border becomes solid primary color, background tint
4. **Error State**: Red border, error icon, error message
5. **Success State**: Green checkmark, file count

**Content Elements**:
- Large upload icon (48px, using `--color-horizon`)
- Primary heading: "Drag photos here or click to browse"
- Subtitle: "Upload JPG, PNG, HEIC, or RAW files up to 50MB each"
- File format icons (small, subtle)
- Browse button (secondary style)

**Interaction Requirements**:
- Click anywhere to trigger file browser
- Support drag-and-drop for multiple files
- Keyboard accessible (Tab + Enter/Space)
- Screen reader announcements

### 2. File Preview Grid

**Layout**:
- CSS Grid: `repeat(auto-fill, minmax(120px, 1fr))`
- Gap: `16px`
- Max 6 columns on desktop, 3 on mobile

**Individual File Card**:
```css
.file-card {
  position: relative;
  aspect-ratio: 1;
  border-radius: 8px;
  background: var(--color-white);
  box-shadow: 0 2px 8px rgba(30, 95, 116, 0.06);
  overflow: hidden;
}
```

**Card Elements**:
- Thumbnail image (covers full card)
- Loading overlay with progress bar
- Remove button (top-right, 32x32px minimum)
- Error state overlay (red tint + error icon)
- File name tooltip on hover

### 3. Collection Settings Panel

**Panel Design**:
- Card style with `border-radius: 12px`
- Background: `var(--color-white)`
- Padding: `24px`
- Margin top: `32px`

**Form Fields**:
1. **Collection Name** (required)
   - Input type: text
   - Placeholder: "Enter collection name"
   - Max length: 100 characters
   - Real-time character counter

2. **Description** (optional)
   - Textarea, 3 rows
   - Placeholder: "Add a description for your collection"
   - Max length: 500 characters

3. **Privacy Settings**
   - Radio buttons: Public, Unlisted, Password Protected
   - Default: Unlisted

4. **Expiration** (optional)
   - Dropdown: Never, 1 week, 1 month, 3 months, 1 year

### 4. Upload Progress Section

**Progress Indicator**:
```css
.upload-progress {
  width: 100%;
  height: 8px;
  background: var(--color-horizon);
  border-radius: 4px;
  overflow: hidden;
}

.upload-progress-bar {
  height: 100%;
  background: var(--color-primary);
  transition: width 200ms ease;
}
```

**Progress Information**:
- Overall progress percentage
- "Uploading X of Y files"
- Estimated time remaining
- Current upload speed

### 5. Action Buttons

**Button Layout**:
- Flexbox row, gap `16px`
- Mobile: Stack vertically

**Buttons**:
1. **Start Upload** (Primary CTA)
   - Style: `btn-primary`
   - Disabled until files selected
   - Text: "Start Upload" → "Uploading..." → "Upload Complete"

2. **Cancel** (Secondary)
   - Style: `btn-outline`
   - Visible during upload
   - Confirms cancellation

3. **Clear All** (Ghost)
   - Style: `btn-ghost`
   - Removes all selected files

---

## Technical Implementation Details

### File Handling Logic

**Supported File Types**:
```javascript
const ALLOWED_TYPES = [
  'image/jpeg',
  'image/jpg',
  'image/png',
  'image/heic',
  'image/tiff',
  'image/webp',
  'image/x-adobe-dng' // RAW format example
];
```

**File Validation**:
- Max file size: 50MB per file
- Max total size: 500MB per collection
- Max files per collection: 100
- Duplicate detection by filename + size

**Error Handling**:
- Invalid file type: "This file type isn't supported. Please use JPG, PNG, HEIC, or RAW files."
- File too large: "This file is too large. Maximum size is 50MB per file."
- Too many files: "Maximum 100 files per collection. Remove some files to continue."

### R2 Storage Integration

**Upload Strategy**:
1. Use multipart upload for files > 10MB
2. Parallel uploads (max 3 concurrent)
3. Chunked upload with progress tracking
4. Retry mechanism (3 attempts max)

**API Endpoints**:
- `POST /api/collections/create` - Initialize collection
- `POST /api/upload/presigned` - Get signed upload URLs
- `POST /api/collections/:id/finalize` - Complete upload

**Progress Tracking**:
```javascript
// Individual file progress
const fileProgress = {
  fileId: string,
  bytesUploaded: number,
  totalBytes: number,
  status: 'pending' | 'uploading' | 'complete' | 'error'
};

// Overall progress calculation
const overallProgress = files.reduce((acc, file) => {
  return acc + (file.bytesUploaded / file.totalBytes);
}, 0) / files.length * 100;
```

### Performance Optimizations

**Image Processing**:
- Generate thumbnails client-side using Canvas API
- Compress previews to 150x150px, 85% JPEG quality
- Original files upload unchanged

**Memory Management**:
- Revoke object URLs after thumbnail generation
- Implement file queue to prevent memory overflow
- Clean up FileReader instances

**Network Optimization**:
- Implement upload pausing/resuming
- Network error retry with exponential backoff
- Upload queue management (priority for smaller files)

---

## Accessibility Requirements

### Keyboard Navigation
- Upload zone: Focusable with Tab, activatable with Enter/Space
- File removal: Individual files focusable and removable with Delete key
- Form fields: Proper tab order, label associations
- Buttons: Clear focus indicators

### Screen Reader Support
```html
<!-- Upload zone -->
<div class="upload-zone"
     role="button"
     tabindex="0"
     aria-label="Upload photos to collection"
     aria-describedby="upload-instructions">

<div id="upload-instructions" class="sr-only">
  Drag and drop photos here, or press Enter to browse files.
  Supported formats: JPG, PNG, HEIC, RAW. Maximum 50MB per file.
</div>
```

**ARIA Labels**:
- Progress bars: `aria-valuenow`, `aria-valuemin`, `aria-valuemax`
- File removal: `aria-label="Remove [filename]"`
- Upload status: `aria-live="polite"` region for progress updates

### Color Contrast Compliance
- All text meets WCAG AA (4.5:1 contrast ratio)
- Focus indicators visible with 3:1 contrast
- Error states use both color and icons
- No color-only information conveyance

---

## Error Handling & Edge Cases

### Client-Side Error Scenarios

1. **Network Failure During Upload**
   - Show retry button
   - Preserve upload progress
   - Allow resume from last successful chunk

2. **File Corruption Detection**
   - Validate file headers
   - Show specific error per file
   - Allow individual file retry

3. **Quota Exceeded**
   - Show storage quota warning
   - Prevent additional uploads
   - Link to upgrade page

4. **Session Expiration**
   - Detect expired auth tokens
   - Pause uploads automatically
   - Show re-login modal
   - Resume after re-authentication

### Server-Side Error Handling

1. **R2 Storage Failures**
   - Retry with exponential backoff
   - Fall back to alternative storage regions
   - Partial upload recovery

2. **Database Connection Issues**
   - Queue metadata writes
   - Retry mechanism
   - Graceful degradation

### User Experience During Errors
- Clear, non-technical error messages
- Specific instructions for resolution
- Progress preservation where possible
- Support contact information for persistent issues

---

## Security Considerations

### File Upload Security
- Server-side file type validation (don't trust MIME types)
- Virus scanning integration (if available)
- File size limits enforced server-side
- Content-type validation

### Access Control
- Authenticate all upload requests
- Rate limiting: 10 uploads per minute per user
- CSRF protection on all forms
- Signed upload URLs with expiration

### Data Privacy
- No file content processing beyond thumbnail generation
- Metadata stripping optional (user choice)
- Secure deletion of temporary files
- GDPR compliance for user data

---

## Common Junior Developer Pitfalls & Solutions

### ⚠️ Critical Mistakes to Avoid

1. **Memory Leaks from FileReader**
   ```javascript
   // WRONG - Creates memory leaks
   files.forEach(file => {
     const reader = new FileReader();
     // reader never cleaned up
   });

   // CORRECT - Clean up resources
   const reader = new FileReader();
   reader.onload = () => {
     // process file
     reader.onload = null; // Clean up reference
   };
   ```

2. **Blocking UI Thread with Large Files**
   ```javascript
   // WRONG - Synchronous processing
   const processAllFiles = () => {
     files.forEach(processFile); // Blocks UI
   };

   // CORRECT - Async with chunking
   const processFilesAsync = async () => {
     for (const file of files) {
       await processFile(file);
       await new Promise(resolve => setTimeout(resolve, 0)); // Yield control
     }
   };
   ```

3. **Poor Progress Tracking**
   ```javascript
   // WRONG - Inaccurate progress
   const progress = uploadedCount / totalCount * 100;

   // CORRECT - Byte-based progress
   const progress = totalUploadedBytes / totalBytes * 100;
   ```

4. **Inadequate Error Handling**
   ```javascript
   // WRONG - Generic error handling
   upload.catch(error => {
     setError("Upload failed");
   });

   // CORRECT - Specific error handling
   upload.catch(error => {
     if (error.code === 'NetworkError') {
       setError("Connection lost. Check your internet and try again.");
     } else if (error.code === 'QuotaExceeded') {
       setError("Storage limit reached. Please upgrade your plan.");
     }
     // etc.
   });
   ```

5. **Accessibility Oversights**
   ```html
   <!-- WRONG - No keyboard access -->
   <div onClick={openFileDialog}>Upload</div>

   <!-- CORRECT - Keyboard accessible -->
   <button onClick={openFileDialog}
           onKeyDown={handleKeyDown}
           aria-label="Upload files">Upload</button>
   ```

### 🔧 Implementation Guidelines

**File Processing Order**:
1. Client-side validation first (fast feedback)
2. Generate thumbnails for preview
3. Server-side validation before upload
4. Upload files in order of size (small first)

**State Management Structure**:
```javascript
const uploadState = {
  files: Map<fileId, FileObject>,
  collection: CollectionSettings,
  upload: {
    status: 'idle' | 'uploading' | 'complete' | 'error',
    progress: number,
    currentFile: fileId,
    errors: Error[]
  }
};
```

**Component Organization**:
- Separate upload logic from UI components
- Custom hooks for file processing
- Context for upload state management
- Separate components for each UI section

---

## Testing Requirements

### Unit Testing Focus Areas
- File validation logic
- Progress calculation accuracy
- Error handling scenarios
- State management updates

### Integration Testing
- File upload flow end-to-end
- R2 storage integration
- Authentication handling
- Error recovery flows

### Accessibility Testing
- Keyboard navigation complete flows
- Screen reader announcements
- Focus management
- Color contrast verification

### Performance Testing
- Large file upload (50MB)
- Multiple file upload (100 files)
- Network interruption recovery
- Memory usage monitoring

---

## Success Metrics & Monitoring

### User Experience Metrics
- Upload success rate (target: >95%)
- Average upload completion time
- User abandonment rate during upload
- Error recovery success rate

### Technical Metrics
- R2 storage upload success rate
- Average chunk upload time
- Memory usage during uploads
- Failed upload retry success rate

### Business Metrics
- Collections created per user
- Photos per collection (average)
- Feature adoption rate
- User retention post-upload

---

## Deployment Considerations

### Environment Variables
```bash
R2_ACCOUNT_ID=
R2_ACCESS_KEY_ID=
R2_SECRET_ACCESS_KEY=
R2_BUCKET_NAME=
MAX_FILE_SIZE_MB=50
MAX_COLLECTION_SIZE_MB=500
MAX_FILES_PER_COLLECTION=100
```

### CDN Configuration
- Enable CORS for upload endpoints
- Configure proper cache headers for thumbnails
- Set up error pages for upload failures

### Monitoring & Alerts
- Upload failure rate alerts
- Storage quota monitoring
- R2 API error rate tracking
- User session timeout alerts

---

## Future Enhancement Considerations

### Phase 2 Features
- Batch editing (crop, rotate, filters)
- Automatic organization by date/location
- AI-powered tagging and search
- Advanced sharing permissions

### Performance Improvements
- WebRTC for peer-to-peer uploads
- Service Worker for offline queueing
- Progressive image loading
- Advanced chunking algorithms

### Integration Opportunities
- Adobe Lightroom plugin
- Camera import via USB
- Cloud storage connectors (Google Drive, Dropbox)
- Social media sharing integration

---

This document provides comprehensive technical requirements while highlighting potential pitfalls. The implementation should prioritize user experience, accessibility, and performance while maintaining The Open Harbor's minimal, photographer-focused brand identity.

For questions or clarifications, refer to the brand guidelines in `/docs/llm/brand.md` and existing component patterns in the codebase.