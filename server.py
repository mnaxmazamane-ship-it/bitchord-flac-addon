import os
import requests
from flask import Flask, request, jsonify, redirect

app = Flask(__name__)

IA_SEARCH_URL = "https://archive.org/advancedsearch.php"
IA_METADATA_URL = "https://archive.org/metadata/"

@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    return response

@app.route("/")
@app.route("/manifest.json")
def manifest():
    return jsonify({
        "id": "com.bitchord.ia.flac",
        "name": "Internet Archive FLAC",
        "version": "1.0.0",
        "description": "Lossless FLAC audio streams from Internet Archive",
        "endpoints": {
            "search": "/search",
            "stream": "/stream"
        }
    })

@app.route("/health")
def health():
    return jsonify({"status": "ok"})

@app.route("/search")
def search():
    query = request.args.get("q", "")
    limit = int(request.args.get("limit", 20))
    if not query:
        return jsonify({"tracks": [], "total": 0})

    params = {
        "q": f'({query}) AND mediatype:(audio) AND format:(FLAC)',
        "fl[]": ["identifier", "title", "creator"],
        "rows": limit,
        "output": "json"
    }
    
    try:
        res = requests.get(IA_SEARCH_URL, params=params, timeout=10).json()
        docs = res.get("response", {}).get("docs", [])
        
        tracks = []
        for doc in docs:
            tracks.append({
                "id": doc.get("identifier"),
                "title": doc.get("title", "Unknown Title"),
                "artist": doc.get("creator", "Internet Archive"),
                "audioQuality": "LOSSLESS",
                "format": "FLAC",
                "isLossless": True,
                "mimeType": "audio/flac"
            })
            
        return jsonify({"tracks": tracks, "total": len(tracks)})
    except Exception as e:
        return jsonify({"tracks": [], "error": str(e)}), 500

@app.route("/stream")
def stream():
    item_id = request.args.get("id")
    redirect_mode = request.args.get("redirect", "true") # Default to direct redirect
    
    if not item_id:
        return jsonify({"error": "Missing id"}), 400

    try:
        res = requests.get(f"{IA_METADATA_URL}{item_id}", timeout=10).json()
        files = res.get("files", [])
        server = res.get("server")
        dir_path = res.get("dir")

        # Find the exact FLAC file
        flac_file = next((f.get("name") for f in files if f.get("format") == "FLAC" or f.get("name", "").lower().endswith(".flac")), None)

        if not flac_file:
            return jsonify({"error": "No FLAC file found"}), 404

        direct_url = f"https://{server}{dir_path}/{flac_file}"

        # If redirect parameter is false, return JSON; otherwise, HTTP 302 directly to raw FLAC
        if redirect_mode.lower() == "false":
            return jsonify({
                "url": direct_url,
                "streamUrl": direct_url,
                "format": "FLAC",
                "mimeType": "audio/flac",
                "quality": "LOSSLESS",
                "isLossless": True
            })
        
        # Direct HTTP redirect (forces ExoPlayer to stream FLAC natively)
        return redirect(direct_url, code=302)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
