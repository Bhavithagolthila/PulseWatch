"""URL validation used before a monitor is saved and again before every check.

Limitation (also in the README): DNS is resolved here to *validate* the address, but the
HTTP client resolves the name again when it connects. A malicious DNS server could answer
differently the second time (DNS rebinding). Pinning the validated IP to the socket is
future work.
"""
import ipaddress
import socket
from urllib.parse import urlsplit


class UnsafeTarget(ValueError):
    """The URL points somewhere we refuse to connect to."""


class UnresolvableHost(UnsafeTarget):
    """The hostname does not resolve. For a health check this means DOWN, not 'blocked'."""


BLOCKED_HOSTS = {"localhost", "metadata.google.internal"}
BLOCKED_SUFFIXES = (".localhost", ".local", ".internal")


def _is_public(address) -> bool:
    # An IPv4 address wrapped in IPv6 (::ffff:127.0.0.1) must be judged as the IPv4 address.
    mapped = getattr(address, "ipv4_mapped", None)
    if mapped is not None:
        address = mapped
    return address.is_global and not address.is_multicast


def validate_public_url(url: str) -> None:
    parts = urlsplit(url)
    if parts.scheme not in {"http", "https"} or not parts.hostname:
        raise UnsafeTarget("Only valid HTTP and HTTPS URLs are allowed.")
    if parts.username or parts.password:
        raise UnsafeTarget("URLs containing embedded credentials are not allowed.")
    try:
        port = parts.port  # raises ValueError for e.g. ":99999" or ":abc"
    except ValueError:
        raise UnsafeTarget("The URL contains an invalid port.")

    host = parts.hostname.lower().rstrip(".")
    if host in BLOCKED_HOSTS or host.endswith(BLOCKED_SUFFIXES):
        raise UnsafeTarget("Local and internal hostnames are not allowed.")

    try:
        addresses = {ipaddress.ip_address(host)}
    except ValueError:
        # Not a literal IP: resolve it. getaddrinfo also understands odd forms such as
        # "2130706433" or "0x7f.1", which it turns into 127.0.0.1 so they get blocked below.
        try:
            infos = socket.getaddrinfo(host, port or (443 if parts.scheme == "https" else 80), type=socket.SOCK_STREAM)
        except OSError:
            raise UnresolvableHost("The hostname could not be resolved.")
        addresses = {ipaddress.ip_address(item[4][0].split("%")[0]) for item in infos}

    if not addresses:
        raise UnresolvableHost("The hostname could not be resolved.")
    for address in addresses:
        if not _is_public(address):
            raise UnsafeTarget("Private, loopback, link-local, multicast, and reserved destinations are not allowed.")
