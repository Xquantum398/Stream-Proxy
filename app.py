from flask import Flask, request, Response
import requests
from urllib.parse import urlparse, urljoin, quote

app = Flask(__name__)

# ==============================
# GÜÇLÜ HEADER (403 FIX)
# ==============================
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Referer": "https://patronyayin1.cfd/",
    "Origin": "https://patronyayin1.cfd/",
    "Accept": "*/*",
    "Connection": "keep-alive"
}

# ==============================
# SESSION (cookie için)
# ==============================
session = requests.Session()
session.headers.update(HEADERS)

# ==============================
# M3U8 REWRITE
# ==============================
def rewrite_m3u8(content, base_url):
    parsed = urlparse(base_url)
    base = f"{parsed.scheme}://{parsed.netloc}{parsed.path.rsplit('/',1)[0]}/"

    output = []

    for line in content.splitlines():
        line = line.strip()

        if line.startswith("#EXT-X-KEY") and "URI=" in line:
            key_url = line.split('"')[1]
            line = line.replace(
                key_url,
                f"/proxy/key?url={quote(key_url)}"
            )

        elif line and not line.startswith("#"):
            if not line.startswith("http"):
                line = urljoin(base, line)

            line = f"/proxy/ts?url={quote(line)}"

        output.append(line)

    return "\n".join(output)

# ==============================
# M3U PROXY
# ==============================
@app.route("/proxy/m3u")
def proxy_m3u():
    url = request.args.get("url")

    try:
        # 🔥 ÖNCE siteyi ziyaret et (cookie al)
        session.get("https://patronyayin1.cfd/", timeout=10)

        # 🔥 SONRA stream çek
        r = session.get(url, timeout=15)
        r.raise_for_status()

        content = r.text

        if not content.startswith("#EXTM3U"):
            return Response(content)

        modified = rewrite_m3u8(content, r.url)

        return Response(modified, content_type="application/vnd.apple.mpegurl")

    except Exception as e:
        return f"HATA: {str(e)}", 500

# ==============================
# TS PROXY
# ==============================
@app.route("/proxy/ts")
def proxy_ts():
    url = request.args.get("url")

    try:
        r = session.get(url, stream=True, timeout=20)

        return Response(
            r.iter_content(8192),
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
        r = session.get(url, timeout=10)
        return Response(r.content)
    except Exception as e:
        return str(e), 500

# ==============================
@app.route("/")
def home():
    return "403 Fix Proxy OK"

# ==============================
if __name__ == "__main__":
    import os
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 7860)))
