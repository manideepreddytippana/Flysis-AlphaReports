
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool
from app.core.config import get_settings
settings = get_settings()


engine = create_async_engine(
  settings.database_url,
  pool_pre_ping=True,
  pool_size=10,
  max_overflow=20,
  echo=False,
)
AsyncSessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

worker_engine = create_async_engine(
  settings.database_url,
  poolclass=NullPool,
  echo=False,
)
WorkerAsyncSessionLocal = async_sessionmaker(bind=worker_engine, class_=AsyncSession, expire_on_commit=False)

class Base(DeclarativeBase):
  pass

async def get_db():
  async with AsyncSessionLocal() as db:
    yield db

async def init_db():
  async with engine.begin() as conn:
    await conn.run_sync(Base.metadata.create_all)
