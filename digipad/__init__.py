import argparse
from getpass import getpass
import json
from urllib.parse import unquote
import requests

from tabulate import tabulate

from .session import Session

from .utils import COOKIE_FILE, get_userinfo

__version__ = "2024.2.22"


def create_block_cmd(args):
    """Handler for digipad create-block."""
    pads = Session(args).pads.get_all(args.LIST)
    for pad in pads:
        print(f"Creating block on {pad}...")
        block_id = pad.create_block(args.title, args.text, args.hidden, args.column_n)
        if args.comment:
            pad.comment_block(block_id, args.title, args.comment)


def rename_column_cmd(args):
    """Handler for digipad rename-column."""
    pads = Session(args).pads.get_all(args.LIST)
    for pad in pads:
        print(f"Renaming column on {pad}...")
        pad.rename_column(args.column_n, args.title)


def export_pads_cmd(args):
    """Handler for digipad export."""
    pads = Session(args).pads.get_all(args.LIST)
    if not pads:
        print("No pad to export")
        return

    for pad in pads:
        pad.export(args.output)
        print(f"Exported pad {pad}")


def list_pads_cmd(args):
    """Handler for digipad list."""
    pads = Session(args).pads.get_all(args.LIST)

    verbose_names = {
        "id": "Pad ID",
        "hash": "Pad hash",
        "name": "Pad name",
        "code": "PIN code",
    }

    data = []
    for pad in pads:
        data.append({
            "id": pad.id,
            "hash": pad.hash,
        })

    if args.format == "json":
        print(json.dumps(data))
    else:
        if not pads:
            print("No pad")
            return

        def fix_dict(item: dict):
            """Replace the keys by the verbose names in the specified `item`."""
            ret = {}
            for key, value in item.items():
                ret[verbose_names.get(key, key)] = value
            return ret

        print(tabulate([fix_dict(item) for item in data], headers="keys"))
        print()
        print(f"{len(pads)} {'pads' if len(pads) >= 2 else 'pad'}")


def login_cmd(args):
    """Handler for digipad login."""
    username = args.USERNAME or input("Username: ")
    password = args.PASSWORD or getpass("Password: ")

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

    userinfo = get_userinfo(cookie)
    if not userinfo:
        raise ValueError("Not logged in, double-check your username and password")

    print(f"Logged in as {userinfo}")
    COOKIE_FILE.write_text(cookie, encoding="utf-8")
    print(f"Cookie saved to {COOKIE_FILE}")


def set_cookie_cmd(args):
    """Handler for digipad set-cookie."""
    cookie = unquote(args.COOKIE)

    userinfo = get_userinfo(cookie)
    if not userinfo:
        raise ValueError("Not logged in")

    print(f"Logged in as {userinfo}")
    COOKIE_FILE.write_text(cookie, encoding="utf-8")
    print(f"Cookie saved to {COOKIE_FILE}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cookie", help="Digipad cookie")
    subparsers = parser.add_subparsers(required=True)

    parser_create_block = subparsers.add_parser("create-block", help="Create a block in a pad")
    parser_create_block.add_argument("LIST", nargs="*", default=("created",), help="pads to edit")
    parser_create_block.add_argument("--title", default="", help="title of the block")
    parser_create_block.add_argument("--text", default="", help="text of the block", required=True)
    parser_create_block.add_argument("--column-n", default=0, help="column number (starting from 0)")
    parser_create_block.add_argument("--hidden", action="store_true", help="if specified, hide the block")
    parser_create_block.add_argument("--comment", help="comment to add to the block")
    parser_create_block.set_defaults(func=create_block_cmd)

    parser_rename_column = subparsers.add_parser("rename-column", help="Rename a column in a pad")
    parser_rename_column.add_argument("LIST", nargs="*", default=("created",), help="pads to edit")
    parser_rename_column.add_argument("--title", default="", help="title of the column")
    parser_rename_column.add_argument("--column-n", help="column number (starting from 0)")
    parser_rename_column.set_defaults(func=rename_column_cmd)

    parser_export = subparsers.add_parser("export", help="Export pads")
    parser_export.add_argument("LIST", nargs="*", default=("created",), help="pad list to export")
    parser_export.add_argument("-o", "--output", help="output directory")
    parser_export.set_defaults(func=export_pads_cmd)

    parser_list = subparsers.add_parser("list", help="List pads")
    parser_list.add_argument("LIST", nargs="*", default=("created",), help="pad list to export")
    parser_list.add_argument("-f", "--format", choices=["table", "json"], default="table", help="output format")
    parser_list.add_argument("-v", "--verbose", action="store_true", help="print more information about pads")
    parser_list.set_defaults(func=list_pads_cmd)

    parser_login = subparsers.add_parser("login", help="Log into Digipad and save the cookie")
    parser_login.add_argument("USERNAME", nargs="?", help="Digipad username")
    parser_login.add_argument("PASSWORD", nargs="?", help="Digipad password")
    parser_login.set_defaults(func=login_cmd)

    parser_set_cookie = subparsers.add_parser("set-cookie", help="Save the Digipad cookie for later use")
    parser_set_cookie.add_argument("COOKIE", help="Digipad cookie")
    parser_set_cookie.set_defaults(func=set_cookie_cmd)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
