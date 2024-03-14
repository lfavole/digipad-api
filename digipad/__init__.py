import json
from dataclasses import dataclass
from urllib.parse import unquote

import click
import requests
from tabulate import tabulate

from .progress import Progress
from .session import Session
from .utils import COOKIE_FILE, get_userinfo

__version__ = "2024.2.22"


@dataclass
class Options:
    """Global command line options."""
    delay: int
    cookie: str


pass_opts = click.make_pass_decorator(Options)

pad_argument = click.argument("PADS", nargs=-1, required=True)


@click.group()
@click.version_option(__version__)
@click.option("--delay", type=int, default=0, help="delay between operations")
@click.option("--cookie", help="Digipad cookie")
@click.pass_context
def cli(ctx, delay, cookie):
    """Main command that handles the default parameters."""
    ctx.obj = Options(delay, cookie)


@cli.command()
@pad_argument
@click.option("--title", default="", help="title of the block")
@click.option("--text", default="", help="text of the block", required=True)
@click.option("--column-n", default=0, help="column number (starting from 0)")
@click.option("--hidden", is_flag=True, help="if specified, hide the block")
@click.option("--comment", help="comment to add to the block")
@pass_opts
def create_block(opts, pads, title, text, column_n, hidden, comment):
    """Create a block in a pad."""
    pads = Session(opts).pads.get_all(pads)
    for pad in pads:
        with Progress(f"Creating block on {pad}") as prog:
            block_id = pad.create_block(title, text, hidden, column_n)
            prog.end()
            if comment:
                prog.start("Commenting")
                pad.comment_block(block_id, title, comment)


@cli.command()
@pad_argument
@click.option("--title", required=True, help="title of the column")
@click.option("--column-n", required=True, help="column number (starting from 0)")
@pass_opts
def rename_column(opts, pads, title, column_n):
    """Rename a column in a pad."""
    pads = Session(opts).pads.get_all(pads)
    for pad in pads:
        with Progress(f"Renaming column on {pad}"):
            pad.rename_column(column_n, title)


@cli.command()
@pad_argument
@click.option("-o", "--output", help="output directory")
@pass_opts
def export(opts, pads, output):
    """Export pads."""
    pads = Session(opts).pads.get_all(pads)
    if not pads:
        print("No pad to export")
        return

    for pad in pads:
        with Progress(f"Exporting pad {pad}"):
            pad.export(output)


@cli.command()
@pad_argument
@click.option("-f", "--format", type=click.Choice(["table", "json"]), default="table", help="output format")
@click.option("-v", "--verbose", is_flag=True, help="print more information about pads")
@pass_opts
def list(opts, pads, format, verbose):
    """List pads."""
    pads = Session(opts).pads.get_all(pads)

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
        if verbose:
            data.append({
                "id": pad.id,
                "hash": pad.hash,
                "title": pad.title,
                "access": pad.access,
                "code": pad.code,
                "columns": pad.columns,
            })
        else:
            data.append({
                "id": pad.id,
                "title": pad.title,
            })

    if format == "json":
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


@cli.command()
@click.option("--username", prompt="Username")
@click.option("--password", prompt="Password", hide_input=True)
@click.option("--print-cookie", is_flag=True, help="print the cookie and don't save it")
def login(username, password, print_cookie):
    """Log into Digipad and save the cookie."""
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
    if print_cookie:
        print(f"Cookie: {cookie}")
        return

    COOKIE_FILE.write_text(cookie, encoding="utf-8")
    print(f"Cookie saved to {COOKIE_FILE}")


@cli.command()
@click.argument("COOKIE", required=False)
@pass_opts
def userinfo(opts, cookie):
    """Print information about the current logged-in user or a specified cookie."""
    userinfo = Session(cookie or opts).userinfo
    print(f"Logged in as {userinfo}")
    if not userinfo:
        print("Anonymous session")


@cli.command(help="Save the Digipad cookie for later use")
@click.argument("COOKIE")
def set_cookie(cookie):
    """Save the Digipad cookie for later use."""
    cookie = unquote(cookie)

    userinfo = get_userinfo(cookie)
    if not userinfo:
        raise ValueError("Not logged in")

    print(f"Logged in as {userinfo}")
    COOKIE_FILE.write_text(cookie, encoding="utf-8")
    print(f"Cookie saved to {COOKIE_FILE}")


@cli.command(help="Delete the Digipad cookie file and log out")
def logout():
    """Handler for digipad logout."""
    COOKIE_FILE.unlink(True)
    print("Logged out")


def main():
    cli.main()


if __name__ == "__main__":
    main()
