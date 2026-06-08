from pydantic import BaseModel
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.classification_service import (
    classify_item,
    load_budget_line_descriptions,
    preview_classification_candidates,
)

router = APIRouter(prefix="/classification", tags=["Classification"])


class ClassificationRequest(BaseModel):
    descripcion: str
    tipo: str | None = None


@router.get("/debug-descriptions")
def debug_descriptions():
    descriptions = load_budget_line_descriptions()

    return {
        "total_descripciones": len(descriptions),
        "tiene_112": "112" in descriptions,
        "tiene_268": "268" in descriptions,
        "tiene_299": "299" in descriptions,
        "descripcion_268": descriptions.get("268"),
    }


@router.post("/candidates")
def get_candidates(
    payload: ClassificationRequest,
    db: Session = Depends(get_db),
):
    return {
        "descripcion": payload.descripcion,
        "tipo": payload.tipo,
        "candidatos": preview_classification_candidates(
            db,
            payload.descripcion,
            payload.tipo,
        ),
    }


@router.post("/test")
def test_classification(
    payload: ClassificationRequest,
    db: Session = Depends(get_db),
):
    candidates = preview_classification_candidates(
        db,
        payload.descripcion,
        payload.tipo,
    )

    budget_line, confidence, origin = classify_item(
        db,
        payload.descripcion,
        payload.tipo,
    )

    if not budget_line:
        return {
            "descripcion": payload.descripcion,
            "tipo": payload.tipo,
            "renglon": None,
            "concepto": None,
            "confianza": None,
            "origen": None,
            "candidatos_usados": candidates,
            "mensaje": "No se pudo clasificar.",
        }

    return {
        "descripcion": payload.descripcion,
        "tipo": payload.tipo,
        "renglon": budget_line.renglon,
        "concepto": budget_line.concepto,
        "confianza": float(confidence) if confidence is not None else None,
        "origen": origin,
        "candidatos_usados": candidates,
    }