TEMPLATE = r"""
function FindProxyForURL(url, host) {{
  if (dnsDomainIs(host, ".kancolle-server.com")) {{
    return "PROXY {host}:{port}";
  }}
  if (dnsDomainIs(host, "mitm.it")) {{
      return "PROXY {host}:{port}";
  }}
  return "DIRECT";
}}
"""


def generate_pac_script(host: str, port: int) -> str:
    return TEMPLATE.format(
        host=host,
        port=port,
    ).lstrip()
