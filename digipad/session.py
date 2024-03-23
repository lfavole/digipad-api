import requests
from flask.sessions import SessionMixin

from .edit import PadList, format_pads
from .utils import extract_data, get_cookie_from_args, get_userinfo


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

        pads = PadsOnAccount(
            session=self,
            created=format_pads(data["pageProps"]["padsCrees"], pad_hashes, self),
            visited=format_pads(data["pageProps"]["padsRejoints"], pad_hashes, self),
            admin=format_pads(data["pageProps"]["padsAdmins"], pad_hashes, self),
            favourite=format_pads(data["pageProps"]["padsFavoris"], pad_hashes, self),
            pad_hashes=pad_hashes,
        )

        for folder in data["pageProps"]["dossiers"]:
            pads.folder_names[folder["id"]] = folder["nom"]
            pads.folders[folder["id"]] = PadList([pad for pad in pads.all if pad.id in folder["pads"]])

        return pads
