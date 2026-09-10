"""Motor de base de datos, sesión y Base declarativa de SQLAlchemy.

El esquema real (tablas, tipos, constraints) vive en `backend/schema.sql`
y se aplica manualmente con `psql` — este módulo solo abre la conexión
y define el mapeo ORM, nunca crea ni migra tablas (sin Alembic).
"""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from backend.config import get_settings

engine = create_engine(get_settings().database_url, pool_pre_ping=True)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    """Dependencia de FastAPI: entrega una sesión por request y la cierra siempre."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
