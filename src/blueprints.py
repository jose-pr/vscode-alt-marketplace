import json, urllib.parse
from flask import Blueprint, Response, request

from .utils.matching import simple_query
from .utils.flask import return_asset
from .components import IGallery, IAssetSrc


def generate_gallery_blueprint(gallery: IGallery):
    gallery_bp = Blueprint("vscode-marketplace-gallery", "gallery-api")

    def get_extension_asset(extensionId: str, version: str | None, asset: str):
        data, name = gallery.get_extension_asset(
            extensionId, version=version, asset=asset
        )
        return return_asset(data, filename=name, disposition="attachment")

    gallery_bp.route("/extensions/<extensionId>/<version>/assets/<asset>")(
        get_extension_asset
    )

    def get_publisher_extension(publisher: str, extension: str, version: str):
        data, name = gallery.get_publisher_vspackage(publisher, extension, version)
        return return_asset(data, filename=name, disposition="attachment")

    gallery_bp.route(
        "/publishers/<publisher>/vsextensions/<extension>/<version>/vspackage"
    )(get_publisher_extension)

    def extension_query():
        query = (
            request.json
            if request.method == "POST"
            else simple_query(request.args.get("search_text", type=str) or "")
        )
        resp = gallery.extension_query(query)
        return Response(json.dumps(resp), 200)
    gallery_bp.route("/extensionquery", methods=["POST", "GET"])(extension_query)

    return gallery_bp

assets_bp = Blueprint("assets", "assets")
web_bp = Blueprint("web", "web")

def generate_asset_uri(filepath):
    return  f"{request.host_url}/assets/{urllib.parse.quote_plus(filepath)}"

def generate_assets_blueprint(src:IAssetSrc):
    assets_bp = Blueprint("assets", "assets")
    def get_asset(path: str, asset: str):
        vsix = urllib.parse.unquote_plus(path)
        return return_asset(*src.get_asset(vsix, asset))
    assets_bp.route("/<path:path>/<asset>")(get_asset)
    return assets_bp