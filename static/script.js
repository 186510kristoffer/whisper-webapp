let mediaRecorder;
let lydBiter = [];

const startBtn = document.getElementById('startOpptak');
const stoppBtn = document.getElementById('stoppOpptak');
const statusDiv = document.getElementById('status');
const resultatDiv = document.getElementById('resultat');
const filSkjema = document.getElementById('filSkjema');

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
            statusDiv.innerText = "Sender til AI-server for transkribering (dette kan ta litt tid)...";

            const lydBlob = new Blob(lydBiter, { type: 'audio/webm' });
            await sendTilBackend(lydBlob, 'mikrofon_opptak.webm');

            stream.getTracks().forEach(track => track.stop());
        };

        mediaRecorder.start();
        startBtn.disabled = true;
        stoppBtn.disabled = false;
        statusDiv.innerText = "🔴 Tar opp... Snakk i mikrofonen!";
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

// 2. Håndter tradisjonell filopplasting
filSkjema.addEventListener('submit', async (e) => {
    e.preventDefault();
    const fil = document.getElementById('lydFil').files[0];
    if (!fil) return;

    statusDiv.innerText = "Sender fil til AI-server (dette kan ta litt tid)...";
    resultatDiv.innerText = "";
    await sendTilBackend(fil, fil.name);
});

async function sendTilBackend(filData, filNavn) {
    const formData = new FormData();
    formData.append('file', filData, filNavn);

    // Hent ut valgt språk fra nedtrekksmenyen
    const valgtSpraak = document.getElementById('spraakValg').value;
    formData.append('language', valgtSpraak); // Sender f.eks. 'no' eller 'en'

    try {
        const response = await fetch('/transkriber', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (data.error) {
            resultatDiv.innerText = "Feil fra server: " + data.error;
        } else {
            resultatDiv.innerText = data.text || JSON.stringify(data, null, 2);
        }
        statusDiv.innerText = "Ferdig!";
    } catch (err) {
        statusDiv.innerText = "Nettverksfeil. Fikk ikke kontakt med serveren.";
        resultatDiv.innerText = String(err);
    }
}