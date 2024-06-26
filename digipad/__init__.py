import json
import os
import time
import webbrowser
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote

import click
from tabulate import tabulate

from .progress import Progress
from .session import Session
from .utils import COOKIE_FILE, get_pads_table, get_secret_key

__version__ = "2024.2.22"


@dataclass
class Options:
    """Global command line options."""

    delay: int
    cookie: str
    domain: str


pass_opts = click.make_pass_decorator(Options)

pad_argument = click.argument("PADS", nargs=-1, required=True)
delay_option = click.option("--delay", type=int, default=1)


@click.group()
@click.version_option(__version__)
@click.option("--delay", type=int, default=0, help="delay between operations")
@click.option("--cookie", help="Digipad cookie")
@click.option("--domain", "--instance", help="domain of Digipad instance")
@click.pass_context
def cli(ctx, delay, cookie, domain):
    """Main command that handles the default parameters."""
    ctx.obj = Options(delay, cookie, domain)


@cli.command()
@click.argument("TITLES", nargs=-1, required=True)
@click.option("--template", help="pad to use as a template")
@delay_option
@pass_opts
def create_pad(opts, titles, template, delay):
    """Create a pad."""
    pads = Session(opts).pads
    for pad_title in titles:
        with Progress(f"Creating pad {pad_title}") as prog:
            pads.create_pad(pad_title, template)
            prog.end()
            time.sleep(delay)


@cli.command()
@pad_argument
@delay_option
@click.option("--title", default="", help="title of the block")
@click.option("--text", default="", help="text of the block", required=True)
@click.option("--column-n", default=0, help="column number (starting from 0)")
@click.option("--hidden", is_flag=True, help="if specified, hide the block")
@click.option("--comment", help="comment to add to the block")
@pass_opts
def create_block(opts, pads, delay, title, text, column_n, hidden, comment):
    """Create a block in a pad."""
    pads = Session(opts).pads.get_all(pads)
    for pad in pads:
        with Progress(f"Creating block on {pad}") as prog:
            block_id = pad.create_block(title, text, hidden, column_n)
            prog.end()
            if comment:
                time.sleep(delay)
                prog.start("Commenting")
                pad.comment_block(block_id, title, comment)
            pad.connection.close()
            time.sleep(delay)


@cli.command()
@pad_argument
@delay_option
@click.option("--title", required=True, help="title of the column")
@click.option("--column-n", type=int, required=True, help="column number (starting from 0)")
@pass_opts
def rename_column(opts, pads, delay, title, column_n):
    """Rename a column in a pad."""
    pads = Session(opts).pads.get_all(pads)
    for pad in pads:
        with Progress(f"Renaming column on {pad}"):
            pad.rename_column(column_n, title)
        pad.connection.close()
        time.sleep(delay)


@cli.command()
@pad_argument
@delay_option
@click.option("-o", "--output", help="output directory")
@pass_opts
def export(opts, pads, delay, output):
    """Export pads."""
    pads = Session(opts).pads.get_all(pads)
    if not pads:
        print("No pad to export")
        return

    for pad in pads:
        with Progress(f"Exporting pad {pad}"):
            pad.export(output)
        time.sleep(delay)


@cli.command()
@pad_argument
@click.option("-f", "--format", type=click.Choice(["table", "json"]), default="table", help="output format")
@click.option("-v", "--verbose", is_flag=True, help="print more information about pads")
@pass_opts
def list(opts, pads, format, verbose):  # pylint: disable=W0622
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
@pass_opts
def login(opts, username, password, print_cookie):
    """Log into Digipad and save the cookie."""
    session = Session(opts)
    session.login(username, password)
    userinfo = session.userinfo  # pylint: disable=W0621
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
    session = Session(opts)
    if cookie:
        session.cookie = cookie
    userinfo = session.userinfo  # pylint: disable=W0621
    print(f"Logged in as {userinfo}")
    if not userinfo:
        print("Anonymous session")


@cli.command(help="Save the Digipad cookie for later use")
@click.option("--cookie", prompt="Digipad cookie", hide_input=True)
@pass_opts
def set_cookie(opts, cookie):
    """Save the Digipad cookie for later use."""
    cookie = unquote(cookie)

    session = Session(opts)
    session.cookie = cookie
    userinfo = session.userinfo  # pylint: disable=W0621
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
def web(open, secret_key, host, port, debug):  # pylint: disable=W0622
    """Open the web interface."""
    secret_key = get_secret_key(secret_key)

    if open and not os.getenv("WERKZEUG_RUN_MAIN"):
        webbrowser.open(f"http://{'127.0.0.1' if host == '0.0.0.0' else host}:{port}")

    from .app import app

    app.secret_key = secret_key
    app.run(host, port, debug)


def main():
    cli.main()


if __name__ == "__main__":
    main()
