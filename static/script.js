let mediaRecorder;
let lydBiter = [];
let tidtaker; // Variabel for stoppeklokken
let startTidspunkt; // Når vi startet klokken

const startBtn = document.getElementById('startOpptak');
const stoppBtn = document.getElementById('stoppOpptak');
const statusDiv = document.getElementById('status');
const resultatDiv = document.getElementById('resultat');
const filSkjema = document.getElementById('filSkjema');
const filInput = document.getElementById('lydFil');
const spraakValg = document.getElementById('spraakValg');
const sendFilBtn = document.querySelector('#filSkjema button[type="submit"]');
const tidsbrukDiv = document.getElementById('tidsbruk');

const MAX_FILESIZE = 50 * 1024 * 1024;
const TILLATTE_TYPER = ["audio/mpeg", "audio/wav", "audio/mp3", "audio/ogg", "audio/x-m4a", "video/mp4", "audio/webm"];

function settLasterTilstand(laster) {
    startBtn.disabled = laster;
    filInput.disabled = laster;
    sendFilBtn.disabled = laster;
    spraakValg.disabled = laster;
}

function startStoppeklokke() {
    tidsbrukDiv.classList.remove('ferdig');
    tidsbrukDiv.style.display = 'block';
    startTidspunkt = Date.now();

    tidtaker = setInterval(() => {
        const sekunderBrukt = ((Date.now() - startTidspunkt) / 1000).toFixed(1);
        tidsbrukDiv.innerText = `Tid gått: ${sekunderBrukt} s`;
    }, 100);
}

function stoppStoppeklokke(endeligTidFraBackend) {
    clearInterval(tidtaker);
    const totalFrontendTid = ((Date.now() - startTidspunkt) / 1000).toFixed(1);
    tidsbrukDiv.classList.add('ferdig');
    tidsbrukDiv.innerText = `Ferdig. Whisper AI brukte: ${endeligTidFraBackend} s\n Tid brukt totalt: ${totalFrontendTid} s`;
}

// --- NYE VARIABLER, SLIDERS OG OPPTAKSLOGIKK ---

// Konfigurasjon for modell-slider
const modellNavn = { 1: "tiny", 2: "base", 3: "small", 4: "medium" };
const modellTekst = {
    1: "Tiny (Veldig rask, unøyaktighet)",
    2: "Base (Balansert, standard)",
    3: "Small (Tregere, høy nøyaktighet)",
    4: "Medium (Ekstremt treg, best nøyaktighet)"
};

// Referanser til UI-elementer
const modellSlider = document.getElementById('modellSlider');
const modellBeskrivelse = document.getElementById('modellBeskrivelse');
const kjernerSlider = document.getElementById('kjernerSlider');
const kjernerBeskrivelse = document.getElementById('kjernerBeskrivelse');
const filOpplastingSeksjon = document.getElementById('filOpplastingSeksjon');

const opptakBoks = document.getElementById('opptakBoks');
const opptakTeller = document.getElementById('opptakTeller');
const opptakStatusTekst = document.getElementById('opptakStatusTekst');
const etterOpptakValg = document.getElementById('etterOpptakValg');
const lydAvspiller = document.getElementById('lydAvspiller');
const sendOpptakBtn = document.getElementById('sendOpptakBtn');
const forkastOpptakBtn = document.getElementById('forkastOpptakBtn');

let opptakTidtaker;
let opptakSekunder = 0;
let midlertidigLydBlob = null;

// Hjelpefunksjon for tid (MM:SS)
function formaterTid(sekunder) {
    const min = Math.floor(sekunder / 60).toString().padStart(2, '0');
    const sek = (sekunder % 60).toString().padStart(2, '0');
    return `${min}:${sek}`;
}

// Oppdater teksten når man drar i sliderne
modellSlider.addEventListener('input', (e) => {
    modellBeskrivelse.innerText = modellTekst[e.target.value];
});
kjernerSlider.addEventListener('input', (e) => {
    kjernerBeskrivelse.innerText = `${e.target.value} kjerner valgt`;
});

// Hjelpefunksjon for å rydde opp UI
function tilbakestillOpptakUI() {
    clearInterval(opptakTidtaker);
    opptakBoks.classList.add('skjult');
    startBtn.classList.remove('skjult');
    etterOpptakValg.classList.add('skjult');
    filOpplastingSeksjon.classList.remove('skjult'); // VIS filopplasting igjen
    lydAvspiller.src = "";
    midlertidigLydBlob = null;
}

// 1. Håndter direkte opptak
startBtn.addEventListener('click', async () => {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        mediaRecorder = new MediaRecorder(stream);
        lydBiter = [];

        mediaRecorder.ondataavailable = event => {
            if (event.data.size > 0) lydBiter.push(event.data);
        };

        mediaRecorder.onstop = () => {
            clearInterval(opptakTidtaker);
            midlertidigLydBlob = new Blob(lydBiter, { type: 'audio/webm' });

            if (midlertidigLydBlob.size > MAX_FILESIZE) {
                statusDiv.innerText = "Feil: Opptaket ble for stort.";
                tilbakestillOpptakUI();
                settLasterTilstand(false);
                return;
            }

            stoppBtn.classList.add('skjult');
            opptakStatusTekst.innerText = "Opptak ferdig. Sjekk lyden og velg under:";
            opptakStatusTekst.classList.remove('blinker');

            const lydUrl = URL.createObjectURL(midlertidigLydBlob);
            lydAvspiller.src = lydUrl;
            etterOpptakValg.classList.remove('skjult');

            stream.getTracks().forEach(track => track.stop());
        };

        mediaRecorder.start();
        settLasterTilstand(true);

        startBtn.classList.add('skjult');
        opptakBoks.classList.remove('skjult');
        stoppBtn.classList.remove('skjult');
        etterOpptakValg.classList.add('skjult');
        filOpplastingSeksjon.classList.add('skjult'); // SKJUL filopplasting

        opptakStatusTekst.innerText = "🔴 Tar opp lyd...";
        opptakStatusTekst.classList.add('blinker');

        opptakSekunder = 0;
        opptakTeller.innerText = "00:00";
        opptakTidtaker = setInterval(() => {
            opptakSekunder++;
            opptakTeller.innerText = formaterTid(opptakSekunder);
        }, 1000);

        statusDiv.innerText = "";
        resultatDiv.innerText = "";
        tidsbrukDiv.style.display = 'none';
    } catch (err) {
        statusDiv.innerText = "Feil: Fikk ikke tilgang til mikrofonen.";
        console.error(err);
    }
});

// Stopp-knapp
stoppBtn.addEventListener('click', () => {
    mediaRecorder.stop();
});

// Knapp for å sende inn lyden etter å ha hørt på den
endOpptakBtn.addEventListener('click', async () => {
    const blobÅSende = midlertidigLydBlob;
    tilbakestillOpptakUI();

    statusDiv.innerText = "Sender til AI-server for transkribering...";
    startStoppeklokke();

    await sendTilBackend(blobÅSende, 'mikrofon_opptak.webm');
});

// Knapp for å kaste lyden
forkastOpptakBtn.addEventListener('click', () => {
    tilbakestillOpptakUI();
    statusDiv.innerText = "Opptak forkastet.";
    settLasterTilstand(false);
});

// 2. Håndter filopplasting
filSkjema.addEventListener('submit', async (e) => {
    e.preventDefault();
    const fil = document.getElementById('lydFil').files[0];
    if (!fil) return;

    if (fil.size > MAX_FILESIZE) {
        statusDiv.innerText = "Feil: Filen er for stor, maks 50 MB tillatt.";
        return;
    }


    //fil validering
    const gyldigeEndelser = ['.weba', '.webm', '.mp3', '.wav', '.m4a', '.mp4', '.ogg', '.flac'];
    const harGyldigEndelse = gyldigeEndelser.some(endelse => fil.name.toLowerCase().endsWith(endelse));
    if (!TILLATTE_TYPER.includes(fil.type) && !fil.type.startsWith("audio/") && !fil.type.startsWith("video/") && !harGyldigEndelse) {
        statusDiv.innerText = `Feil: Ugyldig filtype (${fil.type}). Vennligst velg en godkjent fil.`;
        return;
    }

    settLasterTilstand(true);
    startStoppeklokke();
    statusDiv.innerText = "Sender fil og venter på server...";
    resultatDiv.innerText = "";

    await sendTilBackend(fil, fil.name);
});

// 3. Kommunikasjon med backend
async function sendTilBackend(filData, filNavn) {
    const formData = new FormData();
    const modellVerdi = modellSlider.value;
    const faktiskModell = modellNavn[modellVerdi];
    const kjernerVerdi = kjernerSlider.value;

    const lydSpraak = document.querySelector('input[name="lydSpraak"]:checked').value;

    formData.append('modell', faktiskModell);
    formData.append('kjerner', kjernerVerdi);
    formData.append('file', filData, filNavn);
    formData.append('language', spraakValg.value);

    try {
        const response = await fetch('/transkriber', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) throw new Error("Serverfeil ved opplasting");

        const data = await response.json();
        statusDiv.innerText = "Fil mottatt, sjekker status...";
        sjekkJobbStatus(data.job_id);

    } catch (err) {
        clearInterval(tidtaker);
        settLasterTilstand(false);
        statusDiv.innerText = "Nettverksfeil eller avvist av server.";
        resultatDiv.innerText = String(err);
    }
}

// 4. Polling for jobbstatus
async function sjekkJobbStatus(jobId) {
    try {
        const response = await fetch(`/jobb/${jobId}`);
        if (!response.ok) throw new Error("Klarte ikke hente status");

        const data = await response.json();

        if (data.status === "ferdig") {
            stoppStoppeklokke(data.tid_brukt);
            settLasterTilstand(false);
            statusDiv.innerText = "Transkribering fullført";
            resultatDiv.innerText = data.tekst.replace(/\n/g, ' ');
        } else if (data.status === "feil") {
            clearInterval(tidtaker);
            settLasterTilstand(false);
            statusDiv.innerText = "Feil under transkribering.";
            resultatDiv.innerText = data.melding;
        } else {
            if (data.melding) {
                statusDiv.innerText = data.melding;
            }
            setTimeout(() => sjekkJobbStatus(jobId), 1000);
        }
    } catch (error) {
        clearInterval(tidtaker);
        settLasterTilstand(false);
        statusDiv.innerText = "Feil ved henting av status.";
        resultatDiv.innerText = String(error);
    }
}

// 5. Oppdater den status symbolet
async function sjekkServerStatus(){
    try{
        let res= await fetch('/status');
        let data = await res.json();
        let prikk = document.getElementById('status-indicator');

        if (data.status === 'online'){
            prikk.style.backgroundColor = 'green';
            prikk.title = 'AI-serveren er Online';
        } else {
            prikk.style.backgroundColor = 'red';
            prikk.title = 'Ingen kontakt med AI-server';
        }
    } catch (e) {
        console.log('Kunne ikke sjekke status');
    }
}
setInterval(sjekkServerStatus, 5000);