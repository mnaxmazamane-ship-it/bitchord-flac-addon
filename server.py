import os
import requests
from flask import Flask, request, jsonify, redirect

app = Flask(__name__)

IA_SEARCH_URL = "https://archive.org/advancedsearch.php"
IA_METADATA_URL = "https://archive.org/metadata/"

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

    res = requests.get(IA_SEARCH_URL, params=params).json()
    docs = res.get("response", {}).get("docs", [])

    tracks = []
    for doc in docs:
        tracks.append({
            "id": doc.get("identifier"),
            "title": doc.get("title", "Unknown Title"),
            "artist": doc.get("creator", "Unknown Artist"),
            "audioQuality": "LOSSLESS",
            "format": "FLAC"
        })

    return jsonify({"tracks": tracks, "total": len(tracks)})

@app.route("/stream")
def stream():
    item_id = request.args.get("id")
    if not item_id:
        return jsonify({"error": "Missing id"}), 400

    res = requests.get(f"{IA_METADATA_URL}{item_id}").json()
    files = res.get("files", [])
    server = res.get("server")
    dir_path = res.get("dir")

    flac_file = next((f.get("name") for f in files if f.get("format") == "FLAC" or f.get("name", "").lower().endswith(".flac")), None)

    if not flac_file:
        return jsonify({"error": "No FLAC file found"}), 404

    return redirect(f"https://{server}{dir_path}/{flac_file}")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
