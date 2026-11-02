import socket
from unittest.mock import patch

import pytest

from app.services.security import UnresolvableHost, UnsafeTarget, validate_public_url


def fake_dns(*addresses):
    family = lambda a: socket.AF_INET6 if ":" in a else socket.AF_INET
    return lambda *args, **kwargs: [(family(a), socket.SOCK_STREAM, 6, "", (a, 0)) for a in addresses]


@pytest.mark.parametrize(
    "url",
    [
        "ftp://example.com",
        "http://localhost",
        "http://127.0.0.1",
        "http://10.0.0.1",
        "http://192.168.1.10",
        "http://169.254.169.254/latest/meta-data",  # cloud metadata service
        "http://[::1]/",
        "http://[::ffff:127.0.0.1]/",  # IPv4 hidden inside IPv6
        "http://100.64.0.1/",  # carrier-grade NAT range
        "http://printer.local",
        "https://user:pass@example.com",
        "https://example.com:99999",
    ],
)
def test_rejects_unsafe_destinations(url):
    with pytest.raises(UnsafeTarget):
        validate_public_url(url)


def test_rejects_unresolvable_host():
    with patch("app.services.security.socket.getaddrinfo", side_effect=socket.gaierror):
        with pytest.raises(UnresolvableHost):
            validate_public_url("https://definitely-not-a-real-pulsewatch-domain.invalid")


def test_accepts_host_resolving_to_public_ip():
    with patch("app.services.security.socket.getaddrinfo", fake_dns("93.184.216.34")):
        validate_public_url("https://example.com")


def test_rejects_public_looking_name_that_resolves_to_private_ip():
    with patch("app.services.security.socket.getaddrinfo", fake_dns("10.1.2.3")):
        with pytest.raises(UnsafeTarget):
            validate_public_url("https://innocent-looking.example.com")


def test_rejects_if_any_resolved_address_is_private():
    with patch("app.services.security.socket.getaddrinfo", fake_dns("93.184.216.34", "127.0.0.1")):
        with pytest.raises(UnsafeTarget):
            validate_public_url("https://mixed.example.com")
