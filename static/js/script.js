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
            
            // Get cookies if provided
            const sessionidInput = document.getElementById('sessionid');
            const csrftokenInput = document.getElementById('csrftoken');
            const dsUserIdInput = document.getElementById('ds_user_id');
            
            // Prepare payload
            const payload = { 
                url: instagramUrl 
            };
            
            // Add cookies if provided (at least sessionid)
            if (sessionidInput && sessionidInput.value.trim()) {
                payload.cookies = {
                    sessionid: sessionidInput.value.trim(),
                    csrftoken: csrftokenInput ? csrftokenInput.value.trim() : '',
                    ds_user_id: dsUserIdInput ? dsUserIdInput.value.trim() : ''
                };
                console.log("Adding Instagram cookies to request");
            }
            
            const response = await fetch(apiEndpoint, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(payload),
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
            // Also allow URLs with query parameters
            const path = parsedUrl.pathname;
            const instagramRegex = /^\/(p|reel|tv)\/[a-zA-Z0-9_-]+\/?$/;
            
            return instagramRegex.test(path);
        } catch {
            // Invalid URL format
            return false;
        }
    }
    
    // Add direct download button handler
    const directMethodBtn = document.getElementById('direct-method-btn');
    
    if (directMethodBtn) {
        directMethodBtn.addEventListener('click', function() {
            // Validate URL
            const instagramUrl = document.getElementById('instagramUrl').value.trim();
            if (!instagramUrl) {
                showError('Please enter an Instagram URL first');
                return;
            }
            
            if (!isValidInstagramUrl(instagramUrl)) {
                showError('Please enter a valid Instagram URL');
                return;
            }
            
            // Show loader
            loader.classList.remove('d-none');
            
            // Call the API endpoint
            callApiDownload(instagramUrl);
        });
    }
    
    // Add alternative method button handler
    const alternativeMethodBtn = document.getElementById('alternative-method-btn');
    
    if (alternativeMethodBtn) {
        alternativeMethodBtn.addEventListener('click', function() {
            // Validate URL
            const instagramUrl = document.getElementById('instagramUrl').value.trim();
            if (!instagramUrl) {
                showError('Please enter an Instagram URL first');
                return;
            }
            
            // Create modified URL for alternative method
            const alternativeUrl = createAlternativeUrl(instagramUrl);
            
            // Show notification in the error container (reusing it for info)
            errorMessage.textContent = 'Opening reliable third-party downloader...';
            errorContainer.classList.remove('d-none');
            errorContainer.classList.remove('alert-danger');
            errorContainer.classList.add('alert-info');
            
            // Try the download with alternative method
            tryAlternativeDownload(alternativeUrl);
        });
    }
    
    // Function to call the API download endpoint
    async function callApiDownload(url) {
        try {
            // Check which API endpoint to use
            let apiEndpoint = '/api/download';
            
            // If we're deployed on Railway, use the deployed API
            if (window.location.hostname !== 'localhost' && !window.location.hostname.includes('replit')) {
                apiEndpoint = 'https://insta99-production.up.railway.app/api/download';
                console.log("Using Railway API endpoint");
            }
            
            console.log("Submitting URL:", url);
            
            // Make the API request
            const response = await fetch(apiEndpoint, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ url: url }),
            });
            
            console.log("API Response status:", response.status);
            
            // Parse the response
            const responseText = await response.text();
            console.log("API Raw Response:", responseText);
            
            let data;
            try {
                data = JSON.parse(responseText);
                console.log("Parsed JSON data:", data);
            } catch (e) {
                console.error("Failed to parse JSON response:", e);
                throw new Error("Invalid response from server");
            }
            
            // Check if it's a processing status (for slower methods)
            if (data.status === "processing") {
                // Show a progress message
                errorMessage.textContent = data.message || "Processing your request...";
                errorContainer.classList.remove('d-none');
                errorContainer.classList.remove('alert-danger');
                errorContainer.classList.add('alert-info');
                
                // Wait a bit and then try the fallback endpoint with the shortcode
                setTimeout(async () => {
                    try {
                        const fallbackResponse = await fetch(apiEndpoint, {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json',
                            },
                            body: JSON.stringify({ url: url }),
                        });
                        
                        const fallbackData = await fallbackResponse.json();
                        
                        // Hide loader
                        loader.classList.add('d-none');
                        
                        // Check if download URL was found in fallback
                        if (fallbackData.download_url) {
                            // Show success UI
                            videoTitle.textContent = fallbackData.title || "Instagram Video";
                            downloadBtn.href = fallbackData.download_url;
                            thumbnailContainer.innerHTML = '<div class="alert alert-success">Video ready for download!</div>';
                            resultsContainer.classList.remove('d-none');
                            
                            // Hide the info message
                            errorContainer.classList.add('d-none');
                        } else {
                            // Show error and suggest using alternative method
                            showError((fallbackData.error || "Failed to extract video") + 
                                ". Try clicking the 'Use Reliable Method' button instead.");
                        }
                    } catch (fallbackError) {
                        console.error("Fallback error:", fallbackError);
                        loader.classList.add('d-none');
                        showError("An error occurred during processing. Try the 'Use Reliable Method' button instead.");
                    }
                }, 2000); // Wait 2 seconds before trying the fallback
                
                return;
            }
            
            // Hide loader for immediate response
            loader.classList.add('d-none');
            
            // Check if download URL was found
            if (data.download_url) {
                // Show success UI
                videoTitle.textContent = data.title || "Instagram Video";
                downloadBtn.href = data.download_url;
                
                // Add caption if available
                if (data.caption) {
                    const captionElement = document.createElement('p');
                    captionElement.className = 'card-text mb-3';
                    captionElement.textContent = data.caption;
                    thumbnailContainer.innerHTML = '';
                    thumbnailContainer.appendChild(captionElement);
                } else {
                    thumbnailContainer.innerHTML = '<div class="alert alert-success">Video ready for download!</div>';
                }
                
                resultsContainer.classList.remove('d-none');
            } else {
                // Show error and suggest using alternative method
                showError((data.error || "Failed to extract video") + 
                    ". Try clicking the 'Use Reliable Method' button instead.");
            }
        } catch (error) {
            console.error("Error:", error);
            loader.classList.add('d-none');
            showError("An error occurred. Try the 'Use Reliable Method' button instead.");
        }
    }
    
    // Function to create alternative URL
    function createAlternativeUrl(url) {
        try {
            const parsedUrl = new URL(url);
            const path = parsedUrl.pathname;
            
            // Extract post ID from URL
            const matches = path.match(/\/(p|reel|tv)\/([a-zA-Z0-9_-]+)/);
            if (matches && matches[2]) {
                const postId = matches[2];
                // Use multiple alternative Instagram downloaders
                const services = [
                    `https://saveinsta.app/en/instagram-reels-downloader#${postId}`,
                    `https://sssinstagram.com/reel/${postId}`,
                    `https://www.instagramsave.com/instagram-reels-downloader.php?url=https://www.instagram.com/reel/${postId}`
                ];
                
                return services[0]; // Return first alternative for now
            } else {
                return `https://saveinsta.app/en/instagram-reels-downloader#${encodeURIComponent(url)}`;
            }
        } catch {
            // If URL parsing fails, send to a service that can handle any URL
            return `https://saveinsta.app/en`;
        }
    }
    
    // Function to try alternative download method
    async function tryAlternativeDownload(url) {
        // Open the alternative URL in a new tab
        window.open(url, '_blank');
    }
});
