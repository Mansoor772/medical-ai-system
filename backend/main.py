from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.database import init_global_db
from routers import auth, hospitals, admin, doctors, patients, knowledge, diagnosis, lab, chatbot, compliance


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_global_db()
    _migrate_all_tenant_dbs()
    yield


def _migrate_all_tenant_dbs():
    """Ensure all existing hospital DBs have the latest tenant schema."""
    from core.database import get_global_db, provision_tenant_schema
    from models.global_models import Hospital
    db = next(get_global_db())
    try:
        hospitals = db.query(Hospital).filter(Hospital.is_active == True).all()
        for hospital in hospitals:
            provision_tenant_schema(hospital.db_name)
    finally:
        db.close()


app = FastAPI(
    title="Medical AI System",
    version="1.0.0",
    description="AI-assisted medical diagnosis and records system",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(hospitals.router)
app.include_router(admin.router)
app.include_router(doctors.router)
app.include_router(patients.router)
app.include_router(knowledge.router)
app.include_router(diagnosis.router)
app.include_router(lab.router)
app.include_router(chatbot.router)
app.include_router(compliance.router)


@app.get("/health")
def health():
    return {"status": "ok", "service": "Medical AI System"}
