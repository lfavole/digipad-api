import argparse

from .edit import comment_block, create_block
from .export import export_pad
from .get_pads import get_all_pads, get_userinfo
from .utils import get_cookie, COOKIE_FILE

__version__ = "2024.2.22"


def create_block_cmd(args):
    cookie = get_cookie(args, False)
    all_pads = get_all_pads(cookie)
    pads = all_pads.get_pads(args.LIST)
    for pad_id in pads:
        pad_hash = all_pads.pad_hashes[pad_id]
        block_id = create_block(pad_id, pad_hash, args.title, args.text, column_n=args.column_n, digipad_cookie=cookie)
        if args.comment:
            comment_block(pad_id, pad_hash, block_id, args.title, args.comment, digipad_cookie=cookie)


def export_pads_cmd(args):
    cookie = get_cookie(args)
    pads = get_all_pads(cookie).get_pads(args.LIST)
    if not pads:
        print("No pad to export")
        return

    for pad_id, pad_title in pads.items():
        export_pad(pad_id, args.cookie, args.output)
        print(f"Exported pad #{pad_id} ({pad_title})")


def list_pads_cmd(args):
    cookie = get_cookie(args)
    pads = get_all_pads(cookie).get_pads(args.LIST)
    if not pads:
        print("No pad")
        return

    print("Pad ID|Pad name")
    print("===============")
    for pad_id, pad_name in pads.items():
        print(pad_id, pad_name)
    print()
    print(f"{len(pads)} {'pads' if len(pads) >= 2 else 'pad'}")


def set_cookie_cmd(args):
    cookie = args.COOKIE
    if not get_userinfo(cookie).username:
        raise ValueError("Not logged in")
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
    parser_create_block.add_argument("--comment", help="comment to add to the block")
    parser_create_block.set_defaults(func=create_block_cmd)

    parser_export = subparsers.add_parser("export", help="Export pads")
    parser_export.add_argument("LIST", nargs="*", default=("created",), help="pad list to export")
    parser_export.add_argument("-o", "--output", help="output directory")
    parser_export.set_defaults(func=export_pads_cmd)

    parser_list = subparsers.add_parser("list", help="List pads")
    parser_list.add_argument("LIST", nargs="*", default=("created",), help="pad list to export")
    parser_list.set_defaults(func=list_pads_cmd)

    parser_export = subparsers.add_parser("set-cookie", help="Save the Digipd cookie for later use")
    parser_export.add_argument("COOKIE", help="Digipad cookie")
    parser_export.set_defaults(func=set_cookie_cmd)

    args = parser.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()
