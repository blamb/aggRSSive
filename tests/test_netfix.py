import socket

from aggrssive import netfix


def test_parse_tolerates_spacing_and_separators():
    assert netfix.parse(" a.example = 1.2.3.4 ; B.Example=5.6.7.8,bad, =9") == {"a.example": "1.2.3.4", "b.example": "5.6.7.8"}


def test_override_redirects_resolution_only_for_listed_hosts():
    orig = socket.getaddrinfo
    try:
        netfix.install("pinned.example=127.0.0.1")
        assert socket.getaddrinfo("pinned.example", 80)[0][4][0] == "127.0.0.1"
        assert socket.getaddrinfo("PINNED.example", 80)[0][4][0] == "127.0.0.1"
        assert socket.getaddrinfo("localhost", 80)  # untouched names still resolve
    finally:
        socket.getaddrinfo = orig
        netfix._overrides.clear()
