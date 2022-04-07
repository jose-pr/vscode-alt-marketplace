import json
from typing import Literal
from flask import Blueprint, Flask, request, Response, abort
import urllib.parse

from src import Gallery
from src.components.sources import LocalGallerySrc
from src.models.gallery import AssetType
from src.utils.extension import get_version_asset, get_version
from src.utils.matching import simple_query
from tests.common import debug_run

app = Flask(__name__)


gallery_bp = Blueprint("vscode-marketplace-gallery", "gallery-api")
assets_bp = Blueprint("assets", "assets")
# https://update.code.visualstudio.com/commit:${commit_sha}/server-linux-x64/stable
# https://marketplace.visualstudio.com/items?itemName=rust-lang.rust


gallery = Gallery(
    LocalGallerySrc(
        "private",
        proxy_url=lambda filepath, type, ext, ver: f"https://127.0.0.1/assets/{urllib.parse.quote_plus(filepath)}",
    )
)


@gallery_bp.route("/extensions/<extensionId>/<version>/assets/<asset>")
def get_extension_asset(extensionId: str, version: str, asset: str):
    src: LocalGallerySrc = gallery.exts_src
    extuid = src.uid_map.get(extensionId.lower(), None)
    if extuid:
        ext = src.exts[extuid]
        ver = get_version(ext, version)
        if ver:
            return get_asset(
                get_version_asset(ver, AssetType.VSIX), asset, "attachment"
            )
    abort(404)


@gallery_bp.route(
    "/publishers/<publisher>/vsextensions/<extension>/<version>/vspackage"
)
def get_publisher_extension(publisher: str, extension: str, version: str):
    src: LocalGallerySrc = gallery.exts_src
    ext = src.exts.get(f"{publisher}.{extension}".lower(), None)
    if ext:
        ver = get_version(ext, version)
        if ver:
            return get_asset(get_version_asset(ver, AssetType.VSIX), AssetType.VSIX)
    abort(404)


@gallery_bp.route("/extensionquery", methods=["POST", "GET"])
def extension_query():
    query = (
        request.json
        if request.method == "POST"
        else simple_query(request.args.get("search_text", type=str) or "")
    )
    resp = gallery.extension_query(query)
    return Response(json.dumps(resp), 200)


@assets_bp.route("/<path:path>/<asset>")
def get_asset(
    path: str, asset: str, disposition: Literal["inline", "attachment"] = "inline"
):
    vsix = urllib.parse.unquote_plus(path)
    src: LocalGallerySrc = gallery.exts_src
    filename, data, mime = src.get_asset(vsix, asset)
    if filename:
        return Response(
            data,
            mimetype=mime,
            headers={
                "Content-Disposition": f"{disposition}; filename={filename}; filename*=utf-8''{filename}"
            },
        )
    else:
        abort(404)


app.register_blueprint(assets_bp, url_prefix="/assets")
app.register_blueprint(gallery_bp, url_prefix="/_apis/public/gallery")

debug_run(app)
