from flask import Flask

from src.utils.flask import allow_cors, load_ssl_context


def debug_run(app:Flask):
    app.after_request(allow_cors)
    crt, key = load_ssl_context(
        "./private/marketplace.visualstudio.com",
        ["marketplace.visualstudio.com", "vscode-gallery.local"],
        ["127.0.0.1"],
    )
    app.run(
        host="127.0.0.1",
        port=443,
        ssl_context=(
            crt,
            key,
        ),
    )
