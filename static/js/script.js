document.addEventListener('DOMContentLoaded', function() {
    // DOM Elements
    const downloadForm = document.getElementById('downloadForm');
    const instagramUrlInput = document.getElementById('instagramUrl');
    const submitBtn = document.getElementById('submitBtn');
    const loader = document.getElementById('loader');
    const errorContainer = document.getElementById('errorContainer');
    const errorMessage = document.getElementById('errorMessage');
    const resultsContainer = document.getElementById('resultsContainer');
    const videoTitle = document.getElementById('videoTitle');
    const thumbnailContainer = document.getElementById('thumbnailContainer');
    const downloadBtn = document.getElementById('downloadBtn');
    const copyLinkBtn = document.getElementById('copyLinkBtn');
    const copyToast = document.getElementById('copyToast');

    // Initialize Bootstrap toast
    const toast = new bootstrap.Toast(copyToast);
    
    // Form submission handler
    downloadForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        // Get the Instagram URL
        const instagramUrl = instagramUrlInput.value.trim();
        
        // Validate URL (basic validation)
        if (!instagramUrl) {
            showError('Please enter an Instagram URL');
            return;
        }

        // Simple URL validation
        if (!isValidInstagramUrl(instagramUrl)) {
            showError('Please enter a valid Instagram post or reel URL');
            return;
        }
        
        // Reset UI state
        resetUI();
        
        // Show loader
        loader.classList.remove('d-none');
        submitBtn.disabled = true;
        
        try {
            // Call the API - log the URL for debugging
            console.log("Submitting URL:", instagramUrl);
            
            // Check which API endpoint to use
            let apiEndpoint = '/api/download';
            
            // If we're deployed on Railway, use the deployed API
            if (window.location.hostname !== 'localhost' && !window.location.hostname.includes('replit')) {
                apiEndpoint = 'https://insta99-production.up.railway.app/api/download';
                console.log("Using Railway API endpoint");
            }
            
            const response = await fetch(apiEndpoint, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ url: instagramUrl }),
            });
            
            console.log("API Response status:", response.status);
            
            // Log the raw response for debugging
            const responseText = await response.text();
            console.log("API Raw Response:", responseText);
            
            // Parse the JSON response
            let data;
            try {
                data = JSON.parse(responseText);
                console.log("Parsed JSON data:", data);
            } catch (e) {
                console.error("Failed to parse JSON:", e);
                throw new Error("Invalid JSON response from server");
            }
            
            // Hide loader
            loader.classList.add('d-none');
            submitBtn.disabled = false;
            
            // Handle the API response
            if (data.download_url) {
                // Show results
                videoTitle.textContent = 'Instagram Video';
                
                // Set download link
                downloadBtn.href = data.download_url;
                
                // No thumbnail available with simplified API
                thumbnailContainer.innerHTML = '<div class="alert alert-info">Video ready for download</div>';
                
                // Show results container
                resultsContainer.classList.remove('d-none');
            } else {
                // Show error message
                showError(data.error || 'Failed to extract download link');
            }
        } catch (error) {
            console.error('Error:', error);
            loader.classList.add('d-none');
            submitBtn.disabled = false;
            showError('An unexpected error occurred. Please try again.');
        }
    });
    
    // Copy link button handler
    copyLinkBtn.addEventListener('click', function() {
        if (downloadBtn.href) {
            navigator.clipboard.writeText(downloadBtn.href)
                .then(() => {
                    // Show toast notification
                    toast.show();
                })
                .catch(err => {
                    console.error('Failed to copy: ', err);
                    showError('Failed to copy link to clipboard');
                });
        }
    });
    
    // Function to show error message
    function showError(message) {
        errorMessage.textContent = message;
        errorContainer.classList.remove('d-none');
    }
    
    // Function to reset UI state
    function resetUI() {
        errorContainer.classList.add('d-none');
        resultsContainer.classList.add('d-none');
        thumbnailContainer.innerHTML = '';
    }
    
    // Function to validate Instagram URL
    function isValidInstagramUrl(url) {
        try {
            const parsedUrl = new URL(url);
            const hostname = parsedUrl.hostname;
            
            // Check if hostname is instagram.com or www.instagram.com
            if (hostname !== 'instagram.com' && hostname !== 'www.instagram.com') {
                return false;
            }
            
            // Check if path exists and matches Instagram post pattern
            const path = parsedUrl.pathname;
            const instagramRegex = /^\/(p|reel|tv)\/[a-zA-Z0-9_-]+\/?$/;
            
            return instagramRegex.test(path);
        } catch {
            // Invalid URL format
            return false;
        }
    }
});
