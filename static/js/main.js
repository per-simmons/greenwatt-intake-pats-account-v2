document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('intakeForm');
    const loading = document.getElementById('loading');
    const result = document.getElementById('result');
    
    // File upload elements
    const uploadArea = document.getElementById('uploadArea');
    const fileInput = document.getElementById('utility_bill');
    const fileInfo = document.getElementById('fileInfo');
    
    
    // File upload functionality - unified single input system
    function setupFileUploads() {
        // Single file input handler
        if (fileInput) {
            fileInput.addEventListener('change', function(e) {
                console.log('File input changed:', e.target.files);
                if (e.target.files.length > 0) {
                    updateFileInfo(e.target.files[0]);
                }
            });
        }
        
        // Upload area click and drag/drop functionality
        if (uploadArea && fileInput) {
            // Click to upload
            uploadArea.addEventListener('click', function() {
                fileInput.click();
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
            console.log('Drag enter/over detected');
            uploadArea.classList.add('dragover');
        }
        
        function unhighlight(e) {
            console.log('Drag leave/drop detected');
            uploadArea.classList.remove('dragover');
        }
        
        function handleDrop(e) {
            console.log('File dropped!');
            const dt = e.dataTransfer;
            const files = dt.files;
            
            if (files.length > 0) {
                console.log('Processing dropped file:', files[0].name);
                
                try {
                    // Modern approach: Create a new FileList-like object and assign it properly
                    const dataTransfer = new DataTransfer();
                    dataTransfer.items.add(files[0]);
                    fileInput.files = dataTransfer.files;
                    
                    // Trigger change event to ensure all handlers are called
                    const event = new Event('change', { bubbles: true });
                    fileInput.dispatchEvent(event);
                    
                    console.log('File successfully set via drag & drop (modern method)');
                } catch (error) {
                    console.log('DataTransfer not supported, using fallback method');
                    // Fallback: Store file reference and update UI manually
                    fileInput.droppedFile = files[0];
                    
                    // Create a custom change event with file data
                    const event = new CustomEvent('change', { 
                        bubbles: true,
                        detail: { droppedFile: files[0] }
                    });
                    fileInput.dispatchEvent(event);
                }
                
                updateFileInfo(files[0]);
                console.log('Drag & drop processing complete');
            }
        }
        
        function updateFileInfo(file) {
            const maxSize = 16 * 1024 * 1024; // 16MB
            const allowedTypes = ['pdf', 'jpg', 'jpeg', 'png'];
            const fileExt = file.name.split('.').pop().toLowerCase();
            
            console.log('Updating file info for:', file.name, 'Type:', file.type, 'Size:', file.size);
            console.log('File extension:', fileExt, 'Allowed types:', allowedTypes);
            
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
    
    // Real-time progress tracking variables
    let progressInterval = null;
    let progressStartTime = null;
    
    // Real-time progress polling function
    async function pollProgress(sessionId) {
        try {
            const response = await fetch(`/progress/${sessionId}`);
            const progress = await response.json();
            
            // Update progress UI elements
            updateProgressUI(progress);
            
            // Check if processing is complete
            if (progress.status === 'completed') {
                clearInterval(progressInterval);
                showCompletionResult(progress);
            } else if (progress.status === 'error') {
                clearInterval(progressInterval);
                showErrorResult(progress);
            }
        } catch (error) {
            console.error('Error polling progress:', error);
            // Continue polling on network errors (temporary issues)
        }
    }
    
    // Update progress UI with real-time data
    function updateProgressUI(progress) {
        const progressFill = document.getElementById('progressFill');
        const progressPercent = document.getElementById('progressPercent');
        const progressStep = document.getElementById('progressStep');
        const progressDescription = document.getElementById('progressDescription');
        
        // Update progress bar
        if (progressFill && progress.progress !== undefined) {
            progressFill.style.width = `${progress.progress}%`;
        }
        
        // Update percentage text
        if (progressPercent && progress.progress !== undefined) {
            progressPercent.textContent = `${Math.round(progress.progress)}%`;
        }
        
        // Update step name and description
        if (progressStep && progress.step_name) {
            progressStep.textContent = progress.step_name;
        }
        
        if (progressDescription && progress.description) {
            progressDescription.textContent = progress.description;
        }
    }
    
    
    // Show successful completion result
    function showCompletionResult(progress) {
        loading.style.display = 'none';
        result.style.display = 'block';
        result.className = 'result success';
        
        const data = progress.result_data || {};
        result.innerHTML = `
            <h3>Submission Successful!</h3>
            <p>Your application has been processed successfully.</p>
            <p><strong>Processing Time:</strong> ${formatElapsedTime()}</p>
            <p><strong>Drive Folder:</strong> ${data.drive_folder || 'Generated successfully'}</p>
            <p><strong>Documents:</strong></p>
            <ul>
                ${data.documents ? `
                    <li><a href="${data.documents.utility_bill}" target="_blank">Utility Bill</a></li>
                    <li><a href="${data.documents.poa}" target="_blank">Power of Attorney</a></li>
                    <li><a href="${data.documents.agreement}" target="_blank">Community Solar Agreement</a></li>
                ` : '<li>Documents generated and uploaded successfully</li>'}
            </ul>
            <button onclick="location.reload()" style="margin-top: 20px;">Submit Another</button>
        `;
    }
    
    // Show error result
    function showErrorResult(progress) {
        loading.style.display = 'none';
        result.style.display = 'block';
        result.className = 'result error';
        result.innerHTML = `
            <h3>Processing Error</h3>
            <p>${progress.error || 'An error occurred during processing.'}</p>
            <p><strong>Failed at:</strong> ${progress.step_name || 'Unknown step'}</p>
            <button onclick="location.reload()" style="margin-top: 20px;">Try Again</button>
        `;
    }
    
    // Format elapsed time for display
    function formatElapsedTime() {
        if (!progressStartTime) return 'Unknown';
        const elapsed = Math.floor((new Date() - progressStartTime) / 1000);
        const minutes = Math.floor(elapsed / 60);
        const seconds = elapsed % 60;
        return `${minutes}:${seconds.toString().padStart(2, '0')}`;
    }

    form.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const formData = new FormData(form);
        
        // Handle dropped files for browsers that don't support DataTransfer
        if (fileInput && fileInput.droppedFile && (!fileInput.files || fileInput.files.length === 0)) {
            console.log('Adding dropped file to form data:', fileInput.droppedFile.name);
            formData.set('utility_bill', fileInput.droppedFile);
        }
        
        // Hide form and show loading with progress tracking
        form.style.display = 'none';
        loading.style.display = 'block';
        result.style.display = 'none';
        
        // Initialize progress tracking
        progressStartTime = new Date();
        
        try {
            // Submit form and get session ID
            const response = await fetch('/submit', {
                method: 'POST',
                body: formData
            });
            
            const data = await response.json();
            
            if (response.ok && data.session_id) {
                // Start polling progress every 1 second
                progressInterval = setInterval(() => {
                    pollProgress(data.session_id);
                }, 1000);
                
                // Start with initial progress state
                updateProgressUI({
                    progress: 5
                });
            } else {
                // Handle immediate errors
                loading.style.display = 'none';
                result.style.display = 'block';
                result.className = 'result error';
                result.innerHTML = `
                    <h3>Submission Error</h3>
                    <p>${data.error || 'Failed to start processing.'}</p>
                    <button onclick="location.reload()" style="margin-top: 20px;">Try Again</button>
                `;
            }
        } catch (error) {
            loading.style.display = 'none';
            result.style.display = 'block';
            result.className = 'result error';
            result.innerHTML = `
                <h3>Network Error</h3>
                <p>Failed to submit form: ${error.message}</p>
                <button onclick="location.reload()" style="margin-top: 20px;">Try Again</button>
            `;
        }
    });
});