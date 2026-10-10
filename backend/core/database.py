import re
import uuid
from typing import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session, DeclarativeBase

from .config import settings


# ── Declarative bases ──────────────────────────────────────────────────────────

class GlobalBase(DeclarativeBase):
    pass


class TenantBase(DeclarativeBase):
    pass


# ── Global DB ──────────────────────────────────────────────────────────────────

_global_engine = create_engine(settings.global_db_url, pool_pre_ping=True)
_GlobalSession = sessionmaker(autocommit=False, autoflush=False, bind=_global_engine)


def get_global_db() -> Generator[Session, None, None]:
    db = _GlobalSession()
    try:
        yield db
    finally:
        db.close()


def init_global_db() -> None:
    GlobalBase.metadata.create_all(bind=_global_engine)


# ── Tenant DB (per-hospital) ────────────────────────────────────────────────────

_tenant_engines: dict = {}


def _get_tenant_engine(db_name: str):
    if db_name not in _tenant_engines:
        engine = create_engine(
            settings.tenant_db_url(db_name),
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=10,
        )
        _tenant_engines[db_name] = engine
    return _tenant_engines[db_name]


def get_tenant_db(db_name: str) -> Generator[Session, None, None]:
    engine = _get_tenant_engine(db_name)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = Session()
    try:
        yield db
    finally:
        db.close()


# ── Hospital database provisioning ────────────────────────────────────────────

def generate_db_name(hospital_name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", hospital_name.lower()).strip("_")[:30]
    short_id = uuid.uuid4().hex[:8]
    return f"medical_{slug}_{short_id}"


def create_hospital_database(db_name: str) -> None:
    """Create a new PostgreSQL database for a hospital. Requires autocommit."""
    engine = create_engine(settings.global_db_url, isolation_level="AUTOCOMMIT")
    with engine.connect() as conn:
        exists = conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname = :name"),
            {"name": db_name},
        ).fetchone()
        if not exists:
            conn.execute(text(f'CREATE DATABASE "{db_name}"'))
    engine.dispose()


def provision_tenant_schema(db_name: str) -> None:
    """Create all tenant tables in the newly created hospital database."""
    from models.tenant_models import TenantBase  # late import avoids circular deps
    engine = _get_tenant_engine(db_name)
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.commit()
    TenantBase.metadata.create_all(bind=engine)


def drop_hospital_database(db_name: str) -> None:
    """Drop a hospital database. Used during offboarding after data export."""
    engine = create_engine(settings.global_db_url, isolation_level="AUTOCOMMIT")
    with engine.connect() as conn:
        # Terminate active connections before dropping
        conn.execute(
            text(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                "WHERE datname = :name AND pid <> pg_backend_pid()"
            ),
            {"name": db_name},
        )
        conn.execute(text(f'DROP DATABASE IF EXISTS "{db_name}"'))
    engine.dispose()
    _tenant_engines.pop(db_name, None)
