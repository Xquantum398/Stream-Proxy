from flask import Flask, request, Response
import requests
from urllib.parse import urlparse, urljoin, quote

app = Flask(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Referer": "https://patronyayin1.cfd/",
    "Origin": "https://patronyayin1.cfd/"
}

session = requests.Session()
session.headers.update(HEADERS)

def rewrite_m3u8(content, base_url):
    parsed = urlparse(base_url)
    base = f"{parsed.scheme}://{parsed.netloc}{parsed.path.rsplit('/',1)[0]}/"
    out = []

    for line in content.splitlines():
        line = line.strip()

        if line.startswith("#EXT-X-KEY") and "URI=" in line:
            key = line.split('"')[1]
            line = line.replace(key, f"/proxy/key?url={quote(key)}")

        elif line and not line.startswith("#"):
            if not line.startswith("http"):
                line = urljoin(base, line)

            line = f"/proxy/ts?url={quote(line)}"

        out.append(line)

    return "\n".join(out)

@app.route("/proxy/m3u")
def m3u():
    url = request.args.get("url")

    session.get("https://patronyayin1.cfd/")

    r = session.get(url)
    data = rewrite_m3u8(r.text, r.url)

    return Response(data, content_type="application/vnd.apple.mpegurl")

@app.route("/proxy/ts")
def ts():
    url = request.args.get("url")
    r = session.get(url, stream=True)
    return Response(r.iter_content(8192), content_type="video/mp2t")

@app.route("/proxy/key")
def key():
    url = request.args.get("url")
    return session.get(url).content

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=7860)
