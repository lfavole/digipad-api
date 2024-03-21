import datetime as dt
import json
import random
import time
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import quote

import requests
import socketio

from .utils import UserInfo, get_anon_userinfo


class PadConnection:
    """
    A connection on a pad that can run commands.
    """

    def __init__(self, pad: "Pad", session=None):
        from .session import Session  # avoid circular import

        self.pad = pad
        self.session = session or Session()
        self.socket = None

    @property
    def userinfo(self) -> UserInfo:
        """
        The user information of this connection.
        """
        return self.session.userinfo  # type: ignore

    def connect(self):
        """
        Connect to the pad.
        """
        if self.socket:
            return self.socket

        if not self.session.userinfo:
            self.session.userinfo = get_anon_userinfo(self.pad.id, self.pad.hash)

        socket = socketio.SimpleClient()
        socket.connect(
            "https://digipad.app",
            headers={"Cookie": "digipad=" + quote(self.session.cookie)},
        )

        socket.emit(
            "connexion",
            {
                "pad": self.pad.id,
                "identifiant": self.session.userinfo.username,
                "nom": self.session.userinfo.name,
            },
        )
        data = socket.receive()
        if data[0] != "connexion":
            raise ValueError(f"Can't log in to pad {self.pad}")
        self.socket = socket
        return socket

    def close(self):
        """
        Disconnect from the pad and remove the socket.
        """
        if self.socket:
            self.socket.disconnect()
            self.socket = None

    def run(self, command, *args):
        """
        Run a command on the pad.
        """
        socket = self.connect()
        socket.emit(command, args)
        ret = socket.receive()
        if ret[0] != command:
            raise ValueError(f"Can't run command {command} on pad {self.pad} ({ret})")
        return ret[1]


@dataclass
class Pad:
    """
    A pad.
    """

    id: int
    hash: str = ""
    title: str = ""
    code: "int | None" = None
    access: str = "public"
    columns: list[str] = field(default_factory=list)
    creator: UserInfo = field(default_factory=UserInfo)
    creation_date: "dt.datetime | None" = None
    _connection: "PadConnection | None" = None

    def __hash__(self):
        return hash(self.id)

    def __str__(self):
        return f"#{self.id}"

    @property
    def connection(self):
        """
        The connection associated to the pad. One is automatically created when needed.
        """
        if self._connection is None:
            self._connection = PadConnection(self)
        return self._connection

    @connection.setter
    def connection(self, connection):
        self._connection = connection

    def export(self, directory=None):
        """
        Export a pad and return the path of the exported ZIP file.
        """
        if not self.connection.userinfo:
            raise ValueError("Not logged in")
        req = requests.post(
            "https://digipad.app/api/exporter-pad",
            json={"padId": self.id, "identifiant": self.connection.userinfo.username, "admin": ""},
            cookies={"digipad": self.connection.userinfo.cookie},
        )
        req.raise_for_status()
        if req.text == "non_connecte":
            raise ValueError("Not logged in")

        filename = req.text
        file = "https://digipad.app/temp/" + filename
        req2 = requests.get(file, stream=True)
        req2.raise_for_status()
        if req2.content == b"non_connecte":
            raise ValueError("Not logged in")

        output_file = (directory or Path.cwd()) / filename
        with output_file.open("wb") as f:
            for chunk in req2.iter_content(65536):
                f.write(chunk)

        with zipfile.ZipFile(output_file) as archive:
            data = json.loads(archive.read("donnees.json"))
        output_file.rename(
            output_file.parent / f"{data['pad']['titre']}_{self.id}_{dt.datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
        )
        return output_file

    def edit_block(self, title, text, hidden=False, column_n=0, block_id=None):
        """
        Edit a block and return its ID.
        """
        command = "modifierbloc"
        if not block_id:
            block_id = f"bloc-id-{int(time.time() * 1000)}{random.randbytes(3).hex()[1:]}"
            command = "ajouterbloc"

        ret = self.connection.run(
            command,
            block_id,
            str(self.id),
            self.hash,
            title,
            text,
            "",  # media
            "",  # iframe
            "",  # type
            "",  # source
            "",  # thumbnail
            self.connection.userinfo.color,
            column_n,
            hidden,
            self.connection.userinfo.username,
            self.connection.userinfo.name,
        )
        return ret["bloc"]

    def create_block(self, title, text, hidden=False, column_n=0):
        """
        Create a block and return its ID.
        """
        return self.edit_block(title, text, hidden, column_n, None)

    def comment_block(self, block_id, title, text):
        """
        Add a comment on a block.
        """
        self.connection.run(
            "commenterbloc",
            block_id,
            str(self.id),
            title,
            text,
            self.connection.userinfo.color,
            self.connection.userinfo.username,
            self.connection.userinfo.name,
        )

    def rename_column(self, column_number, column_title):
        """
        Rename a column.
        """
        self.connection.run(
            "modifiertitrecolonne",
            str(self.id),
            column_title,
            column_number,
            self.connection.userinfo.username,
        )


class PadList(list[Pad]):
    """A list of pads that can be searched for a specific pad."""

    def get(self, pad_id, session=None):
        """Search for a pad in the list and return it, otherwise create a `Pad` object without metadata."""
        pad_hash = ""
        if not isinstance(pad_id, int):
            try:
                pad_id = int(pad_id)
            except ValueError:
                url = pad_id
                try:
                    *_, pad_id, pad_hash = str(pad_id).rstrip("/").split("/")
                    if pad_id == "p":
                        # incomplete URL without hash
                        pad_id = pad_hash
                        pad_hash = ""
                    pad_id = int(pad_id)
                except ValueError as err:
                    raise ValueError(f"Could not extract pad ID from the URL {url}") from err

        for pad in self:
            if pad.id == pad_id:
                return pad

        pad = Pad(pad_id, pad_hash)
        if session:
            pad.connection = PadConnection(pad, session)
        return pad
