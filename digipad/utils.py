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
    from .edit import PadList


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
    connection_error: bool = False

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
    try:
        req = requests.get(f"https://digipad.app/p/{pad_id}/{pad_hash}")
    except OSError:
        return UserInfo(connection_error=True)

    cookie = unquote(req.cookies["digipad"])
    data = extract_data(req)

    return UserInfo.from_json(data, cookie)


def get_userinfo(digipad_cookie):
    """
    Return user information from a Digipad cookie.
    """
    try:
        req = requests.get(
            "https://digipad.app",
            cookies={"digipad": digipad_cookie},
        )
    except OSError:
        return UserInfo(connection_error=True)
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


def login(username, password):
    """Log into Digipad and return the corresponding userinfo."""
    req = requests.post(
        "https://digipad.app/api/connexion",
        json={
            "identifiant": username,
            "motdepasse": password,
        },
    )
    req.raise_for_status()

    cookie = None
    for header, value in req.headers.items():
        if header != "Set-Cookie":
            continue
        value, _, _ = value.partition(";")
        key, _, value = value.partition("=")
        if key != "digipad":
            continue
        cookie = unquote(value)
        break

    if cookie is None:
        raise RuntimeError("Can't get Digipad cookie")

    return get_userinfo(cookie)


def get_pads_table(pads: "PadList", verbose=True, all_data=False):
    """Return a `list` of `dict`s containing information about each pad in a pad list."""
    verbose_names = {
        "id": "Pad ID",
        "hash": "Pad hash",
        "title": "Pad title",
        "access": "Access",
        "code": "PIN code",
        "columns": "Columns",
    }

    data = []
    for pad in pads:
        if all_data:
            data.append({
                "id": pad.id,
                "hash": pad.hash,
                "title": pad.title,
                "access": pad.access,
                "code": pad.code,
                "columns": pad.columns,
            })
        else:
            data.append({
                "id": pad.id,
                "title": pad.title,
            })

    if verbose:
        def fix_dict(item: dict):
            """Replace the keys by the verbose names in the specified `item`."""
            ret = {}
            for key, value in item.items():
                ret[verbose_names.get(key, key)] = value
            return ret

        return [fix_dict(item) for item in data]

    return data
