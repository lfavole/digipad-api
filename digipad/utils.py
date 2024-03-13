from argparse import Namespace
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, overload
from urllib.parse import unquote

import requests


@dataclass
class UserInfo:
    """
    Information about a Digipad user.
    """
    username: str = ""
    name: str = ""
    color: str = "#495057"
    logged_in: bool = True
    cookie: str = ""

    def __bool__(self):
        return self.logged_in

    def __str__(self):
        return self.username + (f" ({self.name})" if self.name else "")


COOKIE_FILE = Path.home() / ".digipad_cookie"


@overload
def get_cookie_from_args(args: Namespace | None, needed: Literal[True]) -> str:
    pass


@overload
def get_cookie_from_args(args: Namespace | None, needed: Literal[False]) -> str | None:
    pass


def get_cookie_from_args(args, needed=True):
    """
    Returns a Digipad cookie, checking first in the arguments. If `needed`, raise an exception.
    """
    if args and args.cookie is not None:
        return unquote(args.cookie)

    return get_cookie(needed)


def get_cookie(needed=True):
    """
    Returns a Digipad cookie. If `needed`, raise an exception.
    """
    if COOKIE_FILE.exists():
        return COOKIE_FILE.read_text(encoding="utf-8")

    if needed:
        raise RuntimeError("Can't get cookie, please pass --cookie argument or use digipad set-cookie")

    return None


def get_anon_userinfo(pad_id, pad_hash):
    """
    Return anonymous user information from a pad ID and a hash.
    """
    req = requests.get(f"https://digipad.app/p/{pad_id}/{pad_hash}")
    digipad_cookie = unquote(req.cookies["digipad"])

    data = extract_data(req)
    username = data["pageProps"]["identifiant"]
    name = data["pageProps"]["nom"]
    logged_in = data["pageProps"]["statut"] != "invite"

    return UserInfo(username, name, logged_in=logged_in, cookie=digipad_cookie)


def get_userinfo(digipad_cookie):
    """
    Return user information from a Digipad cookie.
    """
    req = requests.get(
        "https://digipad.app",
        cookies={"digipad": digipad_cookie},
    )
    if not req.history or not 300 <= req.history[0].status_code < 400:
        return UserInfo()

    username = req.url.rstrip("/").rsplit("/")[-1]

    try:
        data = extract_data(req)
    except ValueError:
        return UserInfo(username, cookie=digipad_cookie)
    name = data.get("pageProps", {}).get("nom", "")
    return UserInfo(username, name, cookie=digipad_cookie)


def extract_data(response: requests.Response):
    """
    Extract JSON data from a Digipad response.
    """
    match = re.search(r'<script id="vike_pageContext"[^>]*>(.*?)</script>', response.text)
    if not match:
        raise ValueError("Can't extract data from response")

    return json.loads(match[1])
