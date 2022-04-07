import json
from flask import Blueprint, Flask, request, Response, send_from_directory
from pathlib import Path
import urllib.parse
import requests


from src import Gallery, IterExtensionSrc
from src.components import gallery
from src.components.sources import LocalGallerySrc, ProxyExtensionSrc
from src.models.gallery import AssetType
from src.utils.flask import allow_cors
from src.utils.matching import simple_text_query

app = Flask(__name__)


gallery_bp = Blueprint("vscode-marketplace-gallery", "gallery-api")
local_bp = Blueprint("local-server", "local")
# https://update.code.visualstudio.com/commit:${commit_sha}/server-linux-x64/stable
# https://marketplace.visualstudio.com/items?itemName=rust-lang.rust


gallery = Gallery(
    LocalGallerySrc(
        "examples",
        proxy_url=lambda filepath, type, ext, ver: f"https://127.0.0.1/local/{urllib.parse.quote_plus(filepath)}",
    )
)


@gallery_bp.route("/extensionquery", methods=["POST", "GET"])
def extension_query():
    query = (
        request.json
        if request.method == "POST"
        else simple_text_query(request.args.get("search_text", type=str) or "")
    )
    resp = gallery.extension_query(query)
    return Response(json.dumps(resp), 200)


@local_bp.route("/<path:path>/<asset>")
def proxy(path: str, asset: str):
    file = urllib.parse.unquote_plus(path)
    src: LocalGallerySrc = gallery.exts_src
    if AssetType(asset) == AssetType.VSIX:
        return send_from_directory(Path("examples").resolve(), file)
    else:
        data, mime = src._get_asset(path, asset)
        return Response(data, mimetype=mime)


app.register_blueprint(local_bp, url_prefix="/local")
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
