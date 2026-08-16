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
    // Låser eller åpner knappene slik at man ikke kan dobbelttrykke
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
        tidsbrukDiv.innerText = `AI jobber... Tid gått: ${sekunderBrukt} s`;
    }, 100);
}

function stoppStoppeklokke(endeligTidFraBackend) {
    clearInterval(tidtaker);
    const totalFrontendTid = ((Date.now() - startTidspunkt) / 1000).toFixed(1);
    tidsbrukDiv.classList.add('ferdig');
    tidsbrukDiv.innerText = `Ferdig. Tid brukt (backend): ${endeligTidFraBackend} s\n Tid brukt (frontend): ${totalFrontendTid} s`;
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

        mediaRecorder.onstop = async () => {
            const lydBlob = new Blob(lydBiter, { type: 'audio/webm' });

            if (lydBlob.size > MAX_FILESIZE) {
                statusDiv.innerText = "Feil: Opptaket ble for stort.";
                settLasterTilstand(false); // Lås opp knapper igjen
                return;
            }

            statusDiv.innerText = "Sender til AI-server for transkribering...";
            startStoppeklokke();
            await sendTilBackend(lydBlob, 'mikrofon_opptak.webm');
            stream.getTracks().forEach(track => track.stop());
        };

        mediaRecorder.start();
        settLasterTilstand(true); // Lås alt unntatt stoppknappen
        stoppBtn.disabled = false;
        statusDiv.innerText = "Tar opp... Snakk i mikrofonen!";
        resultatDiv.innerText = "";
        tidsbrukDiv.style.display = 'none'; // Skjul klokken mens vi tar opp
    } catch (err) {
        statusDiv.innerText = "Feil: Fikk ikke tilgang til mikrofonen.";
        console.error(err);
    }
});

stoppBtn.addEventListener('click', () => {
    mediaRecorder.stop();
    stoppBtn.disabled = true;
});


// 2. Håndter filopplasting
filSkjema.addEventListener('submit', async (e) => {
    e.preventDefault();
    const fil = document.getElementById('lydFil').files[0];
    if (!fil) return;

    // 1. Validering av filstørrelse
    if (fil.size > MAX_FILESIZE) {
        statusDiv.innerText = "Feil: Filen er for stor! Maks 50 MB tillatt.";
        return; // Stopper prosessen umiddelbart
    }

    // 2. Validering av filtype (Fail Fast i frontend)
    if (!TILLATTE_TYPER.includes(fil.type) && !fil.type.startsWith("audio/") && !fil.type.startsWith("video/")) {
        statusDiv.innerText = "Feil: Ugyldig filtype. Vennligst velg en godkjent lyd- eller videofil.";
        return; // Stopper prosessen umiddelbart
    }

    settLasterTilstand(true); // Lås alle inputfelter
    startStoppeklokke();      // Start telleren
    statusDiv.innerText = "Sender fil og venter på server...";
    resultatDiv.innerText = "";

    await sendTilBackend(fil, fil.name);
});


// 3. Kommunikasjon med backend
async function sendTilBackend(filData, filNavn) {
    const formData = new FormData();
    const modellValg = document.getElementById('modellValg').value;
    const kjernerValg = document.getElementById('kjernerValg').value;

    formData.append('modell', modellValg);
    formData.append('kjerner', kjernerValg);
    formData.append('file', filData, filNavn);
    formData.append('language', spraakValg.value);

    try {
        const response = await fetch('/transkriber', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) throw new Error("Serverfeil ved opplasting");

        const data = await response.json();
        statusDiv.innerText = "Fil mottatt! Sjekker status...";
        sjekkJobbStatus(data.job_id);

    } catch (err) {
        clearInterval(tidtaker);
        settLasterTilstand(false); // Lås opp ved feil
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
            settLasterTilstand(false); // Åpne knapper igjen
            statusDiv.innerText = "Transkribering fullført!";
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
            setTimeout(() => sjekkJobbStatus(jobId), 3000);
        }
    } catch (error) {
        clearInterval(tidtaker);
        settLasterTilstand(false);
        statusDiv.innerText = "Feil ved henting av status.";
        resultatDiv.innerText = String(error);
    }
}

// 5. Oppdater den status symbolet,  som sjekker om serveren lever
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
