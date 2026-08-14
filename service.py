import os
import time
import uuid
import asyncio
import subprocess
import httpx
from fastapi import BackgroundTasks
from database import SessionLocal, Transkripsjon

WHISPER_URL = os.getenv("WHISPER_URL", "http://127.0.0.1:8080/inference")
WHISPER_BASE_URL = os.getenv("WHISPER_BASE_URL", "http://127.0.0.1:8080/")

telefon_lock = asyncio.Lock()
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


def forbered_og_start_jobb(innhold: bytes, filnavn: str, language: str, background_tasks: BackgroundTasks) -> str:
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
    background_tasks.add_task(prosesser_lyd_i_bakgrunn, jobb_id, temp_inn_sti, language)

    return jobb_id


def hent_jobb(jobb_id: str) -> dict:
    """
    Slår opp og returnerer status og eventuelt resultat for en spesifikk jobb-ID.
    Returnerer None hvis jobben ikke finnes i minnet.
    """
    return jobber.get(jobb_id)


def lagre_transkripsjon_i_db(sprak: str, tekst: str, brukt_tid: float):
    """
    Oppretter en ny databasetilkobling, lagrer den ferdige transkripsjonen,
    og sørger for at tilkoblingen lukkes trygt uansett utfall.
    """
    db = SessionLocal()
    try:
        ny_post = Transkripsjon(sprak=sprak, tekst=tekst, tid_brukt_sek=brukt_tid)
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


async def prosesser_lyd_i_bakgrunn(jobb_id: str, temp_inn_sti: str, language: str):
    """
    Orkestrerer hele transkriberingsflyten: Konverterer lyd, låser ressurstilgang,
    sender data til AI-serveren, lagrer i databasen og rydder opp filer etterpå.
    Oppdaterer status i den globale jobber-ordboken underveis.
    """
    temp_ut_sti = temp_inn_sti + ".wav"

    try:
        konverter_til_wav(temp_inn_sti, temp_ut_sti)

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
            lagre_transkripsjon_i_db(language, transkribert_tekst, brukt_tid)
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