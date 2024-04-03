from urllib.parse import unquote

import requests
from flask.sessions import SessionMixin

from .edit import PadList, format_pads
from .utils import UserInfo, extract_data, get_cookie_from_args

DEFAULT_INSTANCE = "https://digipad.app"


class Session:
    """
    A session (logged-in or anonymous account) on the Digipad website.
    """

    def __init__(self, cookie=None, domain=DEFAULT_INSTANCE):
        from . import Options

        if isinstance(cookie, Options):
            opts = cookie
            cookie = get_cookie_from_args(opts, False)
            domain = getattr(opts, "domain", domain)
        elif isinstance(cookie, SessionMixin):
            opts = cookie
            cookie = opts.get("digipad_cookie")
            domain = opts.get("digipad_instance") or domain

        self.domain = domain
        if cookie:
            self.userinfo = self.get_userinfo(cookie)
        else:
            self.userinfo = UserInfo(logged_in=False)

    def login(self, username, password):
        """Log into Digipad and return the corresponding userinfo."""
        req = requests.post(
            f"{self.domain}/api/connexion",
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

        self.userinfo = self.get_userinfo(cookie)

    def get_userinfo(self, digipad_cookie):
        """
        Return user information from a Digipad cookie.
        """
        try:
            req = requests.get(
                self.domain,
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

    def get_anon_userinfo(self, pad_id, pad_hash):
        """
        Return anonymous user information from a pad ID and a hash.
        """
        try:
            req = requests.get(f"{self.domain}/p/{pad_id}/{pad_hash}")
        except OSError:
            return UserInfo(connection_error=True)

        cookie = unquote(req.cookies["digipad"])
        data = extract_data(req)

        return UserInfo.from_json(data, cookie)

    @property
    def cookie(self):
        """
        The Digipad cookie that is used to make requests.
        """
        return self.userinfo.cookie

    @cookie.setter
    def cookie(self, cookie):
        self.userinfo = self.get_userinfo(cookie)

    @property
    def pads(self):
        """
        All the pads on the account. If the account is an anonymous account, there will be no pads.
        """
        from .get_pads import PadsOnAccount

        if not self.cookie:
            return PadsOnAccount()

        req = requests.get(
            f"{self.domain}/u/" + self.userinfo.username,
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
