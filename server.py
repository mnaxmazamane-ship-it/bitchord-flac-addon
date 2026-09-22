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
        "description": "FLAC audio streams from Internet Archive",
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
    item_id = request.args.get("id") or request.args.get("query") or request.args.get("title")
    
    if not item_id:
        return jsonify({"error": "Missing track identifier"}), 400

    try:
        # First attempt: treat item_id as a direct Internet Archive item ID
        res = requests.get(f"{IA_METADATA_URL}{item_id}", timeout=10).json()
        files = res.get("files", [])
        server = res.get("server")
        dir_path = res.get("dir")

        # If direct lookup fails, fall back to searching Internet Archive using the query/id text
        if not files or not server:
            search_params = {
                "q": f'({item_id}) AND mediatype:(audio) AND format:(FLAC)',
                "fl[]": ["identifier"],
                "rows": 1,
                "output": "json"
            }
            search_res = requests.get(IA_SEARCH_URL, params=search_params, timeout=10).json()
            docs = search_res.get("response", {}).get("docs", [])
            
            if docs:
                item_id = docs[0].get("identifier")
                res = requests.get(f"{IA_METADATA_URL}{item_id}", timeout=10).json()
                files = res.get("files", [])
                server = res.get("server")
                dir_path = res.get("dir")

        # Extract FLAC file
        flac_file = next((f.get("name") for f in files if f.get("format") == "FLAC" or f.get("name", "").lower().endswith(".flac")), None)

        if not flac_file:
            return jsonify({"error": "No FLAC file found"}), 404

        direct_url = f"https://{server}{dir_path}/{flac_file}"

        # Return HTTP 302 direct stream redirect for BitChord ExoPlayer
        return redirect(direct_url, code=302)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
