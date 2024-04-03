import json
import os
import random
import re
import typing
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, overload
from urllib.parse import unquote

import requests

if typing.TYPE_CHECKING:
    from . import Options
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
    def get_cookie_from_args(args: "Options | None", needed: Literal[True]) -> str:
        pass

    @overload
    def get_cookie_from_args(args: "Options | None", needed: Literal[False]) -> "str | None":
        pass


def get_cookie_from_args(args, needed=True):
    """
    Returns a Digipad cookie, checking first in the arguments. If `needed`, raise an exception.
    """
    from . import Options

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


def extract_data(response: requests.Response):
    """
    Extract JSON data from a Digipad response.
    """
    match = re.search(r'<script id="vike_pageContext"[^>]*>(.*?)</script>', response.text)
    if not match:
        raise ValueError("Can't extract data from response")

    return json.loads(match[1])


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
            data.append(
                {
                    "id": pad.id,
                    "hash": pad.hash,
                    "title": pad.title,
                    "access": pad.access,
                    "code": pad.code,
                    "columns": pad.columns,
                }
            )
        else:
            data.append(
                {
                    "id": pad.id,
                    "title": pad.title,
                }
            )

    if verbose:

        def fix_dict(item: dict):
            """Replace the keys by the verbose names in the specified `item`."""
            ret = {}
            for key, value in item.items():
                ret[verbose_names.get(key, key)] = value
            return ret

        return [fix_dict(item) for item in data]

    return data


def get_secret_key(secret_key=""):
    """Return the secret key that will be used in the web app."""
    if secret_key and Path(secret_key).exists():
        # file containing the secret key
        return Path(secret_key).read_text()

    if isinstance(secret_key, Path):
        # default value of the --secret-key parameter
        secret_key_file = secret_key
        secret_key = random.randbytes(64).hex()
        Path(secret_key_file).write_text(secret_key)
        return secret_key

    return secret_key or os.getenv("DIGIPAD_SECRET_KEY", "")
