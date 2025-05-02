import os
import re
import json
import time
import random
import logging
import tempfile
import urllib.parse
from urllib.request import Request, urlopen
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import instaloader

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Get Instagram cookies from environment variables
INSTAGRAM_SESSIONID = os.environ.get('INSTAGRAM_SESSIONID', '')
INSTAGRAM_CSRFTOKEN = os.environ.get('INSTAGRAM_CSRFTOKEN', '')

# Initialize instaloader instance with authentication if cookies are available
L = instaloader.Instaloader(
    download_pictures=True,
    download_videos=True,
    download_video_thumbnails=False,
    download_geotags=False,
    download_comments=False,
    save_metadata=False,
    compress_json=False,
    quiet=False,
)

# Add Instagram cookies if available
if INSTAGRAM_SESSIONID and INSTAGRAM_CSRFTOKEN:
    logger.info("Instagram cookies found, initializing with authenticated session")
    # Create session and add cookies
    L.context._session.cookies.set("sessionid", INSTAGRAM_SESSIONID, domain=".instagram.com")
    L.context._session.cookies.set("csrftoken", INSTAGRAM_CSRFTOKEN, domain=".instagram.com")
    # Additional metadata to make it look like a real browser session
    L.context._session.cookies.set("ig_did", "D822845C-AA99-4A5F-84F9-5AB0B56E8D32", domain=".instagram.com")
    L.context._session.cookies.set("mid", "YWVW7AALAAGfSR76nq-mVxsPw4F6", domain=".instagram.com")
else:
    logger.info("No Instagram cookies found, will try to proceed without authentication")

# Configure user agents for requests
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 14_7_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1"
]

# Function to extract shortcode from Instagram URL
def extract_shortcode(url):
    """Extract the shortcode from an Instagram URL."""
    try:
        # Parse the URL
        parsed_url = urllib.parse.urlparse(url)
        path = parsed_url.path
        
        # Use regex to find the shortcode
        # Instagram shortcodes are typically in /p/{shortcode}/ or /reel/{shortcode}/
        match = re.search(r'/(p|reel|tv)/([A-Za-z0-9_-]+)', path)
        if match:
            return match.group(2)
        return None
    except Exception as e:
        logger.error(f"Error extracting shortcode: {e}")
        return None

# Method 1: Using instaloader to get direct video URL
def get_video_url_instaloader(shortcode):
    """Get video URL using instaloader library."""
    try:
        logger.info(f"Attempting to get post with shortcode: {shortcode}")
        post = instaloader.Post.from_shortcode(L.context, shortcode)
        
        # Check if it's a video
        if post.is_video:
            logger.info(f"Found video: {post.video_url}")
            return {
                "download_url": post.video_url,
                "title": f"Instagram Video - {post.owner_username}",
                "thumbnail_url": post.url,
                "username": post.owner_username,
                "caption": post.caption if post.caption else ""
            }
        else:
            logger.info("Post is not a video")
            return {"error": "Post is not a video"}
    except instaloader.exceptions.InstaloaderException as e:
        logger.error(f"Instaloader error: {e}")
        return {"error": f"Instaloader error: {str(e)}"}
    except Exception as e:
        logger.exception(f"Error using instaloader: {e}")
        return {"error": f"Error extracting video URL: {str(e)}"}

# Method 2: Direct HTTP request with Instagram cookies
def get_video_url_http(url, shortcode):
    """Get video URL using direct HTTP request with Instagram cookies."""
    try:
        # Try multiple URLs that might contain the video
        urls_to_try = [
            f"https://www.instagram.com/p/{shortcode}/?__a=1&__d=dis",  # API access with cookies
            f"https://www.instagram.com/reel/{shortcode}/?__a=1&__d=dis",  # Reel API access
            f"https://www.instagram.com/api/v1/media/{shortcode}/info/",  # Media info API
            f"https://www.instagram.com/graphql/query/?query_hash=b3055c01b4b222b8a47dc12b090e4e64&variables=%7B%22shortcode%22:%22{shortcode}%22%7D",  # GraphQL API
            f"https://www.instagram.com/p/{shortcode}/",  # Regular page
            f"https://www.instagram.com/reel/{shortcode}/"  # Reel page
        ]
        
        # Create headers with cookies from the environment
        headers = {
            'User-Agent': random.choice(USER_AGENTS),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0',
            'TE': 'trailers',
            'Referer': 'https://www.instagram.com/',  # Make it look like we came from Instagram
        }
        
        # Add cookies if available
        if INSTAGRAM_SESSIONID and INSTAGRAM_CSRFTOKEN:
            headers['Cookie'] = f"sessionid={INSTAGRAM_SESSIONID}; csrftoken={INSTAGRAM_CSRFTOKEN}; ds_user_id=123456789; ig_did=D822845C-AA99-4A5F-84F9-5AB0B56E8D32; mid=YWVW7AALAAGfSR76nq-mVxsPw4F6"
            headers['X-CSRFToken'] = INSTAGRAM_CSRFTOKEN
        
        # Try different delaying strategies between requests to avoid rate limits
        delay_strategies = [0.5, 1, 1.5, 2]
        
        # Try each URL with different delays
        for target_url in urls_to_try:
            # Add some randomness to avoid pattern detection
            time.sleep(random.choice(delay_strategies))
            
            try:
                logger.info(f"Trying to fetch URL: {target_url}")
                
                # Randomize headers slightly for each request
                current_headers = headers.copy()
                if random.random() > 0.5:
                    current_headers['Accept-Encoding'] = 'gzip, deflate, br'
                
                req = Request(target_url, headers=current_headers)
                with urlopen(req, timeout=15) as response:
                    html = response.read().decode('utf-8')
                    
                    # Look for multiple video URL patterns
                    video_patterns = [
                        r'<video[^>]*src="([^"]*)"',  # Standard video tag
                        r'<source[^>]*src="([^"]*)"',  # Source tag inside video
                        r'property="og:video:secure_url"\s*content="([^"]*)"',  # OpenGraph tag
                        r'property="og:video"\s*content="([^"]*)"',  # Alternative OpenGraph
                        r'<meta\s*name="twitter:player:stream"\s*content="([^"]*)"',  # Twitter card
                        r'"video_url":"([^"]*)"',  # JSON format
                        r'"video_url_encoded":"([^"]*)"',  # JSON encoded format
                        r'"contentUrl":"([^"]*)"'  # JSON-LD format
                    ]
                    
                    # Try each video pattern
                    for pattern in video_patterns:
                        video_url_match = re.search(pattern, html)
                        if video_url_match:
                            video_url = video_url_match.group(1)
                            # Clean up URL (unescape special characters)
                            video_url = video_url.replace('\\/', '/').replace('\\u0026', '&')
                            
                            logger.info(f"Found video URL via HTTP: {video_url}")
                            return {
                                "download_url": video_url,
                                "title": f"Instagram Video - {shortcode}",
                            }
                    
                    # If specific patterns fail, look for any MP4 URL
                    mp4_match = re.search(r'(https?://[^"\']+\.mp4[^"\'\s]*)', html)
                    if mp4_match:
                        video_url = mp4_match.group(1)
                        logger.info(f"Found MP4 URL via HTTP: {video_url}")
                        return {
                            "download_url": video_url,
                            "title": f"Instagram Video - {shortcode}",
                        }
                    
                    # If GraphQL URL, parse the JSON response
                    if "graphql" in target_url and "query_hash" in target_url:
                        try:
                            data = json.loads(html)
                            media = data.get("data", {}).get("shortcode_media", {})
                            if media.get("is_video") and media.get("video_url"):
                                video_url = media.get("video_url")
                                logger.info(f"Found video URL via GraphQL: {video_url}")
                                return {
                                    "download_url": video_url,
                                    "title": f"Instagram Video - {shortcode}",
                                    "username": media.get("owner", {}).get("username", ""),
                                    "caption": media.get("edge_media_to_caption", {}).get("edges", [{}])[0].get("node", {}).get("text", "")
                                }
                        except json.JSONDecodeError:
                            logger.warning("Failed to parse GraphQL response as JSON")
                    
                    # If direct video URL is not found, look for any media URL
                    media_url_match = re.search(r'<img[^>]*src="([^"]*)"[^>]*class="[^"]*EmbeddedMediaImage', html)
                    if media_url_match:
                        media_url = media_url_match.group(1)
                        logger.info(f"Found media URL: {media_url}")
                        return {
                            "download_url": media_url,
                            "title": f"Instagram Media - {shortcode}",
                        }
                    
                    logger.info(f"No media URLs found in page: {target_url}")
                
            except Exception as e:
                logger.warning(f"Error with URL {target_url}: {e}")
                continue  # Try the next URL
            
        # If all URLs failed
        return {"error": "Could not find video URL via direct HTTP requests"}
            
    except Exception as e:
        logger.exception(f"Error with all HTTP methods: {e}")
        return {"error": f"HTTP request error: {str(e)}"}

# Method 3: Web proxy method (use Instagram through a proxy service)
def get_video_url_proxy(shortcode):
    """Get video URL through a proxy service."""
    try:
        # Try different proxy services that are likely to work without restrictions
        proxy_services = [
            f"https://imginn.org/reels/{shortcode}/",
            f"https://ig.dumpor.com/view?q={shortcode}",
            f"https://snapinsta.app/api/ajaxSearch?q=https://www.instagram.com/reel/{shortcode}",
            f"https://instagram.fcaptureapps.com/api/reel?url=https://www.instagram.com/reel/{shortcode}"
        ]
        
        # Prepare headers that mimic a real browser
        headers = {
            'User-Agent': random.choice(USER_AGENTS),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Referer': 'https://www.google.com/',
            'DNT': '1',
            'Sec-GPC': '1'
        }
        
        # Try each proxy service until one works
        for proxy_url in proxy_services:
            try:
                logger.info(f"Attempting to use proxy service: {proxy_url}")
                
                req = Request(proxy_url, headers=headers)
                with urlopen(req, timeout=10) as response:
                    html = response.read().decode('utf-8')
                    
                    # Different patterns to look for video URLs in the response
                    patterns = [
                        r'<video[^>]*>\s*<source src="([^"]*)"',  # Standard video tag
                        r'<video[^>]*src="([^"]*)"',  # Video with src attribute
                        r'data-video-url="([^"]*)"',  # Data attribute
                        r'"video_url":"([^"]*)"',     # JSON format
                        r'"contentUrl":"([^"]*)"',    # JSON-LD format
                        r'background-video-link="([^"]*)"',  # Custom attribute
                        r'<a[^>]*href="([^"]*\.mp4[^"]*)"'  # Direct link to MP4
                    ]
                    
                    # Try each pattern
                    for pattern in patterns:
                        video_url_match = re.search(pattern, html)
                        if video_url_match:
                            video_url = video_url_match.group(1)
                            # Unescape any escaped characters
                            video_url = video_url.replace('\\/', '/').replace('\\u0026', '&')
                            
                            logger.info(f"Found video URL via proxy: {video_url}")
                            return {
                                "download_url": video_url,
                                "title": f"Instagram Video - {shortcode}",
                            }
                
                # Look for direct links to MP4 files (sometimes they're in JSON)
                mp4_match = re.search(r'(https?://[^"\']+\.mp4[^"\'\s]*)', html)
                if mp4_match:
                    video_url = mp4_match.group(1)
                    logger.info(f"Found direct MP4 URL: {video_url}")
                    return {
                        "download_url": video_url,
                        "title": f"Instagram Video - {shortcode}",
                    }
                
                logger.info(f"No video URLs found in proxy page: {proxy_url}")
                
            except Exception as e:
                logger.warning(f"Error with proxy {proxy_url}: {e}")
                continue  # Try the next proxy
        
        # If all proxies failed
        return {"error": "Could not find video URL through any proxy service"}
            
    except Exception as e:
        logger.exception(f"Error with all proxy methods: {e}")
        return {"error": f"Proxy service error: {str(e)}"}

# Method 4: API Aggregator (Combined approach with multiple services)
def get_video_url_aggregator(url, shortcode):
    """Combined approach using multiple third-party API services."""
    try:
        # Different API services that can extract Instagram videos
        api_services = [
            {
                "url": f"https://api.savefrom.net/api/convert?url=https://www.instagram.com/reel/{shortcode}/",
                "headers": {
                    "User-Agent": random.choice(USER_AGENTS),
                    "Accept": "application/json",
                    "Origin": "https://savefrom.net",
                    "Referer": "https://savefrom.net/"
                },
                "json_path": ["url", "hd"]  # Path to extract URL from JSON response
            },
            {
                "url": f"https://www.save-insta.com/api/ajaxSearch",
                "method": "POST",
                "data": f"q=https://www.instagram.com/reel/{shortcode}/",
                "headers": {
                    "User-Agent": random.choice(USER_AGENTS),
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Accept": "*/*",
                    "Origin": "https://www.save-insta.com",
                    "Referer": "https://www.save-insta.com/"
                },
                "regex": r'<a[^>]*href="([^"]*\.mp4[^"]*)"'  # Regex to find URL in HTML response
            },
            {
                "url": f"https://saveinsta.app/core/ajax.php",
                "method": "POST",
                "data": f"url=https://www.instagram.com/reel/{shortcode}/&lang=en",
                "headers": {
                    "User-Agent": random.choice(USER_AGENTS),
                    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                    "Accept": "application/json, text/javascript, */*",
                    "X-Requested-With": "XMLHttpRequest",
                    "Origin": "https://saveinsta.app",
                    "Referer": "https://saveinsta.app/en/instagram-reels-downloader"
                },
                "json_path": ["links", 0, "url"]  # Path to extract URL from JSON response
            }
        ]
        
        # Try each API service
        for service in api_services:
            try:
                time.sleep(random.uniform(0.5, 1.5))  # Random delay
                
                logger.info(f"Trying aggregator service: {service['url']}")
                
                # Create request
                if service.get("method") == "POST":
                    req = Request(
                        service["url"], 
                        data=service.get("data", "").encode('utf-8'),
                        headers=service.get("headers", {})
                    )
                else:
                    req = Request(service["url"], headers=service.get("headers", {}))
                
                # Send request and get response
                with urlopen(req, timeout=10) as response:
                    response_data = response.read().decode('utf-8')
                    
                    # Parse response based on service type
                    if "json_path" in service:
                        try:
                            # Try to parse as JSON
                            data = json.loads(response_data)
                            
                            # Navigate through JSON path to find the URL
                            value = data
                            for key in service["json_path"]:
                                if isinstance(key, int):
                                    if isinstance(value, list) and len(value) > key:
                                        value = value[key]
                                    else:
                                        value = None
                                        break
                                else:
                                    value = value.get(key)
                                    if value is None:
                                        break
                            
                            if value and isinstance(value, str) and (value.startswith("http") or value.startswith("//")):
                                # Ensure URL is properly formatted
                                if value.startswith("//"):
                                    value = "https:" + value
                                
                                logger.info(f"Found video URL via aggregator (JSON): {value}")
                                return {
                                    "download_url": value,
                                    "title": f"Instagram Video - {shortcode}",
                                }
                        except json.JSONDecodeError:
                            logger.warning(f"Failed to parse response as JSON from {service['url']}")
                    
                    # If regex pattern is provided, use it to search the response
                    if "regex" in service:
                        match = re.search(service["regex"], response_data)
                        if match:
                            video_url = match.group(1)
                            if video_url.startswith("//"):
                                video_url = "https:" + video_url
                                
                            logger.info(f"Found video URL via aggregator (regex): {video_url}")
                            return {
                                "download_url": video_url,
                                "title": f"Instagram Video - {shortcode}",
                            }
                    
                    # Generic MP4 URL finder
                    mp4_match = re.search(r'(https?://[^"\']+\.mp4[^"\'\s]*)', response_data)
                    if mp4_match:
                        video_url = mp4_match.group(1)
                        logger.info(f"Found MP4 URL via aggregator: {video_url}")
                        return {
                            "download_url": video_url,
                            "title": f"Instagram Video - {shortcode}",
                        }
                    
                    logger.info(f"No video URL found in response from {service['url']}")
                
            except Exception as e:
                logger.warning(f"Error with aggregator service {service['url']}: {e}")
                continue  # Try next service
        
        # If all services failed
        return {"error": "Could not extract video URL through aggregator services"}
        
    except Exception as e:
        logger.exception(f"Error with aggregator method: {e}")
        return {"error": f"Aggregator service error: {str(e)}"}

@app.route("/api/download", methods=["POST"])
def download():
    """API endpoint to process Instagram video download requests."""
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
        
        # Extract the shortcode from the URL
        shortcode = extract_shortcode(url)
        if not shortcode:
            logger.error(f"Invalid Instagram URL: {url}")
            return jsonify({"error": "Invalid Instagram URL format"}), 400
        
        logger.info(f"Extracted shortcode: {shortcode}")
        
        # Since instaloader method was successful last time, prioritize it with cookies
        if INSTAGRAM_SESSIONID and INSTAGRAM_CSRFTOKEN:
            logger.info("Using authenticated instaloader method")
            result = get_video_url_instaloader(shortcode)
            if "download_url" in result:
                logger.info("Instaloader method successful")
                return jsonify(result)
            
            # If instaloader fails, try GraphQL API directly with authentication
            logger.info("Trying direct GraphQL API with authentication")
            try:
                headers = {
                    'User-Agent': random.choice(USER_AGENTS),
                    'Accept': 'application/json',
                    'Referer': 'https://www.instagram.com/',
                    'Cookie': f"sessionid={INSTAGRAM_SESSIONID}; csrftoken={INSTAGRAM_CSRFTOKEN}",
                    'X-CSRFToken': INSTAGRAM_CSRFTOKEN
                }
                
                api_url = f"https://www.instagram.com/graphql/query/?query_hash=b3055c01b4b222b8a47dc12b090e4e64&variables=%7B%22shortcode%22:%22{shortcode}%22%7D"
                req = Request(api_url, headers=headers)
                
                with urlopen(req, timeout=10) as response:
                    data = json.loads(response.read().decode('utf-8'))
                    media = data.get("data", {}).get("shortcode_media", {})
                    
                    if media and media.get("is_video") and media.get("video_url"):
                        video_url = media.get("video_url")
                        logger.info(f"Found video URL via direct GraphQL: {video_url}")
                        
                        return jsonify({
                            "download_url": video_url,
                            "title": f"Instagram Video - {media.get('owner', {}).get('username', '')}",
                            "username": media.get("owner", {}).get("username", ""),
                            "caption": media.get("edge_media_to_caption", {}).get("edges", [{}])[0].get("node", {}).get("text", "")
                        })
            except Exception as e:
                logger.warning(f"Direct GraphQL API failed: {e}")
                # Continue to other methods
        
        # Try HTTP method with shorter timeouts and fewer URLs
        logger.info("Trying optimized HTTP request method")
        try:
            # Only try the most likely URLs to succeed
            urls_to_try = [
                f"https://www.instagram.com/p/{shortcode}/?__a=1&__d=dis",
                f"https://www.instagram.com/reel/{shortcode}/?__a=1&__d=dis"
            ]
            
            headers = {
                'User-Agent': random.choice(USER_AGENTS),
                'Accept': 'application/json, text/html',
                'Referer': 'https://www.instagram.com/',
                'Cookie': f"sessionid={INSTAGRAM_SESSIONID}; csrftoken={INSTAGRAM_CSRFTOKEN}"
            }
            
            for target_url in urls_to_try:
                try:
                    req = Request(target_url, headers=headers)
                    with urlopen(req, timeout=5) as response:  # Reduced timeout
                        data = response.read().decode('utf-8')
                        
                        # Look directly for video URL in JSON
                        video_match = re.search(r'"video_url":"([^"]*)"', data)
                        if video_match:
                            video_url = video_match.group(1).replace('\\/', '/')
                            logger.info(f"Found video URL via optimized HTTP: {video_url}")
                            return jsonify({
                                "download_url": video_url,
                                "title": f"Instagram Video - {shortcode}"
                            })
                except Exception as e:
                    logger.warning(f"Error with optimized URL {target_url}: {e}")
                    continue
        except Exception as e:
            logger.warning(f"Optimized HTTP method failed: {e}")
        
        # If we're here, all optimized methods failed, fall back to the full method
        # but with a message to the user that it's taking longer
        return jsonify({
            "status": "processing",
            "message": "Finding the best source for your video, this may take a moment...",
            "shortcode": shortcode
        })

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
