
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from app.core.config import get_settings
settings = get_settings()

def _get_async_database_url() -> str:
  database_url = settings.database_url
  if database_url.startswith("postgresql://"):
    return database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
  if database_url.startswith("postgresql+psycopg2://"):
    return database_url.replace("postgresql+psycopg2://", "postgresql+asyncpg://", 1)
  if database_url.startswith("postgres://"):
    return database_url.replace("postgres://", "postgresql+asyncpg://", 1)
  if "+asyncpg" in database_url:
    return database_url
  return database_url


engine = create_async_engine(
  _get_async_database_url(),
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    echo=False,  
)
AsyncSessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
  pass


async def get_db():
  async with AsyncSessionLocal() as db:
    yield db


async def init_db():
  async with engine.begin() as conn:
    await conn.run_sync(Base.metadata.create_all)
