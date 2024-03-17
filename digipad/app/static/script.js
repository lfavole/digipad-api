window.addEventListener("DOMContentLoaded", () => {
    if("serviceWorker" in navigator) {
        navigator.serviceWorker.register("/sw.js", {scope: "/"})
        .then(function(reg) {
            console.log(`Service worker registration succeeded. Scope is ${reg.scope}`);
        })
        .catch(function(error) {
            console.error("Service worker registration failed:", error);
        });
    }

    document.querySelectorAll("form").forEach(form => {
        var output = form.querySelector(".output");
        if(!output) return;
        form.addEventListener("submit", async evt => {
            evt.preventDefault();

            var text = "";
            var currentLine = "";

            var updateText = () => {output.textContent = text + currentLine};
            var nextLine = () => {text += currentLine; currentLine = ""};

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
            currentLine += `${pads.length} pad${pads.length >= 2 ? "s" : ""} found\n`;
            updateText();

            for(var i = 0, l = pads.length; i < l; i++) {
                nextLine();

                var pad = pads[i];
                var formdata = new FormData(form);
                formdata.delete("pads");
                formdata.append("pad", pad.id + "/" + pad.hash);
                formdata.append("format", "json");

                currentLine = `${output.dataset.operation} on ${pad.id}... `;
                updateText();
                var req = await fetch(
                    "/create",
                    {
                        method: "POST",
                        body: formdata
                    },
                );
                var data = await req.json();

                currentLine = data.ok ? data.message : `${currentLine}Error: ${data.error}\n`;
                updateText();
            }
        });
    });
});
