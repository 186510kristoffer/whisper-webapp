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
from services import prosesser_lyd_i_bakgrunn, sjekk_server_status, hent_jobb, forbered_og_start_jobb

load_dotenv()


MAX_FILESIZE = 50 * 1024 * 1024
TILLATTE_TYPER = ["audio/mpeg", "audio/wav", "audio/mp3", "audio/ogg", "audio/x-m4a", "video/mp4"]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Kjøres én gang når serveren starter opp.
    Initialiserer databasen og gjør alt klart før vi tar imot trafikk.
    """
    init_db()
    yield

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
):
    """
    Validerer innkommende HTTP-forespørsel (størrelse/type),
    og delegerer filhåndteringen og jobben til service-laget.
    """
    if file.content_type not in TILLATTE_TYPER:
        raise HTTPException(status_code=400, detail="Ugyldig filtype.")

    innhold = await file.read()
    if len(innhold) > MAX_FILESIZE:
        raise HTTPException(status_code=413, detail="Filen er for stor, max 50MB.")

    jobb_id = forbered_og_start_jobb(innhold, file.filename, language, background_tasks)

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


@app.get("/historikk")
async def hent_historikk(db: Session = Depends(get_db)):
    """
    Henter ut en liste over alle tidligere transkripsjoner fra databasen, 
    sortert med den nyeste først.
    """
    return db.query(Transkripsjon).order_by(Transkripsjon.tidspunkt.desc()).all()