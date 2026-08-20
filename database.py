import os
import datetime
from zoneinfo import ZoneInfo
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()

SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./transkripsjoner.db")

if SQLALCHEMY_DATABASE_URL.startswith("sqlite"):
    engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(SQLALCHEMY_DATABASE_URL, pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def norsk_tid_na():
    """Tvinger alltid tidsstempelet til norsk tid (CET/CEST)."""
    return datetime.datetime.now(ZoneInfo("Europe/Oslo"))


class Transkripsjon(Base):
    __tablename__ = "transkripsjoner"

    id = Column(Integer, primary_key=True, index=True)
    filnavn = Column(String, nullable=False)
    tidspunkt = Column(DateTime, default=norsk_tid_na)
    lengde_sekunder = Column(Float, nullable=True)
    fil_str_mb = Column(Float, nullable=True)
    modell = Column(String, nullable=False)
    sprak = Column(String(10))
    lyd_sprak = Column(String(20), default="no")
    kjerner = Column(Integer, nullable=False)
    tekst = Column(Text)
    tid_brukt_sek = Column(Float)
    telefon_slutt_temp = Column(Float, nullable=True)
    total_tid_sek = Column(Float, nullable=True)



class Telemetri(Base):
    __tablename__ = "oneplus_telemetri"

    id = Column(Integer, primary_key=True, index=True)
    tidspunkt = Column(DateTime, default=norsk_tid_na)
    batteri_prosent = Column(Integer)
    fase = Column(String(20))
    telefon_bat_temp = Column(Float)
    telefon_cpu_temp = Column(Float)
    telefon_pmic_temp = Column(Float)


def init_db():
    Base.metadata.create_all(bind=engine)