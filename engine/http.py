"""One shared HTTP client, so repeated calls to the same host reuse a warm
connection instead of paying a new TLS handshake each time. Redirects are never
followed, so a request cannot be bounced somewhere it was not sent, and no cookie
is kept, since one client carries every user's calls.
"""

import threading
from http.cookiejar import CookieJar, DefaultCookiePolicy

import httpx

_lock = threading.Lock()
_client = None


def client():
    global _client
    with _lock:
        if _client is None:
            _client = make_client()
        return _client


def make_client(transport=None):
    return httpx.Client(
        timeout=httpx.Timeout(20.0, connect=5.0),
        limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
        follow_redirects=False,
        cookies=CookieJar(policy=DefaultCookiePolicy(allowed_domains=[])),
        transport=transport,
    )
