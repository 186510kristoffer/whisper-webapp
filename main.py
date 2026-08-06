from fastapi import FastAPI, UploadFile, File, Request, Form, Depends
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import httpx
import asyncio
import os
import tempfile
import subprocess
from sqlalchemy.orm import Session
from database import init_db, SessionLocal, Transkripsjon
from dotenv import load_dotenv


app = FastAPI()

load_dotenv()

app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory= "templates")

WHISPER_URL = os.getenv("WHISPER_URL", "http://127.0.0.1:8080/inference")

telefon_lock = asyncio.Lock()

@app.on_event("startup")
def startup_event():
    init_db()

def get_db():
    db=SessionLocal()
    try:
        yield db
    finally:
        db.close()

def konverter_til_wav(input_sti: str, output_sti:str):
    """
    Kaller FFmpeg for å tvinge lyden over i 16kHz, 16-bit mono WAV.
    Kreves av whisper.cpp.
    """
    kommando = [ "ffmpeg",
                 "-y",                      # Overskriv output-filen hvis den allerede finnes
                 "-i", input_sti,           # Filen brukeren lastet opp
                 "-ar", "16000",            # Tving sample rate til 16 kHz
                 "-ac", "1",                # Tving mono (1 lydkanal)
                 "-c:a", "pcm_s16le",       # Tving 16-bit lydformat
                 output_sti                 # Den ferdige WAV-filen
    ]

    subprocess.run(kommando, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
@app.get("/", response_class=HTMLResponse)
async def hjemmeside(request: Request):
    """
    Laster inn selve nettsiden når du går til adressen i nettleseren.
    Tilsvarende @GetMapping fra java spring controller
    """
    return templates.TemplateResponse(request=request, name="index.html")

@app.post("/transkriber")
async def transkriber_lyd(
        file: UploadFile = File(...),
        language: str = Form("no"),
        db: Session = Depends(get_db)
):
    """
    Dette endepunktet tar imot lydfilen fra nettsiden,
    og sender den umiddelbart videre til whipser serveren
    """

    with tempfile.NamedTemporaryFile(delete=False) as temp_inn:
        temp_inn.write(await file.read())
        temp_inn_sti = temp_inn.name

    temp_ut_sti = temp_inn_sti+".wav"

    try:
        konverter_til_wav(temp_inn_sti, temp_ut_sti)

        with open(temp_ut_sti, "rb") as f:
            wav_data = f.read()

        files = {'file': ("lyd.wav", wav_data, "audio/wav")}

        data = {'language': language}

        async with telefon_lock:
            async with httpx.AsyncClient(timeout=300.0) as client:

                response = await client.post(WHISPER_URL, files=files, data=data)
                response.raise_for_status()
                response_json = response.json()

                transkribert_tekst = response_json.get("text", str(response_json))

                ny_post = Transkripsjon(sprak=language, tekst=transkribert_tekst)
                db.add(ny_post)
                db.commit()
                db.refresh(ny_post)

                return response_json

    except Exception as e:
        return {"error": f"Konvertering eller sending feilet: {str(e)}"}

    finally:
        if os.path.exists(temp_inn_sti):
            os.remove(temp_inn_sti)
        if os.path.exists(temp_ut_sti):
            os.remove(temp_ut_sti)

@app.get("/historikk")
async def hent_historikk(db: Session = Depends(get_db)):
    poster = db.query(Transkripsjon).order_by(Transkripsjon.tidspunkt.desc()).all()
    return poster
