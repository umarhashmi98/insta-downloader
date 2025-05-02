from flask import Flask, request, jsonify
import subprocess
import json
import logging
from flask_cors import CORS

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

@app.route("/api/download", methods=["POST"])
def download():
    try:
        # Log the incoming request
        logger.debug(f"Received request: {request.get_data()}")
        
        data = request.get_json()
        if not data:
            logger.error("No JSON data in request")
            return jsonify({"error": "No data provided"}), 400
            
        url = data.get("url")
        if not url:
            logger.error("No URL in request data")
            return jsonify({"error": "No URL provided"}), 400
            
        logger.info(f"Processing URL: {url}")

        import tempfile
        import os
        import re
        import random
        import base64
        import requests
        from urllib.parse import urlparse, parse_qs
        
        try:
            # Try to extract Instagram post ID from URL
            logger.info("Extracting Instagram post ID from URL")
            post_id = None
            url_parsed = urlparse(url)
            
            # Standard Instagram URL pattern
            if url_parsed.netloc in ['instagram.com', 'www.instagram.com']:
                # Extract post ID from path
                path_match = re.search(r'/(p|reel|tv)/([A-Za-z0-9_-]+)', url_parsed.path)
                if path_match:
                    post_id = path_match.group(2)
                    logger.info(f"Extracted post ID: {post_id}")
                
                # Sometimes the ID is in the query
                if not post_id and 'id=' in url_parsed.query:
                    query_params = parse_qs(url_parsed.query)
                    if 'id' in query_params and query_params['id']:
                        post_id = query_params['id'][0]
                        logger.info(f"Extracted post ID from query: {post_id}")
            
            # If we have a post ID, try multiple methods to fetch the content
            if post_id:
                logger.info(f"Trying multiple methods to download content for post ID: {post_id}")
                
                # Method 1: yt-dlp with additional request headers
                logger.info("Method 1: Using yt-dlp with enhanced headers")
                
                # Rotate between common user agents
                user_agents = [
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Safari/605.1.15",
                    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36",
                    "Mozilla/5.0 (iPhone; CPU iPhone OS 14_7_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1"
                ]
                user_agent = random.choice(user_agents)
                
                # Construct yt-dlp command with optimized options
                yt_dlp_command = [
                    "yt-dlp",
                    "-v",  # Verbose output for debugging
                    "--no-check-certificate",
                    "--user-agent", user_agent,
                    "--add-header", f"Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                    "--add-header", f"Accept-Language: en-US,en;q=0.5",
                    "--add-header", f"Sec-Fetch-Dest: document",
                    "--add-header", f"Sec-Fetch-Mode: navigate",
                    "--add-header", f"Sec-Fetch-Site: none",
                    "--add-header", f"Sec-Fetch-User: ?1",
                    "--force-ipv4",  # Try to use IPv4 to avoid some restrictions
                    "--socket-timeout", "15",  # Increase timeout for better reliability
                    "--extractor-retries", "3",  # Retry extraction
                    "--mark-watched",  # Typically helps with some sites
                    "-j",  # Output as JSON
                    url
                ]
                
                # Execute yt-dlp command
                logger.info(f"Running command with random user agent")
                result = subprocess.run(
                    yt_dlp_command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                
                # Check if Method 1 worked
                if result.returncode == 0 and result.stdout:
                    logger.info("Method 1 successful!")
                    # Process successful result normally
                else:
                    logger.warning("Method 1 failed, trying Method 2...")
                    
                    # Method 2: Try a different extraction approach with yt-dlp
                    logger.info("Method 2: Alternative extraction approach")
                    
                    # Create a modified URL with additional parameters
                    modified_url = f"https://www.instagram.com/reel/{post_id}/?igsh=randomstring"
                    
                    # Try with different options
                    yt_dlp_command2 = [
                        "yt-dlp",
                        "--ignore-errors",
                        "--no-playlist",
                        "--no-check-certificate",
                        "--referer", "https://www.instagram.com/",
                        "--user-agent", user_agents[0],  # Use a stable user agent for second attempt
                        "--extract-audio",
                        "--audio-format", "mp3",
                        "--no-exec",  # Don't actually download, just extract info
                        "-j",
                        modified_url
                    ]
                    
                    # Execute Method 2
                    logger.info(f"Trying Method 2 with modified URL: {modified_url}")
                    result = subprocess.run(
                        yt_dlp_command2,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True
                    )
            else:
                # If we couldn't extract a post ID, proceed with standard method
                logger.warning("Could not extract post ID, proceeding with standard method")
                
                # Construct yt-dlp command with appropriate options
                yt_dlp_command = [
                    "yt-dlp", 
                    "-v",  # Verbose output for debugging
                    "--no-check-certificate",
                    "--user-agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                    "--force-ipv4",  # Try to use IPv4 to avoid some restrictions
                    "--socket-timeout", "30",  # Increase timeout for better reliability
                    "-j",  # Output as JSON
                    url
                ]
                
                # Add rate limiting protection
                yt_dlp_command.extend(["--sleep-interval", "2", "--max-sleep-interval", "5"])
                
                # Execute yt-dlp command
                logger.info(f"Running standard command")
                result = subprocess.run(
                    yt_dlp_command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
        except Exception as e:
            logger.exception(f"Error in extraction process: {e}")
            # Create a result object with similar properties to subprocess.run result
            class DummyResult:
                def __init__(self, returncode, stdout, stderr):
                    self.returncode = returncode
                    self.stdout = stdout
                    self.stderr = stderr
                    
            result = DummyResult(1, '', f"Extraction error: {str(e)}")
        
        # Log the command output (both stdout and stderr)
        logger.debug(f"yt-dlp stdout: {result.stdout}")
        logger.debug(f"yt-dlp stderr: {result.stderr}")
        logger.debug(f"yt-dlp return code: {result.returncode}")

        if result.returncode != 0:
            error_message = result.stderr or "Unknown error"
            logger.error(f"yt-dlp failed: {error_message}")
            return jsonify({"error": f"Failed to fetch video: {error_message}"}), 400

        try:
            video_info = json.loads(result.stdout)
            logger.debug(f"Parsed video info: {video_info.keys()}")
            
            if "url" not in video_info:
                logger.error("No URL found in video info")
                formats = video_info.get("formats", [])
                if formats:
                    # Try to find the best quality format
                    best_format = max(formats, key=lambda x: x.get("height", 0) if x.get("height") else 0)
                    download_url = best_format.get("url")
                    logger.info(f"Found URL in formats: {download_url[:50]}...")
                else:
                    logger.error("No formats found in video info")
                    return jsonify({"error": "Could not extract download URL"}), 400
            else:
                download_url = video_info["url"]
                logger.info(f"Found URL in video info: {download_url[:50]}...")
                
            return jsonify({
                "download_url": download_url,
                "title": video_info.get("title", "Instagram Video")
            })
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON: {e}")
            return jsonify({"error": f"Failed to parse video info: {e}"}), 500

    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        return jsonify({"error": f"Error processing video: {str(e)}"}), 500

@app.route('/')
def index():
    """
    Render the main page with the form to input Instagram URL.
    """
    return app.send_static_file('index.html')

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)
