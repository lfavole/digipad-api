import json
import sys
from html import escape
from pathlib import Path

from flask import Flask, Response, redirect, request, session, url_for
from tabulate import tabulate

from ..session import Session
from ..utils import get_pads_table, login as digipad_login

app = Flask(__name__)

TEMPLATE = (Path(__file__).parent / "template.html").read_text("utf-8")


def get_template(head1="", head2=""):
    userinfo = Session(session).userinfo
    error = session.get("error")
    if error:
        del session["error"]
    return (
        TEMPLATE
        .replace(
            "%(userinfo)s",
            "Impossible de vérifier la connexion"
            if userinfo and userinfo.connection_error
            else 'Non connecté – <a href="/login">Se connecter</a>'
            if userinfo is None or not userinfo.cookie
            else f'{escape(str(userinfo))} – <a href="/logout">Se déconnecter</a>',
        )
        .replace(
            "%(error)s",
            "" if not error else f'<div class="error">{escape(error)}</div>',
        )
        .replace("%(head1)s", head1)
        .replace("%(head2)s", head2)
    )


@app.route("/sw.js")
def editor():
    return Response(
        (Path(__file__).parent / "static/sw.js").read_text("utf-8"),
        content_type="text/javascript",
    )


@app.route("/")
def home():
    return get_template() % {
        "title": "Accueil",
        "body": f"""\
<ul>
    <li><a href="{url_for("create")}">Création de capsules</a></li>
    <li><a href="{url_for("export")}">Exportation des pads</a></li>
    <li><a href="{url_for("list_pads")}">Liste des pads</a></li>
    <li><a href="{url_for("rename_column")}">Renommage des colonnes</a></li>
</ul>
""",
    }


@app.route("/login", methods=["GET", "POST"])
def login():
    userinfo = Session(session).userinfo
    if userinfo is not None and userinfo.cookie:
        return redirect(url_for("home"))

    if request.method == "POST":
        cookie = request.form.get("cookie")
        if cookie:
            session["digipad_cookie"] = cookie
            return redirect(url_for("home"))

        username = request.form.get("username")
        password = request.form.get("password")
        try:
            userinfo = digipad_login(username, password)
        except (OSError, RuntimeError) as err:
            session["error"] = f"{type(err).__qualname__}: {err}"
            return redirect("")
        session["digipad_cookie"] = userinfo.cookie
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


@app.route("/logout")
def logout():
    if "digipad_cookie" in session:
        del session["digipad_cookie"]
    return redirect(url_for("home"))


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
        comment = request.form.get("comment", "")
        if comment:
            pad.comment_block(block_id, request.form.get("title", ""), comment)
        return "OK"

    return get_template("""\
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/pell@1/dist/pell.min.css">
<script src="https://cdn.jsdelivr.net/npm/pell@1/dist/pell.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/voca@1/index.min.js"></script>
""", '<script src="/static/editor.js"></script>') % {
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
<pre class="output"></pre>
</form>
""",
    }


@app.route("/export", methods=["GET", "POST"])
def export():
    return get_template()


@app.route("/list", methods=["GET", "POST"])
def list_pads():
    if request.method == "POST":
        query = request.form.get("pads", "")
        format = request.form.get("format", "html")
        pads = Session(session).pads.get_all(query.split("\n"))
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

    return get_template("""\
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/pell@1/dist/pell.min.css">
<script src="https://cdn.jsdelivr.net/npm/pell@1/dist/pell.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/voca@1/index.min.js"></script>
""", '<script src="/static/editor.js"></script>') % {
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


@app.route("/rename-column", methods=["GET", "POST"])
def rename_column():
    return get_template()


if __name__ == "__main__":
    sys.exit("Please use 'digipad web' to run the server.")
