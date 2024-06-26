window.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll("form").forEach(form => {
        var output = form.querySelector(".output");
        if(!output) return;
        var operation = output.dataset.operation;
        var exporting = operation == "Exporting pads";
        form.addEventListener("submit", async evt => {
            evt.preventDefault();

            var filenames = [];

            var text = "";
            var currentLine = "";

            var updateText = () => {output.textContent = text + currentLine};
            var nextLine = () => {text += currentLine; currentLine = ""};

            if(form.titles) {
                var pads = form.titles.value.split("\n");
            } else {
                var formdata = new FormData();
                formdata.append("pads", form.pads.value);
                formdata.append("format", "json");

                currentLine = "Fetching pads list... ";
                updateText();
                var req = await fetch(
                    "/list",
                    {
                        method: "POST",
                        body: formdata
                    },
                );
                var pads = await req.json();
            }
            currentLine += `${pads.length} pad${pads.length >= 2 ? "s" : ""} found\n`;
            updateText();

            for(var i = 0, l = pads.length; i < l; i++) {
                nextLine();

                var pad = pads[i];
                var formdata = new FormData(form);
                if(form.titles) {
                    formdata.delete("titles");
                    formdata.append("title", pad);
                } else {
                    formdata.delete("pads");
                    formdata.append("pad", pad.id + "/" + pad.hash);
                }
                formdata.append("format", "json");

                if(form.titles) {
                    currentLine = `${operation} ${pad}... `;
                } else {
                    currentLine = `${operation} on #${pad.id}... `;
                }
                updateText();
                var req = await fetch(
                    location.href,
                    {
                        method: "POST",
                        body: formdata
                    },
                );
                var data = await req.json();

                currentLine = data.ok ? data.message : `${currentLine}Error: ${data.error}\n`;
                updateText();

                if(exporting) {
                    var match = /\((\/static\/.*?)\)/.exec(data.message);
                    if(match) filenames.push(match[1]);
                }
            }

            if(exporting) {
                nextLine();

                currentLine = `Zipping ${filenames.length} pad${filenames.length >= 2 ? "s" : ""}... `;
                updateText();

                var formdata = new FormData();
                formdata.append("files", filenames.join("\n"));
                formdata.append("format", "json");
                var req = await fetch(
                    "/zip",
                    {
                        method: "POST",
                        body: formdata
                    },
                );
                var data = await req.text();

                currentLine += `Zip is available at ${data}\n`;
                updateText();
            }
        });
    });
});
