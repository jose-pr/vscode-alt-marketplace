import json
from flask import Flask, request, Response
from pathlib import Path

from src import Gallery, IterExtensionSrc

app = Flask(__name__)


@app.route("/")
def index():
    return "Web App with Python Flask!"


list_gallery = Gallery(
    IterExtensionSrc(json.loads(Path("examples/extensions.json").read_text()))
)


@app.route("/_apis/public/gallery/extensionquery", methods=["POST", "GET"])
def extension_query():
    query = request.json
    resp = list_gallery.extension_query(query)
    return Response(json.dumps(resp), 200)


@app.after_request
def after_request(response: Response):
    origin = request.headers.get("Origin")
    if origin:
        response.headers.add("Access-Control-Allow-Origin", origin)
    # if request.method == 'OPTIONS':
    response.headers.add("Access-Control-Allow-Credentials", "true")
    if request.access_control_request_headers:
        response.access_control_allow_headers = request.access_control_request_headers
    if request.access_control_request_method:
        response.access_control_allow_methods = [request.access_control_request_method]
    return response


crt = Path("./private/marketplace.visualstudio.com.crt")
key = Path("./private/marketplace.visualstudio.com.key")

if not crt.exists() or not key.exists():
    from vendor.cert_gen import generate_selfsigned_cert

    crt_, key_ = generate_selfsigned_cert(
        "marketplace.visualstudio.com",
        ["vscode-gallery.local"],
        ["127.0.0.2"],
        None,
    )
    Path("./private/marketplace.visualstudio.com.crt").write_bytes(crt_)
    Path("./private/marketplace.visualstudio.com.key").write_bytes(key_)


app.run(
    host="127.0.0.2",
    port=443,
    ssl_context=(
        crt,
        key,
    ),
)
