import json
from dataclasses import dataclass
import os
from pathlib import Path
import random
from urllib.parse import unquote
import webbrowser

import click
from tabulate import tabulate

from .progress import Progress
from .session import Session
from .utils import COOKIE_FILE, get_pads_table, get_userinfo, login as digipad_login

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
    data = get_pads_table(pads, verbose, format == "json")

    if format == "json":
        print(json.dumps(data))
    else:
        if not pads:
            print("No pad")
            return

        print(tabulate(data, headers="keys"))
        print()
        print(f"{len(pads)} {'pads' if len(pads) >= 2 else 'pad'}")


@cli.command()
@click.option("--username", prompt="Username")
@click.option("--password", prompt="Password", hide_input=True)
@click.option("--print-cookie", is_flag=True, help="print the cookie and don't save it")
def login(username, password, print_cookie):
    """Log into Digipad and save the cookie."""
    userinfo = digipad_login(username, password)
    if not userinfo:
        raise ValueError("Not logged in, double-check your username and password")

    print(f"Logged in as {userinfo}")
    if print_cookie:
        print(f"Cookie: {userinfo.cookie}")
        return

    COOKIE_FILE.write_text(userinfo.cookie, encoding="utf-8")
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


@cli.command()
@click.option("--open/--no-open", default=True, help="automatically open the browser")
@click.option(
    "-s",
    "--secret-key",
    default=Path.home() / ".digipad_secret_key",
    type=click.Path(exists=False, dir_okay=False),
    help="secret key or path to a file that contains it",
)
@click.option("-h", "--host", default="0.0.0.0", help="hostname where the app is run")
@click.option("-p", "--port", type=int, default=5000, help="port on which the app is run")
@click.option("--debug/--no-debug", default=False, help="run the app in debugging mode")
def web(open, secret_key, host, port, debug):
    """Open the web interface."""
    if Path(secret_key).exists():
        secret_key = Path(secret_key).read_text()
    elif isinstance(secret_key, Path):
        # default value
        secret_key_file = secret_key
        secret_key = random.randbytes(64).hex()
        Path(secret_key_file).write_text(secret_key)

    if open and not os.getenv("WERKZEUG_RUN_MAIN"):
        webbrowser.open(f"http://{'127.0.0.1' if host == '0.0.0.0' else host}:{port}")

    from .app import app
    app.secret_key = secret_key
    app.run(host, port, debug)


def main():
    cli.main()


if __name__ == "__main__":
    main()
