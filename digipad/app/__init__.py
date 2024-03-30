import datetime as dt
import json
import random
import sys
from html import escape
from pathlib import Path
from urllib.parse import urlparse
import zipfile

from flask import Flask, Response, redirect, request, session, url_for
from tabulate import tabulate

from ..session import DEFAULT_INSTANCE, Session
from ..utils import get_pads_table

app = Flask(__name__)

EXPORT_DIRECTORY = Path(__file__).parent / "static/export"
TEMPLATE = (Path(__file__).parent / "template.html").read_text("utf-8")


class JSONResponse(Response):
    def __init__(self, response, *args, **kwargs):
        if not isinstance(response, str):
            response = json.dumps(response)
        super().__init__(response, *args, content_type="application/json", **kwargs)


def get_template(head1="", head2=""):
    digipad_session = Session(session)
    userinfo = digipad_session.userinfo
    error = session.get("error")
    if error:
        del session["error"]
    return (
        TEMPLATE
        .replace(
            "%(instance)s",
            digipad_session.domain,
        )
        .replace(
            "%(userinfo)s",
            (
                "Impossible de vérifier la connexion"
                if userinfo and userinfo.connection_error
                else (
                    'Non connecté – <a href="/login">Se connecter</a>'
                    if userinfo is None or not userinfo.cookie
                    else f'{escape(str(userinfo))} – <a href="/logout">Se déconnecter</a>'
                )
            ),
        )
        .replace(
            "%(error)s",
            "" if not error else f'<div class="error">{escape(error)}</div>',
        )
        .replace("%(head1)s", head1)
        .replace("%(head2)s", head2)
    )


@app.errorhandler(Exception)
def error_handler(err):
    if request.form.get("format", "html") == "json":
        return JSONResponse(
            {"ok": False, "error": f"{type(err).__qualname__}: {err}"},
            status=getattr(err, "code", 500),
        )
    if (
        app.debug
        or "error" in session
        or request.path == url_for("home") and request.args.get("error")
    ):
        raise err
    session["error"] = f"{type(err).__qualname__}: {err}"
    return redirect(url_for("home", error=1))


@app.route("/")
def home():
    return get_template() % {
        "title": "Accueil",
        "body": f"""\
<ul>
    <li><a href="{url_for("create")}">Création de capsules</a></li>
    <li><a href="{url_for("create_pad")}">Création de pads</a></li>
    <li><a href="{url_for("export")}">Exportation des pads</a></li>
    <li><a href="{url_for("list_pads")}">Liste des pads</a></li>
    <li><a href="{url_for("rename_column")}">Renommage des colonnes</a></li>
</ul>
""",
    }


@app.route("/login", methods=["GET", "POST"])
def login():
    digipad_session = Session(session)
    if digipad_session.userinfo.logged_in:
        return redirect(url_for("home"))

    if request.method == "POST":
        cookie = request.form.get("cookie")
        if cookie:
            session["digipad_cookie"] = cookie
            return redirect(url_for("home"))

        username = request.form.get("username")
        password = request.form.get("password")
        digipad_session.login(username, password)
        session["digipad_cookie"] = digipad_session.userinfo.cookie
        return redirect(url_for("home"))

    return get_template() % {
        "title": "Connexion",
        "body": """\
<h2>Avec nom d'utilisateur et mot de passe</h2>
<form method="post">
<p>
    <label for="username">Nom d'utilisateur :</label>
    <input type="text" name="username" id="username">
</p>
<p>
    <label for="password">Mot de passe :</label>
    <input type="password" name="password" id="password">
</p>
<p>
    <input type="submit" value="OK">
</p>
</form>
<hr>
<h2>Avec cookie Digipad</h2>
<form method="post">
<p>
    <label for="cookie">Cookie Digipad :</label>
    <input type="password" name="cookie" id="cookie">
</p>
<p>
    <input type="submit" value="OK">
</p>
</form>
""",
    }


@app.route("/instance", methods=["GET", "POST"])
def instance():
    digipad_session = Session(session)
    if request.method == "POST":
        session["digipad_instance"] = request.form.get("instance") or DEFAULT_INSTANCE
        return redirect(url_for("home"))

    return get_template() % {
        "title": "Changement d'instance",
        "body": f"""\
<form method="post">
<p>
    <label for="instance">Instance :</label>
    <input type="text" name="instance" id="instance" value="{escape(digipad_session.domain)}">
</p>
<p>
    <input type="submit" value="OK">
</p>
</form>
""",
    }


@app.route("/logout")
def logout():
    if "digipad_cookie" in session:
        del session["digipad_cookie"]
    return redirect(url_for("home"))


@app.route("/create-pad", methods=["GET", "POST"])
def create_pad():
    if request.method == "POST":
        title = request.form.get("title", "")
        if not title.strip():
            raise ValueError("Empty title")
        pads = Session(session).pads
        pads.create_pad(title)
        message = f"Creating pad {title}... OK\n"
        return JSONResponse({"ok": True, "message": message})

    return (
        get_template() % {
            "title": "Création de pads",
            "body": """\
<form method="post" action="javascript:;">
<p>
    <label for="titles">Titres des pads à créer <small>(un par ligne)</small> :</label>
    <br>
    <textarea name="titles" id="titles"></textarea>
</p>
<p>
    <input type="submit" value="OK">
</p>
<pre class="output" data-operation="Creating pad"></pre>
</form>
""",
        }
    )


@app.route("/create", methods=["GET", "POST"])
def create():
    if request.method == "POST":
        pad = Session(session).pads.get(request.form.get("pad", ""))
        block_id = pad.create_block(
            title=request.form.get("title", ""),
            text=request.form.get("text", ""),
            hidden=bool(request.form.get("hidden")),
            column_n=int(request.form.get("column_n", 1)) - 1,
        )
        message = f"Creating block on #{pad.id}... OK\n"
        comment = request.form.get("comment", "")
        if comment:
            message += "Commenting... OK\n"
            pad.comment_block(block_id, request.form.get("title", ""), comment)
        pad.connection.close()
        return JSONResponse({"ok": True, "message": message})

    return (
        get_template(
            """\
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/pell@1/dist/pell.min.css">
<script src="https://cdn.jsdelivr.net/npm/pell@1/dist/pell.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/voca@1/index.min.js"></script>
""",
            '<script src="/static/editor.js"></script>',
        )
        % {
            "title": "Création de capsules",
            "body": """\
<form method="post" action="javascript:;">
<p>
    <label for="pads">Pads <small>(un par ligne)</small> :</label>
    <br>
    <textarea name="pads" id="pads"></textarea>
</p>
<p>
    <label for="title">Titre :</label>
    <input type="text" name="title" id="title">
</p>
<p>
    <label for="text">Texte :</label>
    <br>
    <textarea name="text" id="text" class="editor"></textarea>
</p>
<p>
    <label for="column_n">Numéro de colonne :</label>
    <input type="number" name="column_n" id="column_n" min="1">
</p>
<p>
    <label for="hidden">Bloc caché :</label>
    <input type="checkbox" name="hidden" id="hidden">
</p>
<p>
    <label for="comment">Commentaire :</label>
    <br>
    <textarea name="comment" id="comment" class="editor"></textarea>
</p>
<p>
    <input type="submit" value="OK">
</p>
<pre class="output" data-operation="Creating block"></pre>
</form>
""",
        }
    )


@app.route("/zip", methods=["POST"])
def zip():
    files = request.form.get("files", "").splitlines()
    paths: list[Path] = []
    for file in files:
        path = Path(urlparse(file).path).resolve()
        if not path.is_relative_to(EXPORT_DIRECTORY):
            continue
        paths.append(path)

    export_directory = EXPORT_DIRECTORY / random.randbytes(8).hex()
    export_directory.mkdir(parents=True, exist_ok=True)

    path = export_directory / f"pads_{dt.datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
    with zipfile.ZipFile(path, "w") as zip:
        for path in paths:
            zip.write(path, path.name)
    return "/" + path.relative_to(Path(__file__).resolve()).as_posix()


@app.route("/export", methods=["GET", "POST"])
def export():
    if request.method == "POST":
        pad = Session(session).pads.get(request.form.get("pad", ""))
        export_directory = EXPORT_DIRECTORY / random.randbytes(8).hex()
        export_directory.mkdir(parents=True, exist_ok=True)
        path = pad.export(export_directory)
        url = "/" + path.relative_to(Path(__file__).resolve()).as_posix()
        message = f"Exporting #{pad.id}... OK ({url})\n"
        return JSONResponse({"ok": True, "message": message})

    return (
        get_template(
            """\
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/pell@1/dist/pell.min.css">
<script src="https://cdn.jsdelivr.net/npm/pell@1/dist/pell.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/voca@1/index.min.js"></script>
""",
            '<script src="/static/editor.js"></script>',
        )
        % {
            "title": "Exportation des pads",
            "body": """\
<form method="post" action="javascript:;">
<p>
    <label for="pads">Pads <small>(un par ligne)</small> :</label>
    <br>
    <textarea name="pads" id="pads"></textarea>
</p>
<p>
    <input type="submit" value="OK">
</p>
<pre class="output" data-operation="Renaming column"></pre>
</form>
""",
        }
    )


@app.route("/list", methods=["GET", "POST"])
def list_pads():
    if request.method == "POST":
        query = request.form.get("pads", "")
        format = request.form.get("format", "html")
        pads = Session(session).pads.get_all(query.splitlines())
        data = get_pads_table(pads, format != "json", True)

        if format == "json":
            return Response(
                json.dumps(data),
                content_type="application/json",
            )

        if not pads:
            return get_template() % {
                "title": "Liste des pads",
                "body": "<p>Aucun pad n'a été trouvé avec votre requête :</p><pre>{escape(query)}</pre>",
            }

        return get_template() % {
            "title": "Liste des pads",
            "body": f"""\
<p>Les pads correspondant à la requête</p>
<pre>{escape(query)}</pre>
<p>sont :</p>
{tabulate(data, tablefmt="html", headers="keys")}
""",
        }

    return (
        get_template(
            """\
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/pell@1/dist/pell.min.css">
<script src="https://cdn.jsdelivr.net/npm/pell@1/dist/pell.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/voca@1/index.min.js"></script>
""",
            '<script src="/static/editor.js"></script>',
        )
        % {
            "title": "Liste des pads",
            "body": """\
<form method="post">
<p>
    <label for="pads">Pads <small>(un par ligne)</small> :</label>
    <br>
    <textarea name="pads" id="pads"></textarea>
</p>
<p>
    <input type="submit" value="OK">
</p>
</form>
""",
        }
    )


@app.route("/rename-column", methods=["GET", "POST"])
def rename_column():
    if request.method == "POST":
        pad = Session(session).pads.get(request.form.get("pad", ""))
        pad.rename_column(
            column_number=int(request.form.get("column_n", 1)) - 1,
            column_title=request.form.get("title", ""),
        )
        message = f"Renaming column on #{pad.id}... OK\n"
        pad.connection.close()
        return JSONResponse({"ok": True, "message": message})

    return (
        get_template(
            """\
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/pell@1/dist/pell.min.css">
<script src="https://cdn.jsdelivr.net/npm/pell@1/dist/pell.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/voca@1/index.min.js"></script>
""",
            '<script src="/static/editor.js"></script>',
        )
        % {
            "title": "Renommage des colonnes",
            "body": """\
<form method="post" action="javascript:;">
<p>
    <label for="pads">Pads <small>(un par ligne)</small> :</label>
    <br>
    <textarea name="pads" id="pads"></textarea>
</p>
<p>
    <label for="column_n">Numéro de colonne :</label>
    <input type="number" name="column_n" id="column_n" min="1">
</p>
<p>
    <label for="title">Nouveau titre :</label>
    <input type="text" name="title" id="title">
</p>
<p>
    <input type="submit" value="OK">
</p>
<pre class="output" data-operation="Renaming column"></pre>
</form>
""",
        }
    )


if __name__ == "__main__":
    sys.exit("Please use 'digipad web' to run the server.")
