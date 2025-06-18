document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('intakeForm');
    const loading = document.getElementById('loading');
    const result = document.getElementById('result');
    const utilityProvider = document.getElementById('utility_provider');
    const poidField = document.getElementById('poid');
    const poidRequired = document.getElementById('poid_required');
    const poidHint = document.getElementById('poid_hint');
    
    // File upload elements
    const uploadArea = document.getElementById('uploadArea');
    const fileInputMobile = document.getElementById('utility_bill');
    const fileInputDesktop = document.getElementById('utility_bill_desktop');
    const fileInfo = document.getElementById('fileInfo');
    
    // Handle POID requirement based on utility selection
    utilityProvider.addEventListener('change', function() {
        const requiresPOID = ['NYSEG', 'RG&E'].includes(this.value);
        
        if (requiresPOID) {
            poidField.setAttribute('required', '');
            poidRequired.style.display = 'inline';
            poidHint.textContent = 'Point of Delivery ID (required for this utility)';
            poidHint.style.color = '#d9534f';
        } else {
            poidField.removeAttribute('required');
            poidRequired.style.display = 'none';
            poidHint.textContent = 'Point of Delivery ID (optional)';
            poidHint.style.color = '#666';
        }
    });
    
    // File upload functionality - handle both mobile and desktop
    function setupFileUploads() {
        // Mobile file input handler
        if (fileInputMobile) {
            fileInputMobile.addEventListener('change', function(e) {
                console.log('Mobile file input changed:', e.target.files);
                if (e.target.files.length > 0) {
                    // Sync to desktop input and update UI
                    if (fileInputDesktop) {
                        fileInputDesktop.files = e.target.files;
                    }
                    updateFileInfo(e.target.files[0]);
                }
            });
        }
        
        // Desktop file input handler
        if (fileInputDesktop) {
            fileInputDesktop.addEventListener('change', function(e) {
                console.log('Desktop file input changed:', e.target.files);
                if (e.target.files.length > 0) {
                    // Sync to mobile input and update UI
                    if (fileInputMobile) {
                        fileInputMobile.files = e.target.files;
                    }
                    updateFileInfo(e.target.files[0]);
                }
            });
        }
        
        // Desktop drag and drop functionality
        if (uploadArea && fileInputDesktop) {
            // Click to upload (desktop only)
            uploadArea.addEventListener('click', function() {
                fileInputDesktop.click();
            });
            
            // Prevent default drag behaviors
            ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
                uploadArea.addEventListener(eventName, preventDefaults, false);
                document.body.addEventListener(eventName, preventDefaults, false);
            });
            
            // Highlight drop area when item is dragged over it
            ['dragenter', 'dragover'].forEach(eventName => {
                uploadArea.addEventListener(eventName, highlight, false);
            });
            
            ['dragleave', 'drop'].forEach(eventName => {
                uploadArea.addEventListener(eventName, unhighlight, false);
            });
            
            // Handle dropped files
            uploadArea.addEventListener('drop', handleDrop, false);
        }
        
        function preventDefaults(e) {
            e.preventDefault();
            e.stopPropagation();
        }
        
        function highlight(e) {
            uploadArea.classList.add('dragover');
        }
        
        function unhighlight(e) {
            uploadArea.classList.remove('dragover');
        }
        
        function handleDrop(e) {
            const dt = e.dataTransfer;
            const files = dt.files;
            
            if (files.length > 0) {
                // Set files on both inputs to keep them synced
                if (fileInputDesktop) fileInputDesktop.files = files;
                if (fileInputMobile) fileInputMobile.files = files;
                updateFileInfo(files[0]);
            }
        }
        
        function updateFileInfo(file) {
            const maxSize = 16 * 1024 * 1024; // 16MB
            const allowedTypes = ['pdf', 'jpg', 'jpeg', 'png'];
            const fileExt = file.name.split('.').pop().toLowerCase();
            
            console.log('Updating file info for:', file.name, 'Type:', file.type, 'Size:', file.size);
            
            if (file.size > maxSize) {
                fileInfo.innerHTML = '<span style="color: #d9534f;">❌ File too large (max 16MB)</span>';
                fileInfo.style.display = 'block';
                return false;
            }
            
            if (!allowedTypes.includes(fileExt)) {
                fileInfo.innerHTML = '<span style="color: #d9534f;">❌ Invalid file type (PDF, JPG, PNG only)</span>';
                fileInfo.style.display = 'block';
                return false;
            }
            
            fileInfo.innerHTML = `<span style="color: #5cb85c;">✅ Ready: ${file.name} (${(file.size/1024/1024).toFixed(1)}MB)</span>`;
            fileInfo.style.display = 'block';
            return true;
        }
    }
    
    // Initialize file upload handlers
    setupFileUploads();
    
    form.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const formData = new FormData(form);
        
        form.style.display = 'none';
        loading.style.display = 'block';
        result.style.display = 'none';
        
        try {
            const response = await fetch('/submit', {
                method: 'POST',
                body: formData
            });
            
            const data = await response.json();
            
            loading.style.display = 'none';
            result.style.display = 'block';
            
            if (response.ok) {
                result.className = 'result success';
                result.innerHTML = `
                    <h3>Submission Successful!</h3>
                    <p>Your application has been processed successfully.</p>
                    <p><strong>Drive Folder:</strong> ${data.drive_folder}</p>
                    <p><strong>Documents:</strong></p>
                    <ul>
                        <li><a href="${data.documents.utility_bill}" target="_blank">Utility Bill</a></li>
                        <li><a href="${data.documents.poa}" target="_blank">Power of Attorney</a></li>
                        <li><a href="${data.documents.agreement}" target="_blank">Community Solar Agreement</a></li>
                    </ul>
                    <button onclick="location.reload()" style="margin-top: 20px;">Submit Another</button>
                `;
            } else {
                result.className = 'result error';
                result.innerHTML = `
                    <h3>Error</h3>
                    <p>${data.error || 'An error occurred processing your submission.'}</p>
                    <button onclick="location.reload()" style="margin-top: 20px;">Try Again</button>
                `;
            }
        } catch (error) {
            loading.style.display = 'none';
            result.style.display = 'block';
            result.className = 'result error';
            result.innerHTML = `
                <h3>Error</h3>
                <p>Network error: ${error.message}</p>
                <button onclick="location.reload()" style="margin-top: 20px;">Try Again</button>
            `;
        }
    });
});