import html
from io import StringIO
import json
import mimetypes
from typing import List, Literal
from flask import Response, abort, request, Blueprint
from pathlib import Path

from .matching import simple_query
from ..components import IGallery
from markdown import markdown


def allow_cors(response: Response):
    origin = request.headers.get("Origin")
    if origin:
        response.headers.add("Access-Control-Allow-Origin", origin)
    # response.headers.add("Access-Control-Allow-Credentials", "true")
    if request.access_control_request_headers:
        response.access_control_allow_headers = request.access_control_request_headers
    if request.access_control_request_method:
        response.access_control_allow_methods = [request.access_control_request_method]
    return response


def load_ssl_context(base_path: str, hostnames: List[str], ips: List[str]):
    host = hostnames[0]
    crt = Path(f"{base_path}.crt")
    key = crt.with_suffix(".key")

    if not crt.exists() or not key.exists():
        from ..vendor.cert_gen import generate_selfsigned_cert

        crt_, key_ = generate_selfsigned_cert(host, hostnames, ips)
        crt.write_bytes(crt_)
        key.write_bytes(key_)
    return crt, key


_MIMETYPE = mimetypes.MimeTypes(strict=False)
_MIMETYPE.readfp(StringIO("""
application/vsix				vsix
text/markdown                     md
"""))


def render_as_html(data: bytes, mimetype: str = None):
    if data is None:
        return ""

    if mimetype is None or mimetype.startswith("text/"):
        text = data.decode()
        if mimetype in ["text/markdown", "text/x-markdown"]:
            return markdown(text)
        elif mimetype == "text/html":
            return text
        else:
            return f"<pre>{html.escape(text)}</pre>"
    else:
        return ""


def render_asset(data: bytes, filename: str):
    return render_as_html(data, _MIMETYPE.guess_type(filename)[0])


def return_asset(
    data: bytes,
    filename: str,
    disposition: Literal["inline", "attachment"] = "inline",
    mimetype: str = None,
):
    if data is None:
        abort(404)

    headers = {}
    if filename:
        headers[
            "Content-Disposition"
        ] = f"{disposition}; filename={filename}; filename*=utf-8''{filename}"
        if not mimetype:
            mimetype = _MIMETYPE.guess_type(filename)[0]

    return Response(data, mimetype=mimetype, headers=headers)

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

