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

        # Run yt-dlp with verbose output and cookies to help diagnose issues
        # Adding some common Instagram cookies to avoid rate limiting issues
        result = subprocess.run(
            ["yt-dlp", "-v", "--no-check-certificate", "--user-agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36", "-j", url],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
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
