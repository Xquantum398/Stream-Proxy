from flask import Flask, request, Response
import requests
from urllib.parse import urlparse, urljoin, quote

app = Flask(__name__)

# ==============================
# SABİT HEADER (SENİN LİNK İÇİN)
# ==============================
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Referer": "https://patronyayin1.cfd/",
    "Origin": "https://patronyayin1.cfd/",
    "Accept": "*/*",
    "Connection": "keep-alive"
}

# ==============================
# M3U8 REWRITE
# ==============================
def rewrite_m3u8(content, base_url):
    parsed = urlparse(base_url)
    base = f"{parsed.scheme}://{parsed.netloc}{parsed.path.rsplit('/',1)[0]}/"

    output = []

    for line in content.splitlines():
        line = line.strip()

        # KEY
        if line.startswith("#EXT-X-KEY") and "URI=" in line:
            start = line.find('"') + 1
            end = line.rfind('"')
            key_url = line[start:end]

            new_key = f"/proxy/key?url={quote(key_url)}"
            line = line.replace(key_url, new_key)

        # SEGMENT
        elif line and not line.startswith("#"):
            if line.startswith("http"):
                seg = line
            else:
                seg = urljoin(base, line)

            line = f"/proxy/ts?url={quote(seg)}"

        output.append(line)

    return "\n".join(output)

# ==============================
# M3U PROXY
# ==============================
@app.route("/proxy/m3u")
def proxy_m3u():
    url = request.args.get("url")

    if not url:
        return "url param missing", 400

    try:
        r = requests.get(url, headers=DEFAULT_HEADERS, timeout=15)
        r.raise_for_status()

        content = r.text

        if not content.startswith("#EXTM3U"):
            return Response(content, content_type="text/plain")

        modified = rewrite_m3u8(content, r.url)

        return Response(
            modified,
            content_type="application/vnd.apple.mpegurl"
        )

    except Exception as e:
        return str(e), 500

# ==============================
# TS PROXY
# ==============================
@app.route("/proxy/ts")
def proxy_ts():
    url = request.args.get("url")

    try:
        r = requests.get(url, headers=DEFAULT_HEADERS, stream=True, timeout=20)

        return Response(
            r.iter_content(chunk_size=8192),
            content_type="video/mp2t"
        )
    except Exception as e:
        return str(e), 500

# ==============================
# KEY PROXY
# ==============================
@app.route("/proxy/key")
def proxy_key():
    url = request.args.get("url")

    try:
        r = requests.get(url, headers=DEFAULT_HEADERS, timeout=10)

        return Response(
            r.content,
            content_type="application/octet-stream"
        )
    except Exception as e:
        return str(e), 500

# ==============================
# ROOT
# ==============================
@app.route("/")
def home():
    return "HF Proxy çalışıyor"

# ==============================
# HUGGINGFACE RUN
# ==============================
if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 7860))
    app.run(host="0.0.0.0", port=port)
