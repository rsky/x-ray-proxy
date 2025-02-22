import hashlib

import mitmproxy.http

from xrayproxy.lib.pac import generate_pac_script

_cache: dict[str, tuple[bytes, str]] = {}


def get_pac_script_and_etag(host: str, port: int) -> tuple[bytes, str]:
    key = f"{host}:{port}"
    if key not in _cache:
        script = generate_pac_script(host, port).encode()
        m = hashlib.md5()
        m.update(script)
        md5sum = m.hexdigest()
        etag = f'"{md5sum}"'
        _cache[key] = (script, etag)

    return _cache[key]


def request(flow: mitmproxy.http.HTTPFlow) -> None:
    if flow.request.path == "/proxy.pac":
        script, etag = get_pac_script_and_etag(flow.request.host, flow.request.port)

        if flow.request.headers.get("If-None-Match") == etag:
            flow.response = mitmproxy.http.Response.make(
                status_code=304,
                content=b"",
            )
        else:
            flow.response = mitmproxy.http.Response.make(
                status_code=200,
                content=script,
                headers={
                    "Content-Type": "application/x-ns-proxy-autoconfig",
                    "ETag": etag,
                },
            )
