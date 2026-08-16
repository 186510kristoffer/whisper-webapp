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


async def prosesser_lyd_i_bakgrunn(
    jobb_id: str,
    temp_inn_sti: str,
    language: str,
    modell: str,
    kjerner: int,
    fil_str_mb: float
):
    """
    Orkestrerer hele transkriberingsflyten: Konverterer lyd, låser ressurstilgang,
    sender data til AI-serveren, lagrer i databasen og rydder opp filer etterpå.
    Oppdaterer status i den globale jobber-ordboken underveis.
    """
    temp_ut_sti = temp_inn_sti + ".wav"

    try:
        proc = await asyncio.create_subprocess_exec(
            "./start-oneplus.sh",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        await proc.communicate()
        await asyncio.sleep(3)

        konverter_til_wav(temp_inn_sti, temp_ut_sti)

        lengde_sekunder = round(hent_lydlengde_sekunder(temp_inn_sti), 2)

        with open(temp_ut_sti, "rb") as f:
            wav_data = f.read()

        files_payload = {'file': ("lyd.wav", wav_data, "audio/wav")}
        data_payload = {'language': language}

        async with telefon_lock:
            timeout = httpx.Timeout(3600.0)
            async with httpx.AsyncClient(timeout=timeout) as client:
                start_tid = time.time()
                response = await client.post(WHISPER_URL, files=files_payload, data=data_payload)
                slutt_tid = time.time()
                brukt_tid = round(slutt_tid - start_tid, 2)

        if response.status_code == 200:
            transkribert_tekst = response.json().get("text", "")
            lagre_transkripsjon_i_db(
                filnavn="lydfil",  # eller ekte filnavn om du send അത് inn
                sprak=language,
                tekst=transkribert_tekst,
                brukt_tid=brukt_tid,
                modell=modell,
                kjerner=kjerner,
                fil_str_mb=fil_str_mb,
                lengde_sekunder=lengde_sekunder
            )
            jobber[jobb_id] = {"status": "ferdig", "tekst": transkribert_tekst, "tid_brukt": brukt_tid}
        else:
            jobber[jobb_id] = {"status": "feil", "melding": f"AI-server svarte med kode {response.status_code}"}

    except Exception as e:
        jobber[jobb_id] = {"status": "feil", "melding": f"Feil: {str(e)}"}

    finally:
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

            ssh_cmd = ["ssh", "-o", "ConnectTimeout=5", "root@172.16.42.1", "cat /sys/class/power_supply/bq27541-0/capacity"]
            res = subprocess.run(ssh_cmd, capture_output=True, text=True)

            if res.returncode == 0 and res.stdout.strip().isdigit():
                prosent = int(res.stdout.strip())

                if prosent >= 70:
                    subprocess.run(["sudo", "uhubctl", "-l", "1-2", "-p", "1", "-a", "off"], stdout=subprocess.DEVNULL)

                elif prosent <= 30:
                    subprocess.run(["sudo", "uhubctl", "-l", "1-2", "-p", "1", "-a", "on"], stdout=subprocess.DEVNULL)

        except Exception as e:
            pass

        # Sjekk hver 30. minutt
        await asyncio.sleep(1800)