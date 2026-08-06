from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import datetime

# Dette lager en lokal fil som heter 'transkripsjoner.db' helt automatisk
SQLALCHEMY_DATABASE_URL = "sqlite:///./transkripsjoner.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Tabell-strukturen (tilsvarende en @Entity i Java)
class Transkripsjon(Base):
    __tablename__ = "transkripsjoner"

    id = Column(Integer, primary_key=True, index=True)
    tidspunkt = Column(DateTime, default=datetime.datetime.utcnow)
    sprak = Column(String(10))
    tekst = Column(Text)

# Oppretter tabellen i databasetabellen hvis den ikke finnes fra før
def init_db():
    Base.metadata.create_all(bind=engine)