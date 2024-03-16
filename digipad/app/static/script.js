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
            var formdata = new FormData();
            formdata.append("pads", form.pads.value);
            formdata.append("format", "json");
            var req = await fetch(
                "/list",
                {
                    method: "POST",
                    body: formdata
                },
            );
            var data = await req.json();

            output.textContent = "";
            output.textContent += `${data.length} pad${data.length >= 2 ? "s" : ""} found\n`;

            for(var i = 0, l = data.length; i < l; i++) {
                var pad = data[i];
                var formdata = new FormData(form);
                formdata.delete("pads");
                formdata.append("pad", pad.id + "/" + pad.hash);
                output.textContent += `Creating block on ${pad.id}... `;
                var req = await fetch(
                    "/create",
                    {
                        method: "POST",
                        body: formdata
                    },
                );
                output.textContent += (req.ok ? "OK" : "error") + "\n";
            }
        });
    });
});
