import datetime as dt
import json

import requests
from flask.sessions import SessionMixin

from .edit import Pad, PadConnection, PadList
from .utils import UserInfo, extract_data, get_cookie_from_args, get_userinfo


class Session:
    """
    A session (logged-in or anonymous account) on the Digipad website.
    """
    def __init__(self, cookie=None):
        from .__init__ import Options
        if isinstance(cookie, Options):
            cookie = get_cookie_from_args(cookie, False)
        elif isinstance(cookie, SessionMixin):
            cookie = cookie.get("digipad_cookie")

        if cookie:
            self.userinfo = get_userinfo(cookie)
        else:
            self.userinfo = None

    @property
    def cookie(self):
        """
        The Digipad cookie that is used to make requests.
        """
        if self.userinfo is None:
            raise ValueError("Not logged in into a pad")
        return self.userinfo.cookie

    @cookie.setter
    def cookie(self, cookie):
        self.userinfo = get_userinfo(cookie)

    @property
    def pads(self):
        """
        All the pads on the account. If the account is an anonymous account, there will be no pads.
        """
        from .get_pads import PadsOnAccount
        if not self.cookie:
            return PadsOnAccount()

        req = requests.get(
            "https://digipad.app/u/" + get_userinfo(self.cookie).username,
            allow_redirects=False,
            cookies={"digipad": self.cookie},
        )
        if 300 <= req.status_code < 400:
            # redirected to home page = not logged in
            return PadsOnAccount()
        req.raise_for_status()

        data = extract_data(req)

        pad_hashes = {}

        def format_pads(pads: dict) -> PadList:
            """
            Returns a dict that maps pad IDs to pad titles from a Digipad dict.
            """
            ret = PadList()
            for pad in pads:
                pad_hashes[pad["id"]] = pad["token"]
                pad = Pad(
                    id=pad["id"],
                    hash=pad["token"],
                    title=pad["titre"],
                    code=pad.get("code"),
                    access=pad["acces"],
                    columns=json.loads(pad["colonnes"]),
                    creator=UserInfo.from_json(pad),
                    creation_date=dt.datetime.fromisoformat(pad["date"]),
                )
                pad.connection = PadConnection(pad, self)
                ret.append(pad)
            return ret

        pads = PadsOnAccount(
            session=self,
            created=format_pads(data["pageProps"]["padsCrees"]),
            visited=format_pads(data["pageProps"]["padsRejoints"]),
            admin=format_pads(data["pageProps"]["padsAdmins"]),
            favourite=format_pads(data["pageProps"]["padsFavoris"]),
            pad_hashes=pad_hashes,
        )

        for folder in data["pageProps"]["dossiers"]:
            pads.folder_names[folder["id"]] = folder["nom"]
            pads.folders[folder["id"]] = PadList([
                pad
                for pad in pads.all
                if pad.id in folder["pads"]
            ])

        return pads
