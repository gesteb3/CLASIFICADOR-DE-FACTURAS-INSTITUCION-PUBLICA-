import time
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.core.config import get_settings

settings = get_settings()

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    future=True,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    future=True,
)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def wait_for_database(max_attempts: int = 30, delay_seconds: int = 2) -> None:
    for attempt in range(1, max_attempts + 1):
        try:
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            print("Base de datos conectada correctamente.")
            return
        except Exception as exc:
            print(f"Esperando PostgreSQL... intento {attempt}/{max_attempts}. Error: {exc}")
            time.sleep(delay_seconds)

    raise RuntimeError("No se pudo conectar a PostgreSQL.")
