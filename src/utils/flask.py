from typing import List
from flask import Response, request
from pathlib import Path


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
