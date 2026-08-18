import os
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, UploadFile, File, Request, Form, Depends, BackgroundTasks, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from dotenv import load_dotenv
from database import init_db, SessionLocal, Transkripsjon
from services import prosesser_lyd_i_bakgrunn, sjekk_server_status, hent_jobb, forbered_og_start_jobb, \
    sjekk_og_styr_batteri
import asyncio
from services import er_server_opptatt


load_dotenv()

MAX_FILESIZE = 50 * 1024 * 1024


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Kjøres én gang når serveren starter opp.
    Initialiserer databasen og gjør alt klart før vi tar imot trafikk.
    """
    init_db()
    batteri_task = asyncio.create_task(sjekk_og_styr_batteri())
    yield
    batteri_task.cancel()

app = FastAPI(lifespan=lifespan)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")




def get_db():
    """
    Henter en aktiv database-sesjon per nettverkskall, 
    og sørger for at den lukkes pent når kallet er ferdig.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/", response_class=HTMLResponse)
async def hjemmeside(request: Request):
    """
    Laster inn og returnerer index.html
    når brukeren går til rotadressen (/).
    """
    return templates.TemplateResponse(request=request, name="index.html")




@app.get("/status")
async def sjekk_status():
    """
    Pinger whisper-serveren på telefonen for å se om den er våken.
    Returnerer "online" hvis den svarer, ellers "offline".
    """
    er_online = await sjekk_server_status()
    if er_online:
        return {"status": "online"}
    return {"status": "offline"}




@app.post("/transkriber")
async def motta_lydfil(
        background_tasks: BackgroundTasks,
        file: UploadFile = File(...),
        language: str = Form("no"),
        modell: str = Form("base"),
        kjerner: int = Form(4)
):
    """
    Validerer innkommende HTTP-forespørsel (størrelse/type),
    og delegerer filhåndteringen og jobben til service-laget.
    """
    if er_server_opptatt():
        raise HTTPException(
            status_code=429,
            detail="Serveren jobber med en annen fil akkurat nå. Vennligst vent litt og prøv igjen."
        )

    gyldige_endelser = ('.weba', '.webm', '.mp3', '.wav', '.m4a', '.mp4', '.ogg', '.flac')
    er_gyldig_mime = file.content_type.startswith("audio/") or file.content_type.startswith("video/")
    er_gyldig_endelse = file.filename.lower().endswith(gyldige_endelser)

    if not (er_gyldig_mime or er_gyldig_endelse):
        raise HTTPException(status_code=400, detail=f"Ugyldig filtype: {file.content_type} / {file.filename}")

    innhold = await file.read()
    if len(innhold) > MAX_FILESIZE:
        raise HTTPException(status_code=413, detail="Filen er for stor, max 50MB.")

    fil_str_mb = round(len(innhold) / (1024 * 1024), 2)

    jobb_id = forbered_og_start_jobb(
        innhold, file.filename, language, modell, kjerner, fil_str_mb, background_tasks)

    return {"job_id": jobb_id, "status": "jobber"}




@app.get("/jobb/{jobb_id}")
async def hent_jobbstatus(jobb_id: str):
    """
    Lar frontend-en (JavaScript) spørre om hvordan en spesifikk jobb går.
    Returnerer tekst hvis den er ferdig, eller status "jobber" / "feil".
    """
    status = hent_jobb(jobb_id)
    if not status:
        raise HTTPException(status_code=404, detail="Fant ikke jobben.")
    return status




@app.get("/historikk", response_class=HTMLResponse)
async def historikk_side(request: Request):
    """
    Serverer selve historikksiden (historikk.html).
    """
    return templates.TemplateResponse(request=request, name="historikk.html")




@app.get("/api/historikk")
async def hent_historikk_data(db: Session = Depends(get_db)):
    """
    Returnerer alle transkripsjoner som JSON for tabellen på historikksiden.
    """
    return db.query(Transkripsjon).order_by(Transkripsjon.tidspunkt.desc()).all()