import os
import logging
import re
import subprocess
import json
from urllib.parse import urlparse

from flask import Flask, jsonify, request, render_template
from flask_cors import CORS

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "default_secret_key")

# Enable CORS for all routes
CORS(app)

def is_valid_instagram_url(url):
    """
    Validate if the URL is a proper Instagram URL.
    """
    # Basic validation
    if not url:
        return False
    
    parsed_url = urlparse(url)
    
    # Check if the domain is instagram.com or www.instagram.com
    if parsed_url.netloc not in ('instagram.com', 'www.instagram.com'):
        return False
    
    # Check if the URL has a path (e.g., /p/shortcode/ or /reel/shortcode/)
    if not parsed_url.path or parsed_url.path == '/':
        return False
    
    # Simple pattern matching for Instagram URLs
    # Instagram posts typically have paths like /p/{shortcode}/ or /reel/{shortcode}/
    pattern = r'^/(p|reel|tv)/[a-zA-Z0-9_-]+/?$'
    if not re.match(pattern, parsed_url.path):
        return False
    
    return True

def extract_download_link(url):
    """
    Extract download link from Instagram URL using yt-dlp.
    """
    try:
        # Run yt-dlp command to get video info in JSON format
        command = ["yt-dlp", "--dump-json", url]
        output = subprocess.check_output(command, stderr=subprocess.STDOUT)
        
        # Parse the JSON output
        video_info = json.loads(output)
        
        # Get the URL of the best quality format
        download_url = None
        if 'url' in video_info:
            download_url = video_info['url']
        else:
            # Some videos might have formats in a list
            formats = video_info.get('formats', [])
            if formats:
                # Sort formats by quality (if possible) and get the best one
                best_format = max(formats, key=lambda x: x.get('height', 0) if x.get('height') else 0)
                download_url = best_format.get('url')
        
        if not download_url:
            raise ValueError("Could not extract download URL from video info")
        
        return {
            "success": True,
            "download_url": download_url,
            "title": video_info.get('title', 'Instagram Video'),
            "thumbnail": video_info.get('thumbnail', None)
        }
    
    except subprocess.CalledProcessError as e:
        error_message = e.output.decode('utf-8')
        logger.error(f"yt-dlp error: {error_message}")
        
        # Check for specific error messages
        if "This video is not available" in error_message:
            return {"success": False, "error": "This Instagram video is not available or is private"}
        elif "Unsupported URL" in error_message:
            return {"success": False, "error": "Unsupported URL format"}
        else:
            return {"success": False, "error": "Failed to extract download URL"}
    
    except Exception as e:
        logger.error(f"Error extracting download link: {str(e)}")
        return {"success": False, "error": f"Error processing video: {str(e)}"}

@app.route('/')
def index():
    """
    Render the main page with the form to input Instagram URL.
    """
    return render_template('index.html')

@app.route('/api/download', methods=['POST'])
def download():
    """
    API endpoint to process Instagram URL and return download link.
    """
    # Get the Instagram URL from the request
    data = request.get_json()
    
    if not data:
        return jsonify({"success": False, "error": "No data provided"}), 400
    
    instagram_url = data.get('url')
    
    if not instagram_url:
        return jsonify({"success": False, "error": "No URL provided"}), 400
    
    # Validate the Instagram URL
    if not is_valid_instagram_url(instagram_url):
        return jsonify({"success": False, "error": "Invalid Instagram URL"}), 400
    
    # Extract the download link
    result = extract_download_link(instagram_url)
    
    if result["success"]:
        return jsonify(result), 200
    else:
        return jsonify(result), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
