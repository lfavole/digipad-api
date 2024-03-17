window.addEventListener("DOMContentLoaded", function() {
    if(!window.pell) return;

    document.querySelectorAll("textarea.editor").forEach(textarea => {
        var editor = document.createElement("div");
        editor.id = "editor";
        textarea.parentElement.insertBefore(editor, textarea);

        var pell_editor = pell.init({
            element: editor,
            onChange: (html) => {
                var html = html.replace(/(<a [^>]*)(target="[^"]*")([^>]*>)/gi, "$1$3")
                    html = html.replace(/(<a [^>]*)(>)/gi, "$1 target='_blank'$2")
                textarea.value = html;
            },
            actions: [
                {name: "gras", title: "Gras", icon: "<b>B</b>", result: () => pell.exec("bold")},
                {name: "italique", title: "Italique", icon: "<i>I</i>", result: () => pell.exec("italic")},
                {name: "souligne", title: "Souligné", icon: "<u>U</u>", result: () => pell.exec("underline")},
                {name: "barre", title: "Barré", icon: "<s>T</s>", result: () => pell.exec("strikethrough")},
                {name: "listeordonnee", title: "Liste ordonnée", icon: '<span class="list-icon">1. —<br>2. —<br>3. —</span>', result: () => pell.exec("insertOrderedList")},
                {name: "liste", title: "Liste", icon: '<span class="list-icon">· —<br>· —<br>· —</span>', result: () => pell.exec("insertUnorderedList")},
                {name: "couleur", title: "Couleur", icon: "A<input class='couleur-texte' type='color'>", result: () => undefined},
                {name: "lien", title: "Lien", icon: '<span class="link-icon">Lien</span>', result: () => {const url = window.prompt("Adresse du lien :"); if(url) pell.exec("createLink", url)}},
            ],
        });
        editor.content.innerHTML = textarea.value;
        pell_editor.addEventListener("paste", function(evt) {
            evt.preventDefault();
            evt.stopPropagation();
            var html = evt.clipboardData.getData("text/html");
            if(html) {
                html = v.stripTags(html, ["b", "i", "u", "a", "br", "div", "font", "ul", "ol"]);
                html = html.replace(/style=".*?"/mg, "");
                html = html.replace(/class=".*?"/mg, "");
                pell.exec("insertHTML", html);
            } else {
                pell.exec("insertText", evt.clipboardData.getData("text/plain"));
            }
        });
        editor.querySelector(".couleur-texte").addEventListener("change", function(event) {
            pell.exec("foreColor", event.target.value);
        });

        textarea.style.display = "none";
    });
});
