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

        # Create a temporary cookie file for Instagram authentication
        import tempfile
        import os
        
        # Check if cookies were provided in the request
        cookies_provided = False
        cookie_file_path = None
        
        # Get cookies from request if they exist
        cookies = {}
        if isinstance(data, dict) and 'cookies' in data and isinstance(data['cookies'], dict):
            cookies = data['cookies']
            logger.info("Received cookies from client")
        
        try:
            # Only create cookie file if valid cookies were provided
            if cookies.get('sessionid'):
                cookies_provided = True
                with tempfile.NamedTemporaryFile(delete=False, mode='w') as cookie_file:
                    # Write Netscape cookie file format with provided cookies
                    cookie_file.write("# Netscape HTTP Cookie File\n")
                    
                    # Add sessionid (most important)
                    if cookies.get('sessionid'):
                        cookie_file.write(f".instagram.com\tTRUE\t/\tTRUE\t0\tsessionid\t{cookies.get('sessionid')}\n")
                    
                    # Add csrftoken if provided
                    if cookies.get('csrftoken'):
                        cookie_file.write(f".instagram.com\tTRUE\t/\tTRUE\t0\tcsrftoken\t{cookies.get('csrftoken')}\n")
                    
                    # Add ds_user_id if provided
                    if cookies.get('ds_user_id'):
                        cookie_file.write(f".instagram.com\tTRUE\t/\tTRUE\t0\tds_user_id\t{cookies.get('ds_user_id')}\n")
                    
                    # Add a default ig_did
                    cookie_file.write(f".instagram.com\tTRUE\t/\tTRUE\t0\tig_did\t{cookies.get('ig_did', 'default_ig_did')}\n")
                    
                    cookie_file_path = cookie_file.name
                    logger.info(f"Created cookie file at: {cookie_file_path}")
            else:
                logger.warning("No valid cookies provided, attempting without authentication")
            
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
            
            # Add cookies file if it was created
            if cookie_file_path:
                yt_dlp_command.extend(["--cookies", cookie_file_path])
                logger.info("Using authenticated request with cookies")
            
            # Add rate limiting protection
            yt_dlp_command.extend(["--sleep-interval", "2", "--max-sleep-interval", "5"])
            
            # Log the command (remove sensitive data for security)
            safe_command = yt_dlp_command.copy()
            if "--cookies" in safe_command:
                cookie_index = safe_command.index("--cookies")
                if cookie_index + 1 < len(safe_command):
                    safe_command[cookie_index + 1] = "[COOKIE_FILE_REDACTED]"
            logger.info(f"Running command: {safe_command}")
            
            # Execute yt-dlp command
            result = subprocess.run(
                yt_dlp_command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
        finally:
            # Clean up temporary cookie file if it was created
            if cookie_file_path and os.path.exists(cookie_file_path):
                try:
                    os.unlink(cookie_file_path)
                    logger.info(f"Deleted temporary cookie file: {cookie_file_path}")
                except Exception as e:
                    logger.warning(f"Failed to delete cookie file: {e}")
        
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
