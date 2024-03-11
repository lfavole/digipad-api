import functools
import json
import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote

import requests


@dataclass
class UserInfo:
    username: str
    name: str = ""
    color: str = ""
    logged_in: bool = True

    def __bool__(self):
        return self.logged_in


COOKIE_FILE = Path.home() / ".digipad_cookie"


def get_cookie(args=None, needed=True):
    if args and args.cookie is not None:
        return unquote(args.cookie)

    if COOKIE_FILE.exists():
        return COOKIE_FILE.read_text(encoding="utf-8")

    if needed:
        raise RuntimeError("Can't get cookie, please pass --cookie argument or use digipad save-cookie")

    return None


@functools.lru_cache
def get_anon_cookie_and_req(pad_id, pad_hash):
    req = requests.get(f"https://digipad.app/p/{pad_id}/{pad_hash}")
    return req, unquote(req.cookies["digipad"])


def get_anon_cookie(pad_id, pad_hash):
    return get_anon_cookie_and_req(pad_id, pad_hash)[1]


@functools.lru_cache
def get_userinfo(digipad_cookie=None, pad_id=None, pad_hash=None) -> UserInfo:
    if pad_id and pad_hash and not digipad_cookie:
        req, digipad_cookie = get_anon_cookie_and_req(pad_id, pad_hash)
        match = re.search(r'<script id="vike_pageContext"[^>]*>(.*?)</script>', req.text)
        if not match:
            raise ValueError("Can't get user information from pad page")

        data = json.loads(match[1])
        username = data["pageProps"]["identifiant"]
        name = data["pageProps"]["nom"]
        logged_in = data["pageProps"]["statut"] != "invite"
        return UserInfo(username, name, logged_in=logged_in)

    req = requests.get(
        "https://digipad.app",
        cookies={"digipad": digipad_cookie or ""},
    )
    if not req.history or req.history[0].status_code < 300 or req.history[0].status_code >= 400:
        raise ValueError("Not logged in")

    username = req.url.rstrip("/").rsplit("/")[-1]

    match = re.search(r'<script id="vike_pageContext"[^>]*>(.*?)</script>', req.text)
    if not match:
        name = ""
    else:
        data = json.loads(match[1])
        name = data.get("pageProps", {}).get("nom", "")

    return UserInfo(username, name)
