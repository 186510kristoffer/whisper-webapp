function formaterSekunder(sek) {
    if (!sek || isNaN(sek)) return "-";
    const minutter = Math.floor(sek / 60);
    const restSekunder = Math.round(sek % 60);
    if (minutter > 0) {
        return `${minutter}m ${restSekunder}s`;
    }
    return `${sek.toFixed(1)}s`;
}

function formaterDato(isoStreng) {
    if (!isoStreng) return "-";
    const d = new Date(isoStreng);
    return d.toLocaleString("no-NO", {
        day: "2-digit",
        month: "2-digit",
        hour: "2-digit",
        minute: "2-digit"
    });
}

function toggleTekst(id) {
    const kort = document.getElementById(`tekst-kort-${id}`);
    const full = document.getElementById(`tekst-full-${id}`);
    const knapp = document.getElementById(`knapp-${id}`);

    if (full.style.display === "none") {
        full.style.display = "inline";
        kort.style.display = "none";
        knapp.innerText = "Vis mindre";
    } else {
        full.style.display = "none";
        kort.style.display = "inline";
        knapp.innerText = "Vis mer";
    }
}

async function lastHistorikk() {
    const lasterStatus = document.getElementById("laster-status");
    const container = document.getElementById("historikk-kort-container");

    try {
        const res = await fetch("/api/historikk");
        if (!res.ok) throw new Error("Kunne ikke hente data.");

        const data = await res.json();

        if (data.length === 0) {
            lasterStatus.innerText = "Ingen transkripsjoner er lagret ennå.";
            return;
        }

        container.innerHTML = "";

        data.forEach(rad => {
            // Håndterer lang tekst (økte grensen litt til 150 tegn for det nye designet)
            const harLangTekst = rad.tekst && rad.tekst.length > 150;
            const kortTekst = harLangTekst ? rad.tekst.substring(0, 150) + "..." : (rad.tekst || "-");

            const tekstBlokk = harLangTekst ? `
                <span id="tekst-kort-${rad.id}">${kortTekst}</span>
                <span id="tekst-full-${rad.id}" style="display: none;">${rad.tekst}</span>
                <br><br>
                <span class="vis-mer-knapp" id="knapp-${rad.id}" onclick="toggleTekst(${rad.id})">Vis mer</span>
            ` : (rad.tekst || "-");

            // Håndter potensielle null-verdier trygt
            const totalTid = rad.total_tid_sek ? `${rad.total_tid_sek} s` : "N/A";
            const sluttTemp = rad.telefon_slutt_temp ? `${rad.telefon_slutt_temp} °C` : "N/A";
            const lydLengde = rad.lengde_sekunder ? formaterSekunder(rad.lengde_sekunder) : "N/A";
            const filStr = rad.fil_str_mb ? `${rad.fil_str_mb} MB` : "N/A";
            const aiTid = rad.tid_brukt_sek ? `${rad.tid_brukt_sek} s` : "-";

            // Bygg HTML for kortet
            const kort = document.createElement("div");
            kort.className = "historikk-kort";

            kort.innerHTML = `
                <div class="historikk-header">
                    <div class="historikk-tittel">${rad.filnavn || "Ukjent fil"}</div>
                    <div class="historikk-dato">${formaterDato(rad.tidspunkt)}</div>
                </div>
                
                <div class="historikk-meta">
                    <div class="meta-felt">
                        <span class="meta-label">Språk</span>
                        <span class="meta-verdi">${rad.sprak || "-"}</span>
                    </div>
                    <div class="meta-felt">
                        <span class="meta-label">Modell / Kjerner</span>
                        <span class="meta-verdi">${rad.modell || "-"} (${rad.kjerner || "-"})</span>
                    </div>
                    <div class="meta-felt">
                        <span class="meta-label">Lydlengde</span>
                        <span class="meta-verdi">${lydLengde}</span>
                    </div>
                    <div class="meta-felt">
                        <span class="meta-label">Filstørrelse</span>
                        <span class="meta-verdi">${filStr}</span>
                    </div>
                    <div class="meta-felt">
                        <span class="meta-label">AI Tid (Whisper)</span>
                        <span class="meta-verdi">${aiTid}</span>
                    </div>
                    <div class="meta-felt">
                        <span class="meta-label">Total Tid (Backend)</span>
                        <span class="meta-verdi">${totalTid}</span>
                    </div>
                    <div class="meta-felt">
                        <span class="meta-label">CPU Temp</span>
                        <span class="meta-verdi">${sluttTemp}</span>
                    </div>
                </div>
                
                <div class="transkripsjon-tekst">
                    ${tekstBlokk}
                </div>
            `;

            container.appendChild(kort);
        });

        lasterStatus.style.display = "none";

    } catch (err) {
        lasterStatus.innerText = "Feil ved lasting av historikk.";
        console.error(err);
    }
}

document.addEventListener("DOMContentLoaded", lastHistorikk);