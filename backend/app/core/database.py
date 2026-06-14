
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.core.config import get_settings
settings = get_settings()
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    echo=False,  
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
  pass


def get_db():

  db = SessionLocal()
  try:
    yield db
  finally:
    db.close()


def init_db():
  Base.metadata.create_all(bind=engine)
