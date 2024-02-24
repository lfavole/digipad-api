import datetime as dt
import json
import re
import zipfile
from pathlib import Path

import requests


def export_pad(url_or_id, digipad_cookie, directory=None):
    if isinstance(url_or_id, int):
        pad_id = url_or_id
    else:
        match = re.search(r"^https?://digipad\.app/p/(\d+)/", url_or_id)
        if not match:
            raise ValueError("Can't get pad ID")
        pad_id = int(match[1])

    req = requests.post(
        "https://digipad.app/api/exporter-pad",
        json={"padId": pad_id, "identifiant": "lfavole", "admin": ""},
        cookies={"digipad": digipad_cookie},
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
    output_file.rename(output_file.parent / f"{data['pad']['titre']}_{pad_id}_{dt.datetime.now().strftime('%Y%m%d_%H%M%S')}.zip")


def zip_to_html(data_or_filename):
    if isinstance(data_or_filename, str):
        with zipfile.ZipFile(data_or_filename) as archive:
            data_or_filename = json.loads(archive.read("donnees.json"))

    html = ""

    html += "<title>" + data["pad"]["titre"] + "</title>"
    html += """\
    <style>
    body {
        overflow-x: auto;
        background: palegreen;
    }
    .colonne {
        display: inline-block;
        vertical-align: top;
        margin: 8px;
    }
    .colonne > .titre {
        padding: 8px;
        background: white;
        border-radius: 8px;
    }
    .colonne .capsule {
        border-radius: 8px;
        border: 2px solid black;
    }
    .colonne .capsule > :first-child {
        border-radius: 8px 8px 0px 0px;
    }
    .colonne .capsule > :last-child {
        border-radius: 0px 0px 8px 8px;
    }
    .colonne .capsule .titre {
        padding: 8px;
        background: pink;
    }
    .colonne .capsule .contenu {
        padding: 8px;
        background: white;
    }
    .colonne .capsule .commentaire {
        border-top: 2px solid black;
    }
    </style>
    """

    columns = json.loads(data["pad"]["colonnes"])
    columns_display = json.loads(data["pad"]["affichageColonnes"])

    for i, column in enumerate(columns):
        html += '<div class="colonne">'
        html += '<div class="titre">' + column + (" (cachée)" if not columns_display[i] else "") + "</div>"
        for block in data["blocs"]:
            if int(block["colonne"]) != i:
                continue
            html += '<div class="capsule">'
            html += '<div class="titre">' + block["titre"] + "</div>"
            html += '<div class="contenu">' + block["texte"] + "</div>"
            for comment in block["listeCommentaires"]:
                html += '<div class="commentaire">'
                html += comment["texte"]
                html += "</div>"
            html += "</div>"
        html += "</div>"

    return html
