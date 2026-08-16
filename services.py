import os
import time
import uuid
import httpx
from fastapi import BackgroundTasks
from database import SessionLocal, Transkripsjon

import json
import asyncio
import subprocess



WHISPER_URL = os.getenv("WHISPER_URL", "http://127.0.0.1:8080/inference")
WHISPER_BASE_URL = os.getenv("WHISPER_BASE_URL", "http://127.0.0.1:8080/")

telefon_lock = asyncio.Lock()
TILSTANDS_FIL = "lading_aktiv"
jobber = {}
siste_jobb_tid = 0.0
aktiv_ssh_prosess = None
gjeldende_modell = None




async def sjekk_server_status() -> bool:
    """
    Sjekker om den eksterne AI-serveren kjører ved å pinge rotadressen.
    Returnerer True hvis serveren svarer uten krasj, ellers False.
    """
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            response = await client.get(WHISPER_BASE_URL)
            if response.status_code < 500:
                return True
    except Exception:
        pass
    return False




def forbered_og_start_jobb(
    innhold: bytes,
    filnavn: str,
    language: str,
    modell: str,
    kjerner: int,
    fil_str_mb: float,
    background_tasks: BackgroundTasks
) -> str:
    """
    Genererer en unik jobb-ID, lagrer opplastingen midlertidig,
    registrerer jobben i minnet og delegerer prosesseringen til en bakgrunnstråd.
    Returnerer den unike jobb-IDen.
    """
    jobb_id = str(uuid.uuid4())
    temp_inn_sti = f"temp_{jobb_id}_{filnavn}"

    with open(temp_inn_sti, "wb") as f:
        f.write(innhold)

    jobber[jobb_id] = {"status": "jobber"}
    background_tasks.add_task(
        prosesser_lyd_i_bakgrunn,
        jobb_id,
        temp_inn_sti,
        filnavn,
        language,
        modell,
        kjerner,
        fil_str_mb
    )
    return jobb_id




def hent_jobb(jobb_id: str) -> dict:
    """
    Slår opp og returnerer status og eventuelt resultat for en spesifikk jobb-ID.
    Returnerer None hvis jobben ikke finnes i minnet.
    """
    return jobber.get(jobb_id)





def lagre_transkripsjon_i_db(
        filnavn: str,
        sprak: str,
        tekst: str,
        brukt_tid: float,
        modell: str,
        kjerner: int,
        fil_str_mb: float,
        lengde_sekunder: float
):
    """
    Oppretter en ny databasetilkobling, lagrer den ferdige transkripsjonen,
    og sørger for at tilkoblingen lukkes trygt uansett utfall.
    """

    db = SessionLocal()
    try:
        ny_post = Transkripsjon(
            filnavn=filnavn,
            sprak=sprak,
            tekst=tekst,
            tid_brukt_sek=brukt_tid,
            modell=modell,
            kjerner=kjerner,
            fil_str_mb=fil_str_mb,
            lengde_sekunder=lengde_sekunder
        )
        db.add(ny_post)
        db.commit()
    finally:
        db.close()





def konverter_til_wav(input_sti: str, output_sti: str):
    """
    Kaller FFmpeg som en underprosess for å tvinge lydfilen over til
    16kHz, 16-bit mono WAV, uavhengig av opprinnelig format.
    """
    kommando = [
        "ffmpeg", "-y", "-i", input_sti, "-ar", "16000",
        "-ac", "1", "-c:a", "pcm_s16le", output_sti
    ]
    subprocess.run(kommando, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)





async def avslutt_server_etter_inaktivitet():
    """Venter i 2 minutter. Hvis ingen ny jobb har startet, drepes whisper-server."""
    await asyncio.sleep(120)

    if time.time() - siste_jobb_tid >= 115 and not telefon_lock.locked():
        print("[Auto-opprydding] Inaktivitet oppdaget. Skrur av whisper-server på telefonen.")
        try:
            ssh_cmd = ["ssh", "-o", "ConnectTimeout=5", "oneplus", "pkill whisper-server"]
            await asyncio.create_subprocess_exec(*ssh_cmd, stdout=asyncio.subprocess.DEVNULL,
                                                 stderr=asyncio.subprocess.DEVNULL)
        except Exception as e:
            print(f"[Auto-opprydding] Klarte ikke drepe server: {e}")


async def vekk_telefon_og_start_server(jobb_id: str, modell: str, kjerner: int):
    """
    Starter strøm via USB for å vekke telefonen og nettverket.
    Sjekker om riktig modell allerede kjører for å spare tid.
    Holder SSH-forbindelsen åpen i bakgrunnen og bruker smart-venting
    for å starte transkriberingen umiddelbart når modellen er lastet i RAM.
    """
    global aktiv_ssh_prosess, gjeldende_modell

    if await sjekk_server_status() and gjeldende_modell == modell:
        jobber[jobb_id] = {"status": "jobber",
                           "melding": f"AI-modellen ({modell}) kjører allerede. Sender filen rett over!"}
        return

    jobber[jobb_id] = {"status": "jobber", "melding": "Sjekker strøm og vekker telefonen..."}

    proc_start = await asyncio.create_subprocess_exec("./start-oneplus.sh", stdout=asyncio.subprocess.PIPE,
                                                      stderr=asyncio.subprocess.PIPE)
    await proc_start.communicate()
    await asyncio.sleep(1.5)

    jobber[jobb_id] = {"status": "jobber",
                       "melding": f"Starter AI-server (Modell: {modell}, Kjerner: {kjerner})..."}
    modell_sti = f"/data/whisper.cpp/models/nb-{modell}-q5_0.bin"

    pkill_cmd = ["ssh", "-o", "ConnectTimeout=5", "oneplus", "pkill whisper-server"]
    proc_pkill = await asyncio.create_subprocess_exec(*pkill_cmd)
    await proc_pkill.communicate()
    await asyncio.sleep(0.5)

    ssh_start = [
        "ssh", "-o", "ConnectTimeout=5", "oneplus",
        f"cd /data/whisper.cpp && ./build/bin/whisper-server -m {modell_sti} -t {kjerner} --host 0.0.0.0 --port 8080 > server.log 2>&1"
    ]

    aktiv_ssh_prosess = await asyncio.create_subprocess_exec(*ssh_start)

    jobber[jobb_id]["melding"] = f"Laster AI-modellen ({modell}) inn i RAM..."

    for _ in range(40):
        if await sjekk_server_status():
            gjeldende_modell = modell
            break
        await asyncio.sleep(0.5)




'''
async def vekk_telefon_og_start_server(jobb_id: str, modell: str, kjerner: int):
    """Håndterer strøm, nettverk og oppstart av Whisper via SSH."""
    jobber[jobb_id] = {"status": "jobber", "melding": "Skrur på strøm til telefonen og vekker nettverket..."}

    proc_start = await asyncio.create_subprocess_exec("./start-oneplus.sh", stdout=asyncio.subprocess.PIPE,
                                                      stderr=asyncio.subprocess.PIPE)
    await proc_start.communicate()
    await asyncio.sleep(3)

    jobber[jobb_id] = {"status": "jobber",
                       "melding": f"Starter AI-server på telefonen (Modell: {modell}, Kjerner: {kjerner}). Dette tar litt tid..."}
    modell_sti = f"/data/whisper.cpp/models/nb-{modell}-q5_0.bin"

    ssh_start = [
        "ssh", "-o", "ConnectTimeout=5", "oneplus",
        f"pkill whisper-server; cd /data/whisper.cpp && setsid ./build/bin/whisper-server -m {modell_sti} -t {kjerner} --host 0.0.0.0 --port 8080 > server.log 2>&1 < /dev/null &"
    ]

    proc_ssh = await asyncio.create_subprocess_exec(*ssh_start)

    await proc_ssh.communicate()

    await asyncio.sleep(15)
'''





async def send_lyd_til_whisper(jobb_id: str, wav_sti: str, language: str):
    """Sender den ferdige WAV-filen til Whisper API-et og returnerer responsen og tidsbruken."""
    jobber[jobb_id] = {"status": "jobber", "melding": "Transkriberer teksten! Sitter og venter på svar..."}

    with open(wav_sti, "rb") as f:
        wav_data = f.read()

    files_payload = {'file': ("lyd.wav", wav_data, "audio/wav")}
    data_payload = {'language': language}

    timeout = httpx.Timeout(3600.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        start_tid = time.time()
        response = await client.post(WHISPER_URL, files=files_payload, data=data_payload)
        slutt_tid = time.time()

    brukt_tid = round(slutt_tid - start_tid, 2)
    return response, brukt_tid





async def prosesser_lyd_i_bakgrunn(jobb_id: str, temp_inn_sti: str, filnavn: str, language: str, modell: str,
                                   kjerner: int, fil_str_mb: float):
    global siste_jobb_tid
    temp_ut_sti = temp_inn_sti + ".wav"

    try:
        async with telefon_lock:
            await vekk_telefon_og_start_server(jobb_id, modell, kjerner)

            jobber[jobb_id]["melding"] = "Konverterer lydfilen for AI-en..."
            lengde_sekunder = round(hent_lydlengde_sekunder(temp_inn_sti), 2)
            konverter_til_wav(temp_inn_sti, temp_ut_sti)

            response, brukt_tid = await send_lyd_til_whisper(jobb_id, temp_ut_sti, language)

            if response.status_code == 200:
                transkribert_tekst = response.json().get("text", "")
                lagre_transkripsjon_i_db(filnavn, language, transkribert_tekst, brukt_tid, modell, kjerner, fil_str_mb,
                                         lengde_sekunder)
                jobber[jobb_id] = {"status": "ferdig", "tekst": transkribert_tekst, "tid_brukt": brukt_tid}
            else:
                jobber[jobb_id] = {"status": "feil", "melding": f"AI-server svarte med kode {response.status_code}"}

    except Exception as e:
        jobber[jobb_id] = {"status": "feil", "melding": f"Feil under prosessering: {str(e)}"}

    finally:
        siste_jobb_tid = time.time()
        asyncio.create_task(avslutt_server_etter_inaktivitet())

        if os.path.exists(temp_inn_sti):
            os.remove(temp_inn_sti)
        if os.path.exists(temp_ut_sti):
            os.remove(temp_ut_sti)





def hent_lydlengde_sekunder(fil_sti: str) -> float:
    """
    Bruker ffprobe til å hente nøyaktig varighet på lydfilen i sekunder.
    Returnerer 0.0 hvis den ikke klarer å lese den.
    """
    try:
        cmd = [
            "ffprobe", "-v", "quiet", "-print_format", "json",
            "-show_format", fil_sti
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
        return float(data['format']['duration'])
    except Exception:
        return 0.0




async def sjekk_og_styr_batteri():
    """
    Bakgrunnsoppgave som kjører periodisk for å holde batteriet
    mellom 30% og 70% når enheten står plugget i.
    Respekterer lade_stopp.lock for manuell overstyring (f.eks. før ferie).
    """
    while True:
        try:
            if os.path.exists(TILSTANDS_FIL):
                with open(TILSTANDS_FIL, "r") as f:
                    innhold = f.read().strip().lower()
                    if innhold == "false":
                        await asyncio.sleep(900)  # Vent 15 min og sjekk igjen
                        continue

            subprocess.run(["./start-oneplus.sh"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            await asyncio.sleep(5)

            ssh_cmd = ["ssh", "-o", "ConnectTimeout=5", "oneplus", "cat /sys/class/power_supply/bq27541-0/capacity"]
            res = subprocess.run(ssh_cmd, capture_output=True, text=True)

            if res.returncode == 0 and res.stdout.strip().isdigit():
                prosent = int(res.stdout.strip())

                if prosent >= 70 and not er_server_opptatt():
                    subprocess.run(["sudo", "uhubctl", "-l", "1-2", "-p", "1", "-a", "off"], stdout=subprocess.DEVNULL)

                elif prosent <= 30:
                    subprocess.run(["sudo", "uhubctl", "-l", "1-2", "-p", "1", "-a", "on"], stdout=subprocess.DEVNULL)

        except Exception as e:
            pass

        # Sjekk hver 30. minutt
        await asyncio.sleep(1800)




def er_server_opptatt() -> bool:
    """Sjekker om telefon-låsen er i bruk av en annen prosess."""
    return telefon_lock.locked()