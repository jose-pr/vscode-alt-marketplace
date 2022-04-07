import json
from flask import Blueprint, Flask, request, Response
from pathlib import Path
import urllib.parse
import requests


from src import Gallery, IterExtensionSrc
from src.components import gallery
from src.components.sources import ProxyExtensionSrc
from src.utils.flask import allow_cors
from src.utils.matching import simple_text_query

app = Flask(__name__)


gallery_bp = Blueprint("vscode-marketplace-gallery", "gallery-api")
proxy_bp = Blueprint("generic_proxy", "proxy")
#https://update.code.visualstudio.com/commit:${commit_sha}/server-linux-x64/stable
#https://marketplace.visualstudio.com/items?itemName=rust-lang.rust

@app.route("/")
def index():
    return "Web App with Python Flask!"


list_gallery = Gallery(
    ProxyExtensionSrc(
        IterExtensionSrc(json.loads(Path("examples/extensions.json").read_text())),
        lambda uri, type, ext, ver: f"https://127.0.0.1/proxy/{urllib.parse.quote_plus(uri)}",
    )
)


@gallery_bp.route("/extensionquery", methods=["POST", "GET"])
def extension_query():
    query = (
        request.json
        if request.method == "POST"
        else simple_text_query(request.args.get("search_text", type=str) or "")
    )
    resp = list_gallery.extension_query(query)
    return Response(json.dumps(resp), 200)


@proxy_bp.route("/<path:path>")
def proxy(path: str):
    uri = urllib.parse.unquote_plus(path)
    resp = requests.get(uri, stream=True)
    return Response(
        resp.iter_content(chunk_size=10 * 1024),
        content_type=resp.headers["Content-Type"],
    )


app.register_blueprint(proxy_bp, url_prefix="/proxy")
app.register_blueprint(gallery_bp, url_prefix="/_apis/public/gallery")
app.after_request(allow_cors)


crt = Path("./private/marketplace.visualstudio.com.crt")
key = Path("./private/marketplace.visualstudio.com.key")

if not crt.exists() or not key.exists():
    from vendor.cert_gen import generate_selfsigned_cert

    crt_, key_ = generate_selfsigned_cert(
        "marketplace.visualstudio.com",
        ["vscode-gallery.local"],
        ["127.0.0.1"],
        None,
    )
    Path("./private/marketplace.visualstudio.com.crt").write_bytes(crt_)
    Path("./private/marketplace.visualstudio.com.key").write_bytes(key_)


app.run(
    host="127.0.0.1",
    port=443,
    ssl_context=(
        crt,
        key,
    ),
)
