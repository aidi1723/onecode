from __future__ import annotations

import urllib.request
from urllib.parse import urlsplit


def should_strip_redirect_auth(*, old_url: str, new_url: str) -> bool:
    old = urlsplit(old_url)
    new = urlsplit(new_url)
    if (old.hostname or "").casefold() != (new.hostname or "").casefold():
        return True
    return old.scheme.casefold() == "https" and new.scheme.casefold() == "http"


class StripAuthRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        new_req = super().redirect_request(req, fp, code, msg, headers, newurl)
        if new_req is not None and should_strip_redirect_auth(
            old_url=req.full_url,
            new_url=new_req.full_url,
        ):
            for key in list(new_req.headers.keys()):
                if key.lower() in ("authorization", "api-key"):
                    del new_req.headers[key]
        return new_req
