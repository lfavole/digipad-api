from argparse import Namespace
import requests

from .edit import PadConnection, PadList
from .get_pads import Pad, PadsOnAccount
from .utils import extract_data, get_cookie_from_args, get_userinfo


class Session:
    """
    A session (logged-in account) on the Digipad website.
    """
    def __init__(self, cookie=None):
        if cookie:
            if isinstance(cookie, Namespace):
                cookie = get_cookie_from_args(cookie, False)
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

        def format_pads(pads: dict) -> list[Pad]:
            """
            Returns a dict that maps pad IDs to pad titles from a Digipad dict.
            """
            ret = PadList()
            for pad in pads:
                pad_hashes[pad["id"]] = pad["token"]
                pad = Pad(pad["id"], pad["token"])
                pad.connection = PadConnection(pad, self)
                ret.append(pad)
            return ret

        pads = PadsOnAccount(
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
