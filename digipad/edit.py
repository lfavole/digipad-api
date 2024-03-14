import functools
import random
import time
from urllib.parse import quote

import socketio

from .utils import UserInfo, get_anon_cookie, get_userinfo


@functools.lru_cache
def connect(pad_id, pad_hash=None, digipad_cookie=None):
    digipad_cookie = digipad_cookie or get_anon_cookie(pad_id, pad_hash)
    userinfo = get_userinfo(digipad_cookie, pad_id, pad_hash)

    sio = socketio.SimpleClient()
    sio.connect(
        "https://digipad.app",
        transports=["polling"],
        headers={"Cookie": "digipad=" + quote(digipad_cookie)},
    )

    sio.emit(
        "connexion",
        {
            "pad": pad_id,
            "identifiant": userinfo.username,
            "nom": userinfo.name,
        },
    )
    data = sio.receive()
    if data[0] != "connexion":
        raise ValueError("Can't log in")
    user = data[1][0]
    return sio, UserInfo(user["identifiant"], user["nom"], user["couleur"])


def run_command(pad_id, pad_hash, digipad_cookie, command, *args):
    sio, user_info = connect(pad_id, pad_hash, digipad_cookie)
    sio.emit(
        command,
        args,
    )
    ret = sio.receive()
    sio.disconnect()
    if ret[0] != command:
        raise ValueError(f"Can't add block ({ret})")
    return ret[1]


def create_block(pad_id, pad_hash, title, text, hidden=False, column_n=0, block_id=None, digipad_cookie=None):
    digipad_cookie = digipad_cookie or get_anon_cookie(pad_id, pad_hash)
    sio, user_info = connect(pad_id, pad_hash, digipad_cookie)
    command = "modifierbloc"
    if not block_id:
        block_id = f"bloc-id-{int(time.time() * 1000)}{random.randbytes(3).hex()[1:]}"
        command = "ajouterbloc"
    sio.emit(
        command,
        (
            block_id,
            str(pad_id),
            pad_hash,
            title,
            text,
            "",  # media
            "",  # iframe
            "",  # type
            "",  # source
            "",  # thumbnail
            "#495057",
            column_n,
            hidden,
            user_info.username,
            user_info.name,
        ),
    )
    ret = sio.receive()[0]
    sio.disconnect()
    if ret != "ajouterbloc":
        raise ValueError(f"Can't add block ({ret})")
    return block_id


def comment_block(pad_id, pad_hash, block_id, title, text, hidden=False, column_n=0, digipad_cookie=None):
    sio, user_info = connect(pad_id, pad_hash, digipad_cookie)
    sio.emit(
        "commenterbloc",
        (
            block_id,
            str(pad_id),
            title,
            text,
            user_info.color,
            user_info.username,
            user_info.name,
        ),
    )
    ret = sio.receive()[0]
    sio.disconnect()
    if ret != "commenterbloc":
        raise ValueError(f"Can't comment block ({ret})")


def rename_column(pad_id, pad_hash, column_number, column_title, digipad_cookie=None):
    sio, user_info = connect(pad_id, pad_hash, digipad_cookie)
    sio.emit(
        "modifiertitrecolonne",
        (
            str(pad_id),
            column_title,
            column_number,
            user_info.username,
        ),
    )
    ret = sio.receive()[0]
    sio.disconnect()
    if ret != "modifiertitrecolonne":
        raise ValueError(f"Can't rename column ({ret})")
