from flask import Flask, request, Response
import requests
from urllib.parse import urlparse, urljoin, quote, unquote
import re

app = Flask(__name__)

# ✅ M3U türü tespit
def detect_m3u_type(content):
    if "#EXTM3U" in content and "#EXTINF" in content:
        return "m3u8"
    return "m3u"

# ✅ KEY proxy
def replace_key_uri(line, headers_query):
    match = re.search(r'URI="([^"]+)"', line)
    if match:
        key_url = match.group(1)
        return line.replace(key_url, f"/proxy/key?url={quote(key_url)}&{headers_query}")
    return line

# ✅ BASİT RESOLVE (karmaşık iframe kaldırıldı - daha stabil)
def resolve_m3u8_link(url, headers):
    try:
        r = requests.get(url, headers=headers, allow_redirects=True, timeout=10)
        r.raise_for_status()

        # direkt m3u8 ise
        if r.text.strip().startswith("#EXTM3U"):
            return {"resolved_url": r.url, "headers": headers}

        return {"resolved_url": r.url, "headers": headers}

    except:
        return {"resolved_url": url, "headers": headers}

# ✅ ANA PROXY
@app.route('/proxy/m3u')
def proxy_m3u():
    m3u_url = request.args.get('url', '').strip()
    if not m3u_url:
        return "URL yok", 400

    # 🔥 SABİT HEADER (senin link için)
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://patronyayin1.cfd/",
        "Origin": "https://patronyayin1.cfd/"
    }

    # 🔥 DIŞARIDAN HEADER override
    for key, value in request.args.items():
        if key.startswith("h_"):
            headers[key[2:].replace("_", "-")] = unquote(value)

    # 🔥 PATRON FIX
    if "/patron/" in m3u_url:
        print("Patron link detected")

    try:
        # resolve
        result = resolve_m3u8_link(m3u_url, headers)
        final_url = result["resolved_url"]

        r = requests.get(final_url, headers=headers, timeout=15)
        r.raise_for_status()

        content = r.text
        parsed = urlparse(final_url)

        base = f"{parsed.scheme}://{parsed.netloc}{parsed.path.rsplit('/',1)[0]}/"

        headers_query = "&".join([
            f"h_{quote(k)}={quote(v)}" for k, v in headers.items()
        ])

        output = []

        for line in content.splitlines():
            line = line.strip()

            if line.startswith("#EXT-X-KEY"):
                line = replace_key_uri(line, headers_query)

            elif line and not line.startswith("#"):
                full_url = urljoin(base, line)
                line = f"/proxy/ts?url={quote(full_url)}&{headers_query}"

            output.append(line)

        return Response("\n".join(output), content_type="application/vnd.apple.mpegurl")

    except Exception as e:
        return str(e), 500

# ✅ TS STREAM
@app.route('/proxy/ts')
def proxy_ts():
    url = request.args.get('url', '')
    headers = {}

    for key, value in request.args.items():
        if key.startswith("h_"):
            headers[key[2:].replace("_", "-")] = unquote(value)

    r = requests.get(url, headers=headers, stream=True)

    return Response(r.iter_content(8192), content_type="video/mp2t")

# ✅ KEY
@app.route('/proxy/key')
def proxy_key():
    url = request.args.get('url', '')
    headers = {}

    for key, value in request.args.items():
        if key.startswith("h_"):
            headers[key[2:].replace("_", "-")] = unquote(value)

    r = requests.get(url, headers=headers)
    return Response(r.content, content_type="application/octet-stream")

# ✅ TEST
@app.route('/')
def home():
    return "WORKING ✅"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=7860)
