import json
import re
from dataclasses import dataclass, field

import requests

from .utils import get_userinfo


@dataclass
class PadsList:
    created: dict[int, str] = field(default_factory=dict)
    visited: dict[int, str] = field(default_factory=dict)
    admin: dict[int, str] = field(default_factory=dict)
    favourite: dict[int, str] = field(default_factory=dict)
    folder_names: dict[str, str] = field(default_factory=dict)
    folders: dict[str, dict[int, str]] = field(default_factory=dict)
    all: dict[int, str] = field(default_factory=dict)
    pad_hashes: dict[int, str] = field(default_factory=dict)

    def get_pads(self, pad_ids: list[str]):
        ret = {}

        for pad_id in pad_ids:
            try:
                pad_id = int(pad_id)
                ret[pad_id] = self.pad_hashes.get(pad_id, "")
                continue
            except ValueError:
                pass

            try:
                *_, pad_id, pad_hash = str(pad_id).rstrip("/").split("/")
                pad_id = int(pad_id)
                if pad_hash:
                    self.pad_hashes[pad_id] = pad_hash
                ret[pad_id] = self.pad_hashes[pad_id]
                continue
            except ValueError:
                pass

            if pad_id in ("created", "visited", "admin", "favourite", "all"):
                ret.update(getattr(self, pad_id))
                continue

            ret.update(self.get_pads_in_folder(pad_id))

        return ret

    def get_pads_in_folder(self, folder_name):
        if folder_name in self.folders:
            # folder ID
            return self.folders[folder_name]

        # folder name
        for folder_id, folder_name_to_try in self.folder_names:
            if folder_name_to_try == folder_name:
                return self.folders[folder_id]

        raise ValueError(f"Can't find folder {folder_name}")


def get_all_pads(digipad_cookie=None):
    if not digipad_cookie:
        return PadsList()

    req = requests.get(
        "https://digipad.app/u/" + get_userinfo(digipad_cookie).username,
        allow_redirects=False,
        cookies={"digipad": digipad_cookie},
    )
    if 300 <= req.status_code < 400:
        raise ValueError("Not logged in")
    req.raise_for_status()

    match = re.search(r'<script id="vike_pageContext"[^>]*>(.*?)</script>', req.text)
    if not match:
        raise ValueError("Can't get pads list")

    data = json.loads(match[1])

    pad_hashes = {}

    def format_pads(pads: dict) -> dict[int, str]:
        ret = {}
        for pad in pads:
            pad_hashes[pad["id"]] = pad["token"]
            ret[pad["id"]] = pad["titre"]
        return ret

    pads = PadsList(
        created=format_pads(data["pageProps"]["padsCrees"]),
        visited=format_pads(data["pageProps"]["padsRejoints"]),
        admin=format_pads(data["pageProps"]["padsAdmins"]),
        favourite=format_pads(data["pageProps"]["padsFavoris"]),
        pad_hashes=pad_hashes,
    )
    for pad_id, pad_title in {
        **pads.created,
        **pads.visited,
        **pads.admin,
        **pads.favourite,
    }.items():
        if pad_id not in pads.all:
            pads.all[pad_id] = pad_title

    for folder in data["pageProps"]["dossiers"]:
        pads.folder_names[folder["id"]] = folder["nom"]
        pads.folders[folder["id"]] = {
            pad_id: pad_title
            for pad_id, pad_title in pads.all.items()
            if pad_id in folder["pads"]
        }

    return pads
