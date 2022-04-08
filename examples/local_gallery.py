import json
from pathlib import Path
from typing import Dict, Literal, OrderedDict
from flask import Blueprint, Flask, render_template_string, request, Response, abort
import urllib.parse

from markdown import markdown

from src import Gallery
from src.components.common import IGallery
from src.components.sources import LocalGallerySrc
from src.models.gallery import (
    VSCODE_INSTALLATION_TARGET,
    AssetType,
    GalleryExtensionVersion,
    FilterType,
    GalleryFlags,
)
from src.utils.extension import get_version_asset, get_version, get_version_asset_uri
from src.utils.flask import generate_gallery_blueprint, render_asset, return_asset
from src.utils.matching import simple_query
from tests.common import debug_run

app = Flask(__name__)


assets_bp = Blueprint("assets", "assets")
web_bp = Blueprint("web", "web")
# https://update.code.visualstudio.com/commit:${commit_sha}/server-linux-x64/stable
# https://marketplace.visualstudio.com/items?itemName=rust-lang.rust


gallery = Gallery(
    LocalGallerySrc(
        "private",
        proxy_url=lambda filepath, type, ext, ver: f"https://127.0.0.1/assets/{urllib.parse.quote_plus(filepath)}",
    )
)


gallery_bp = generate_gallery_blueprint(gallery)

@assets_bp.route("/<path:path>/<asset>")
def get_asset(path: str, asset: str):
    vsix = urllib.parse.unquote_plus(path)
    return return_asset(*gallery.asset_src.get_asset(vsix, asset))


@web_bp.route("/items")
def items():
    itemName = request.args.get("itemName", type=str)
    ext = gallery.exts_src.get_extension(itemName)

    if not ext:
        abort(404)
    ver = get_version(ext, None)
    if not ver:
        abort(404)

    vsix = get_version_asset(ver, AssetType.VSIX)
    tabs: Dict[str, tuple[str, str]] = OrderedDict()
    tabs[AssetType.Details.name] = "Overview", render_asset(
        *gallery.asset_src.get_asset(vsix, AssetType.Details)
    )
    tabs[AssetType.Changelog.name] = "Change Log", render_asset(
        *gallery.asset_src.get_asset(vsix, AssetType.Changelog)
    )

    return render_template_string(
        Path("examples/item.html.j2").read_text(), tabs=tabs, ext=ext, ver=ver
    )

@web_bp.route("/")
def landing():
    query = simple_query(
        request.args.get("search_text", type=str)
        or [
            {"filterType": FilterType.Target, "value": VSCODE_INSTALLATION_TARGET},
            {
                "filterType": FilterType.ExcludeWithFlags,
                "value": GalleryFlags.Unpublished,
            },
        ],
        flags=GalleryFlags.IncludeAssetUri
        | GalleryFlags.IncludeFiles
        | GalleryFlags.IncludeLatestVersionOnly,
    )
    resp = gallery.extension_query(query)
    return render_template_string(
        Path("examples/landing.html.j2").read_text(),
        exts=resp["results"][0]["extensions"],
    )


app.register_blueprint(assets_bp, url_prefix="/assets")
app.register_blueprint(gallery_bp, url_prefix="/_apis/public/gallery")
app.register_blueprint(web_bp)


app.jinja_env.globals.update(get_asset_uri=get_version_asset_uri, AssetType=AssetType)

debug_run(app)
