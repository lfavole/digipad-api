import json
import re
import typing
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, overload
from urllib.parse import unquote

import requests

if typing.TYPE_CHECKING:
    from .__init__ import Options


@dataclass
class UserInfo:
    """
    Information about a Digipad user.
    """
    username: str = ""
    name: str = ""
    email: str = ""
    color: str = "#495057"
    language: str = ""
    logged_in: bool = True
    cookie: str = ""

    def __bool__(self):
        return self.logged_in

    def __str__(self):
        return self.username + (f" ({self.name})" if self.name else "")

    @classmethod
    def from_json(cls, data, cookie=""):
        """
        Returns a `UserInfo` object from JSON data extracted from a Digipad page.
        """
        page_props = data.get("pageProps", data)
        if not page_props.get("identifiant"):
            return cls(cookie=cookie)

        return cls(
            name=page_props.get("nom", ""),
            username=page_props.get("identifiant", ""),
            email=page_props.get("email", ""),
            color=page_props.get("couleur", ""),
            language=page_props.get("langue", ""),
            logged_in=page_props.get("statut", "utilisateur") == "utilisateur",
            cookie=cookie,
        )

    def full_info(self):
        """
        Return a string containing ALL the available information about the user.
        """
        ret = str(self)
        if self.language:
            ret += f"\nLanguage: {self.language:}"
        return ret


COOKIE_FILE = Path.home() / ".digipad_cookie"


if typing.TYPE_CHECKING:
    @overload
    def get_cookie_from_args(args: Options | None, needed: Literal[True]) -> str:
        pass

    @overload
    def get_cookie_from_args(args: Options | None, needed: Literal[False]) -> str | None:
        pass


def get_cookie_from_args(args, needed=True):
    """
    Returns a Digipad cookie, checking first in the arguments. If `needed`, raise an exception.
    """
    from .__init__ import Options
    if args and isinstance(args, Options) and args.cookie:
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

    cookie = unquote(req.cookies["digipad"])
    data = extract_data(req)

    return UserInfo.from_json(data, cookie)


def get_userinfo(digipad_cookie):
    """
    Return user information from a Digipad cookie.
    """
    req = requests.get(
        "https://digipad.app",
        cookies={"digipad": digipad_cookie},
    )
    if not req.history or not 300 <= req.history[0].status_code < 400:
        return UserInfo(logged_in=False)

    username = req.url.rstrip("/").rsplit("/")[-1]

    try:
        data = extract_data(req)
    except ValueError:
        return UserInfo(username, cookie=digipad_cookie)

    return UserInfo.from_json(data, digipad_cookie)


def extract_data(response: requests.Response):
    """
    Extract JSON data from a Digipad response.
    """
    match = re.search(r'<script id="vike_pageContext"[^>]*>(.*?)</script>', response.text)
    if not match:
        raise ValueError("Can't extract data from response")

    return json.loads(match[1])
