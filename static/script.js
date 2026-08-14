let mediaRecorder;
let lydBiter = [];

const startBtn = document.getElementById('startOpptak');
const stoppBtn = document.getElementById('stoppOpptak');
const statusDiv = document.getElementById('status');
const resultatDiv = document.getElementById('resultat');
const filSkjema = document.getElementById('filSkjema');

// Konstanter for validering, samme som backend
const MAX_FILESIZE = 50 * 1024 * 1024; // 50 MB
const TILLATTE_TYPER = ["audio/mpeg", "audio/wav", "audio/mp3", "audio/ogg", "audio/x-m4a", "video/mp4", "audio/webm"];


// 1. Håndter direkte opptak via mikrofon
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

            // Validering av størrelse på opptak
            if (lydBlob.size > MAX_FILESIZE) {
                statusDiv.innerText = "Feil: Opptaket ble for stort (maks 50 MB).";
                return;
            }

            statusDiv.innerText = "Sender til AI-server for transkribering...";
            await sendTilBackend(lydBlob, 'mikrofon_opptak.webm');
            stream.getTracks().forEach(track => track.stop());
        };

        mediaRecorder.start();
        startBtn.disabled = true;
        stoppBtn.disabled = false;
        statusDiv.innerText = "Tar opp... Snakk i mikrofonen!";
        resultatDiv.innerText = "";
    } catch (err) {
        statusDiv.innerText = "Feil: Fikk ikke tilgang til mikrofonen. Sjekk at nettleseren har tillatelse.";
        console.error(err);
    }
});

// Stopper opptaket
stoppBtn.addEventListener('click', () => {
    mediaRecorder.stop();
    startBtn.disabled = false;
    stoppBtn.disabled = true;
});


// 2. håndter filopplasting
filSkjema.addEventListener('submit', async (e) => {
    e.preventDefault();
    const fil = document.getElementById('lydFil').files[0];
    if (!fil) return;

    // validering av filstørrelse
    if (fil.size > MAX_FILESIZE) {
        statusDiv.innerText = "Feil: Filen er for stor! Maks 50 MB tillatt.";
        return;
    }

    // Validering av filtype
    if (!TILLATTE_TYPER.includes(fil.type) && !fil.type.startsWith("audio/") && !fil.type.startsWith("video/")) {
        statusDiv.innerText = "Advarsel: Filtypen kan være ugyldig, men vi gjør et forsøk...";
    } else {
        statusDiv.innerText = "Laster opp fil...";
    }

    resultatDiv.innerText = "";
    await sendTilBackend(fil, fil.name);
});


// 3. Kommunikasjon med backend
async function sendTilBackend(filData, filNavn) {
    const formData = new FormData();
    formData.append('file', filData, filNavn);

    // Hent ut valgt språk valget
    const valgtSpraak = document.getElementById('spraakValg').value;
    formData.append('language', valgtSpraak);

    try {
        const response = await fetch('/transkriber', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => null);
            throw new Error(errorData ? errorData.detail : `Serverfeil: ${response.status}`);
        }

        const data = await response.json();

        //fikk jobb-ID tilbake, starter
        const jobId = data.job_id;
        statusDiv.innerText = "Fil mottatt! AI-serveren jobber med transkriberingen...";

        sjekkJobbStatus(jobId);

    } catch (err) {
        statusDiv.innerText = "Nettverksfeil eller avvist av server.";
        resultatDiv.innerText = String(err);
    }
}

// 4. Polling for å sjekke om bakgrunnsjobben er ferdig
async function sjekkJobbStatus(jobId) {
    try {
        const response = await fetch(`/jobb/${jobId}`);
        if (!response.ok) throw new Error("Klarte ikke å hente status fra serveren.");

        const data = await response.json();

        if (data.status === "ferdig") {
            statusDiv.innerText = `Ferdig! Brukte ${data.tid_brukt} sekunder.`;
            resultatDiv.innerText = data.tekst;
        } else if (data.status === "feil") {
            statusDiv.innerText = "Feil under transkribering.";
            resultatDiv.innerText = data.melding;
        } else {
            // Hvis status er "jobber", venter vi 3 sekunder og spør på nytt
            statusDiv.innerText = "AI-serveren jobber fortsatt... vennligst vent.";
            setTimeout(() => sjekkJobbStatus(jobId), 3000);
        }
    } catch (error) {
        statusDiv.innerText = "Feil ved henting av status.";
        resultatDiv.innerText = String(error);
    }
}


// 5. Oppdater status symbol som sjekker om serveren lever
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
        console.log('Kunne ikke sjekke status')
    }
}
setInterval(sjekkServerStatus, 5000);