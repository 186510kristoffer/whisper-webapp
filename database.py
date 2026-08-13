import os
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import datetime
from dotenv import load_dotenv

load_dotenv()

SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./transkripsjoner.db")

if SQLALCHEMY_DATABASE_URL.startswith("sqlite"):
    engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(SQLALCHEMY_DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Transkripsjon(Base):
    __tablename__ = "transkripsjoner"

    id = Column(Integer, primary_key=True, index=True)
    tidspunkt = Column(DateTime, default=datetime.datetime.utcnow)
    sprak = Column(String(10))
    tekst = Column(Text)
    tid_brukt_sek = Column(Float)

def init_db():
    Base.metadata.create_all(bind=engine)