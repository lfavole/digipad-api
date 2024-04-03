import os
from pathlib import Path

from PyInstaller.__main__ import run

BASE_PATH = Path(__file__).parent


def add_data(path: Path):
    """Returns the arguments needed to add a data file to the executable."""
    relpath = path.relative_to(BASE_PATH)
    return "--add-data", str(path) + os.pathsep + str(relpath.parent if relpath.is_file() else relpath)


exclusions = [
    "cryptography",  # imported by werkzeug.serving
    "statistics",  # imported by random
    "tornado",  # imported by engineio.async_drivers.tornado
    "watchdog",  # imported by werkzeug._reloader
]
exclusions_args = []
for excl in exclusions:
    exclusions_args.append("--exclude-module")
    exclusions_args.append(excl)

run(
    [
        "--onefile",
        "--name",
        "digipad",
        *add_data(BASE_PATH / "digipad/app/template.html"),
        *add_data(BASE_PATH / "digipad/app/static"),
        *exclusions_args,
        str(BASE_PATH / "digipad/__main__.py"),
    ]
)
