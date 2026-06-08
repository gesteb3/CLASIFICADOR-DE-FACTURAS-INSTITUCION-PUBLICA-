from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, SessionLocal, engine, wait_for_database
from app.models import *
from app.routes.health_routes import router as health_router
from app.routes.catalog_routes import router as catalog_router
from app.routes.invoice_routes import router as invoice_router
from app.routes.classification_routes import router as classification_router
from app.services.catalog_seed_service import seed_all_catalogs

app = FastAPI(
    title="ComprasBotGuatecompras API",
    version="0.1.0",
    description="API para procesar facturas PDF, clasificar renglones presupuestarios y preparar información para GUATECOMPRAS.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup_event():
    wait_for_database()
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        seed_all_catalogs(db)
    finally:
        db.close()


app.include_router(health_router)
app.include_router(catalog_router)
app.include_router(invoice_router)
app.include_router(classification_router)


@app.get("/")
def root():
    return {
        "message": "ComprasBotGuatecompras API funcionando",
        "docs": "/docs",
    }
