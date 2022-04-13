import html
from io import StringIO
import mimetypes
from typing import Literal
from flask import Flask, Response, abort, request
from pathlib import Path

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


def load_ssl_context(base_path: str, hostnames: "list[str]", ips: "list[str]"):
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
_MIMETYPE.readfp(
    StringIO(
        """
application/vsix				vsix
text/markdown                     md
"""
    )
)


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


def debug_run(
    app: Flask,
    base_path: str = "./private/marketplace.visualstudio.com",
    listen="127.0.0.1",
    hostnames=["marketplace.visualstudio.com", "vscode-gallery.local"],
):
    app.after_request(allow_cors)
    crt, key = load_ssl_context(
        base_path,
        hostnames,
        [listen],
    )
    app.run(
        host=listen,
        port=443,
        ssl_context=(
            crt,
            key,
        ),
    )
