import sys
from html import escape
from pathlib import Path

from flask import Flask, Response, redirect, request, session, url_for

from ..session import Session
from ..utils import login as digipad_login

app = Flask(__name__)

TEMPLATE = (Path(__file__).parent / "template.html").read_text("utf-8")


def get_template():
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
<h1>Digipad API</h1>
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
        except Exception as err:
            session["error"] = f"{type(err).__qualname__}: {err}"
            return redirect("")
        session["digipad_cookie"] = userinfo.cookie
        return redirect(url_for("home"))

    return get_template() % {
        "title": "Connexion",
        "body": """\
<h1>Connexion</h1>
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
    return get_template() % {
        "title": "Création de capsules",
        "body": """\
<h1>Création de capsules</h1>
<form method="post">
<p>
    <label for="title">Titre :</label>
    <input type="text" name="title" id="title">
</p>
<p>
    <label for="text">Texte :</label>
    <br>
    <textarea name="text" id="text"></textarea>
</p>
<p>
    <input type="submit" value="OK">
</p>
</form>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/pell@1/dist/pell.min.css">
<script src="https://cdn.jsdelivr.net/npm/pell@1/dist/pell.min.js"></script>
<script src="/static/editor.js"></script>
""",
    }


@app.route("/export", methods=["GET", "POST"])
def export():
    return get_template()


@app.route("/list", methods=["GET", "POST"])
def list_pads():
    return get_template()


@app.route("/rename-column", methods=["GET", "POST"])
def rename_column():
    return get_template()


if __name__ == "__main__":
    sys.exit("Please use 'digipad web' to run the server.")
