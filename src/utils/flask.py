from flask import Response, request


def allow_cors(response: Response):
    origin = request.headers.get("Origin")
    if origin:
        response.headers.add("Access-Control-Allow-Origin", origin)
    #response.headers.add("Access-Control-Allow-Credentials", "true")
    if request.access_control_request_headers:
        response.access_control_allow_headers = request.access_control_request_headers
    if request.access_control_request_method:
        response.access_control_allow_methods = [request.access_control_request_method]
    return response