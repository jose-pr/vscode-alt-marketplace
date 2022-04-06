import json
from flask import Blueprint, Flask, request, Response
from pathlib import Path

from src import Gallery, IterExtensionSrc
from src.components import gallery
from src.utils.flask import allow_cors
from src.utils.matching import simple_text_query

app = Flask(__name__)


gallery_bp = Blueprint('vscode-marketplace-gallery', 'gallery-api')

@app.route("/")
def index():
    return "Web App with Python Flask!"


list_gallery = Gallery(
    IterExtensionSrc(json.loads(Path("examples/extensions.json").read_text()))
)

@gallery_bp.route("/extensionquery", methods=["POST", "GET"])
def extension_query():
    query = request.json if request.method == "POST" else  simple_text_query(request.args.get('search_text', type=str) or "")
    resp = list_gallery.extension_query(query)
    return Response(json.dumps(resp), 200)

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
