import json
import re
import unicodedata
from decimal import Decimal
import httpx
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import BudgetLine, ClassificationRule

settings = get_settings()


def normalize_text(value: str) -> str:
    value = value.lower().strip()
    value = unicodedata.normalize("NFD", value)
    value = "".join(char for char in value if unicodedata.category(char) != "Mn")
    value = re.sub(r"[^a-z0-9\s]", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def classify_by_rules(db: Session, description: str) -> tuple[BudgetLine | None, Decimal | None, str | None]:
    normalized = normalize_text(description)

    rules = db.query(ClassificationRule).filter(
        ClassificationRule.activo.is_(True)
    ).order_by(ClassificationRule.priority.desc()).all()

    for rule in rules:
        keyword = normalize_text(rule.keyword)
        if keyword and keyword in normalized:
            return rule.budget_line, Decimal("95.00"), "REGLA"

    return None, None, None


def classify_by_ollama(db: Session, description: str) -> tuple[BudgetLine | None, Decimal | None, str | None]:
    budget_lines = db.query(BudgetLine).filter(BudgetLine.activo.is_(True)).all()

    if not budget_lines:
        return None, None, None

    options = "\n".join(
        f"{line.renglon} - {line.concepto}"
        for line in budget_lines
    )

    prompt = f"""
Eres un clasificador presupuestario para compras pÃºblicas de Guatemala.

Debes clasificar la descripciÃ³n en UNO de los renglones disponibles.
No inventes renglones.
Responde solo JSON vÃ¡lido.

DescripciÃ³n:
{description}

Renglones disponibles:
{options}

Formato obligatorio:
{{"renglon": "141", "confianza": 80}}
"""

    try:
        response = httpx.post(
            f"{settings.ollama_host}/api/generate",
            json={
                "model": settings.ollama_model,
                "prompt": prompt,
                "stream": False,
            },
            timeout=60,
        )
        response.raise_for_status()
        data = response.json()
        raw_answer = data.get("response", "")

        json_match = re.search(r"\{.*\}", raw_answer, re.DOTALL)
        if not json_match:
            return None, None, None

        parsed = json.loads(json_match.group(0))
        renglon = str(parsed.get("renglon", "")).strip()
        confianza = Decimal(str(parsed.get("confianza", 70)))

        budget_line = db.query(BudgetLine).filter(BudgetLine.renglon == renglon).first()
        if budget_line:
            return budget_line, confianza, "IA_LOCAL"

    except Exception as exc:
        print(f"No se pudo clasificar con Ollama: {exc}")

    return None, None, None


def classify_item(db: Session, description: str) -> tuple[BudgetLine | None, Decimal | None, str | None]:
    budget_line, confidence, origin = classify_by_rules(db, description)

    if budget_line:
        return budget_line, confidence, origin

    budget_line, confidence, origin = classify_by_ollama(db, description)

    if budget_line:
        return budget_line, confidence, origin

    fallback = db.query(BudgetLine).filter(BudgetLine.renglon == "199").first()
    if fallback:
        return fallback, Decimal("50.00"), "FALLBACK"

    return None, None, None
