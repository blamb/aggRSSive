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
        netfix._resolve.clear()


def test_rewrite_form_changes_target_and_keeps_host_header():
    try:
        netfix.install("lms.example=http://10.0.0.5, other.example=1.2.3.4")
        url, headers = netfix.rewrite("https://LMS.example/mod/lti/openid-configuration.php?x=1")
        assert url == "http://10.0.0.5/mod/lti/openid-configuration.php?x=1"
        assert headers == {"Host": "LMS.example"}
        assert netfix.rewrite("https://elsewhere.example/a") == ("https://elsewhere.example/a", {})
        assert "other.example" in netfix._resolve and "other.example" not in netfix._rewrite
    finally:
        socket.getaddrinfo = netfix._orig_getaddrinfo
        netfix._rewrite.clear(); netfix._resolve.clear()
