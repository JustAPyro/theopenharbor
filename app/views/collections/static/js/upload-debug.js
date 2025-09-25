// Debug version of upload.js to test basic functionality
console.log('DEBUG: Upload debug script loaded');

document.addEventListener('DOMContentLoaded', function() {
    console.log('DEBUG: DOM loaded, setting up basic file upload');

    const fileInput = document.getElementById('fileInput');
    const uploadZone = document.getElementById('uploadZone');
    const browseButton = document.getElementById('browseButton');

    console.log('DEBUG: Elements found:', {
        fileInput: !!fileInput,
        uploadZone: !!uploadZone,
        browseButton: !!browseButton
    });

    if (fileInput) {
        fileInput.addEventListener('change', function(e) {
            console.log('DEBUG: File input changed');
            console.log('DEBUG: Files selected:', e.target.files.length);

            for (let i = 0; i < e.target.files.length; i++) {
                const file = e.target.files[i];
                console.log('DEBUG: File', i, ':', file.name, file.type, file.size);
            }

            if (e.target.files.length > 0) {
                alert(`Selected ${e.target.files.length} files! Check console for details.`);
            }
        });
    }

    if (uploadZone) {
        uploadZone.addEventListener('click', function(e) {
            console.log('DEBUG: Upload zone clicked');
            if (fileInput) {
                fileInput.click();
            }
        });
    }

    if (browseButton) {
        browseButton.addEventListener('click', function(e) {
            console.log('DEBUG: Browse button clicked');
            e.stopPropagation();
            if (fileInput) {
                fileInput.click();
            }
        });
    }
});