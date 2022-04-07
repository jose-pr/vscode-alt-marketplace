import json
from flask import Blueprint, Flask, request, Response
from pathlib import Path
import urllib.parse
import requests


from src import Gallery, IterExtensionSrc
from src.components.sources import ProxyExtensionSrc
from src.utils.matching import simple_query
from tests.common import debug_run

app = Flask(__name__)


gallery_bp = Blueprint("vscode-marketplace-gallery", "gallery-api")
proxy_bp = Blueprint("generic_proxy", "proxy")

@app.route("/")
def index():
    return "Web App with Python Flask!"


list_gallery = Gallery(
    ProxyExtensionSrc(
        IterExtensionSrc(json.loads(Path("private/extensions.json").read_text())),
        lambda uri, type, ext, ver: f"https://127.0.0.1/proxy/{urllib.parse.quote_plus(uri)}",
    )
)


@gallery_bp.route("/extensionquery", methods=["POST", "GET"])
def extension_query():
    query = (
        request.json
        if request.method == "POST"
        else simple_query(request.args.get("search_text", type=str) or "")
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

debug_run(app)