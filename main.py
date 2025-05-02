from flask import Flask, request, jsonify
import subprocess
import json
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

@app.route("/api/download", methods=["POST"])
def download():
    try:
        data = request.get_json()
        url = data["url"]

        result = subprocess.run(
            ["yt-dlp", "-j", url],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        if result.returncode != 0:
            return jsonify({"error": "Failed to fetch video"}), 400

        video_info = json.loads(result.stdout)
        download_url = video_info["url"]

        return jsonify({"download_url": download_url})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/')
def index():
    """
    Render the main page with the form to input Instagram URL.
    """
    return app.send_static_file('index.html')

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)
