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
    const tabell = document.getElementById("historikkTabell");
    const tabellKropp = document.getElementById("tabellKropp");

    try {
        const res = await fetch("/api/historikk");
        if (!res.ok) throw new Error("Kunne ikke hente data.");

        const data = await res.json();

        if (data.length === 0) {
            lasterStatus.innerText = "Ingen transkripsjoner er lagret ennå.";
            return;
        }

        tabellKropp.innerHTML = "";

        data.forEach(rad => {
            const tr = document.createElement("tr");

            const harLangTekst = rad.tekst && rad.tekst.length > 80;
            const kortTekst = harLangTekst ? rad.tekst.substring(0, 80) + "..." : (rad.tekst || "-");

            const tekstCelle = harLangTekst ? `
                <span id="tekst-kort-${rad.id}">${kortTekst}</span>
                <span id="tekst-full-${rad.id}" style="display: none;">${rad.tekst}</span>
                <br>
                <span class="vis-mer-knapp" id="knapp-${rad.id}" onclick="toggleTekst(${rad.id})">Vis mer</span>
            ` : (rad.tekst || "-");

            // Sikre oss mot tomme felt hvis noen gamle rader mangler data
            const totalTid = rad.total_tid_sek ? `${rad.total_tid_sek} s` : "-";
            const sluttTemp = rad.telefon_slutt_temp ? `${rad.telefon_slutt_temp} °C` : "-";

            tr.innerHTML = `
                <td style="white-space: nowrap;">${formaterDato(rad.tidspunkt)}</td>
                <td><b>${rad.filnavn || "-"}</b></td>
                <td style="white-space: nowrap;">${rad.modell || "-"} (${rad.kjerner || "-"} k.)</td>
                <td style="white-space: nowrap;">${formaterSekunder(rad.lengde_sekunder)}</td>
                <td style="white-space: nowrap;">${rad.fil_str_mb ? rad.fil_str_mb + " MB" : "-"}</td>
                <td style="white-space: nowrap;">${formaterSekunder(rad.tid_brukt_sek)}</td>
                <td style="white-space: nowrap;">${totalTid}</td>
                <td style="white-space: nowrap;">${sluttTemp}</td>
                <td>${tekstCelle}</td>
            `;

            tabellKropp.appendChild(tr);
        });

        lasterStatus.style.display = "none";
        tabell.style.display = "table";

    } catch (err) {
        lasterStatus.innerText = "Feil ved lasting av historikk.";
        console.error(err);
    }
}

document.addEventListener("DOMContentLoaded", lastHistorikk);