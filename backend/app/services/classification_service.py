import csv
import json
import re
import unicodedata
from decimal import Decimal
from pathlib import Path

import httpx
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import BudgetLine, ClassificationRule

settings = get_settings()


STOPWORDS = {
    "de", "del", "la", "las", "el", "los", "un", "una", "unos", "unas",
    "para", "por", "con", "sin", "en", "a", "al", "y", "o", "u",
    "que", "se", "su", "sus", "es", "son", "como", "tipo", "marca",
    "unidad", "unidades", "bolsa", "bolsas", "metro", "metros",
    "servicio", "servicios", "producto", "productos", "compra",
    "adquisicion", "adquisición", "suministro", "suministros",
}


def normalize_text(value: str | None) -> str:
    if not value:
        return ""

    value = value.lower().strip()
    value = unicodedata.normalize("NFD", value)
    value = "".join(char for char in value if unicodedata.category(char) != "Mn")
    value = re.sub(r"[^a-z0-9\s]", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def tokenize(value: str | None) -> list[str]:
    normalized = normalize_text(value)
    tokens = []

    for token in normalized.split():
        if len(token) < 3:
            continue

        if token in STOPWORDS:
            continue

        tokens.append(token)

    return tokens


def load_budget_line_descriptions() -> dict[str, str]:
    descriptions_path = Path("/app/database/catalogos/descripciones_renglones.csv")

    if not descriptions_path.exists():
        return {}

    descriptions: dict[str, str] = {}

    try:
        with descriptions_path.open("r", encoding="utf-8-sig", newline="") as file:
            reader = csv.DictReader(file)

            for row in reader:
                renglon = str(row.get("renglon", "")).strip()
                descripcion = str(row.get("descripcion", "")).strip()

                if renglon and descripcion:
                    descriptions[renglon] = descripcion

    except Exception as exc:
        print(f"No se pudieron cargar descripciones_renglones.csv: {exc}")

    return descriptions


def get_all_active_budget_lines(db: Session) -> list[BudgetLine]:
    return (
        db.query(BudgetLine)
        .filter(BudgetLine.activo.is_(True))
        .order_by(BudgetLine.renglon.asc())
        .all()
    )


def get_budget_line_by_code(
    db: Session,
    renglon: str | int | None,
) -> BudgetLine | None:
    if renglon is None:
        return None

    clean_renglon = str(renglon).strip()

    if not clean_renglon:
        return None

    return (
        db.query(BudgetLine)
        .filter(BudgetLine.renglon == clean_renglon)
        .filter(BudgetLine.activo.is_(True))
        .first()
    )


def get_line_text(line: BudgetLine, extra_description: str | None = None) -> str:
    return f"{line.renglon} {line.concepto} {extra_description or ''}"


def token_similarity_score(
    description: str,
    line: BudgetLine,
    extra_description: str | None = None,
) -> int:
    description_tokens = tokenize(description)
    line_text = normalize_text(get_line_text(line, extra_description))
    line_tokens = set(tokenize(line_text))

    if not description_tokens:
        return 0

    score = 0

    for token in description_tokens:
        if token in line_tokens:
            score += 12
        elif token in line_text:
            score += 6
        else:
            for line_token in line_tokens:
                if token in line_token or line_token in token:
                    score += 3
                    break

    concept_tokens = set(tokenize(line.concepto))

    for token in description_tokens:
        if token in concept_tokens:
            score += 8

    return score


def type_group_score(tipo: str | None, line: BudgetLine) -> int:
    normalized_tipo = normalize_text(tipo)
    renglon = str(line.renglon)

    if normalized_tipo == "bien":
        if renglon.startswith("2"):
            return 8

        if renglon.startswith("3"):
            return 6

        if renglon.startswith("1"):
            return -5

    if normalized_tipo == "servicio":
        if renglon.startswith("1"):
            return 8

        if renglon.startswith("2"):
            return -4

        if renglon.startswith("3"):
            return -4

    return 0


def get_candidate_budget_lines(
    db: Session,
    description: str,
    tipo: str | None = None,
    limit: int = 15,
) -> list[BudgetLine]:
    descriptions = load_budget_line_descriptions()
    budget_lines = get_all_active_budget_lines(db)

    scored_candidates: list[tuple[int, BudgetLine]] = []

    for line in budget_lines:
        extra_description = descriptions.get(line.renglon)

        score = token_similarity_score(
            description=description,
            line=line,
            extra_description=extra_description,
        )

        score += type_group_score(tipo, line)

        if score > 0:
            scored_candidates.append((score, line))

    scored_candidates.sort(
        key=lambda item: (item[0], item[1].renglon),
        reverse=True,
    )

    candidates = [line for _, line in scored_candidates[:limit]]

    if candidates:
        return candidates

    normalized_tipo = normalize_text(tipo)

    fallback_codes = []

    if normalized_tipo == "bien":
        fallback_codes = ["299", "298", "289", "279"]
    elif normalized_tipo == "servicio":
        fallback_codes = ["199", "189", "142", "141"]
    else:
        fallback_codes = ["299", "199"]

    fallback_candidates = []

    for code in fallback_codes:
        line = get_budget_line_by_code(db, code)

        if line:
            fallback_candidates.append(line)

    return fallback_candidates[:limit]


def build_budget_lines_text_from_candidates(candidates: list[BudgetLine]) -> str:
    descriptions = load_budget_line_descriptions()
    lines: list[str] = []

    for line in candidates:
        extra_description = descriptions.get(line.renglon)

        if extra_description:
            lines.append(
                f"{line.renglon} - {line.concepto}\n"
                f"Descripción del renglón: {extra_description}"
            )
        else:
            lines.append(f"{line.renglon} - {line.concepto}")

    return "\n\n".join(lines)


def parse_ollama_json(raw_answer: str) -> dict | None:
    if not raw_answer:
        return None

    match = re.search(r"\{.*\}", raw_answer, re.DOTALL)

    if not match:
        return None

    try:
        return json.loads(match.group(0))
    except Exception:
        return None


def normalize_confidence(value: object) -> Decimal:
    try:
        confidence = Decimal(str(value))
    except Exception:
        confidence = Decimal("60")

    if confidence < 1:
        confidence = Decimal("1")

    if confidence > 100:
        confidence = Decimal("100")

    return confidence


def classify_by_ollama(
    db: Session,
    description: str,
    tipo: str | None = None,
) -> tuple[BudgetLine | None, Decimal | None, str | None]:
    candidates = get_candidate_budget_lines(
        db=db,
        description=description,
        tipo=tipo,
        limit=15,
    )

    if not candidates:
        print("No se encontraron candidatos para enviar a la IA.")
        return None, None, None

    budget_lines_text = build_budget_lines_text_from_candidates(candidates)

    prompt = f"""
Eres un asistente experto en clasificación presupuestaria del sector público de Guatemala.

Tu tarea es clasificar UNA línea de factura en UN SOLO renglón presupuestario.

Debes decidir usando únicamente los renglones candidatos que se te proporcionan.
No inventes códigos.
No uses códigos que no estén en la lista de candidatos.
No respondas texto fuera del JSON.
No expliques fuera del JSON.

Criterios de decisión:
1. Lee la descripción de la factura.
2. Lee el tipo de línea: Bien o Servicio.
3. Lee el concepto y la descripción de cada renglón candidato.
4. Elige el renglón que mejor coincida con la naturaleza del gasto.
5. Si es un bien físico o consumible, normalmente corresponde a materiales, suministros, productos o equipo.
6. Si es una prestación contratada, traslado, mantenimiento, reparación, asesoría, capacitación u otro trabajo realizado por terceros, normalmente corresponde a servicios.
7. Si hay renglones parecidos, decide usando la descripción del renglón.
8. Si no estás totalmente seguro, elige el candidato más cercano y usa confianza baja.
9. La confianza debe ser un número entero de 1 a 100.

Línea de factura:
Descripción: {description}
Tipo: {tipo or "No especificado"}

Renglones candidatos permitidos:
{budget_lines_text}

Formato obligatorio:
{{
  "renglon": "000",
  "confianza": 80,
  "razon_breve": "Motivo breve de la elección."
}}
"""

    try:
        response = httpx.post(
            f"{settings.ollama_host}/api/generate",
            json={
                "model": settings.ollama_model,
                "prompt": prompt,
                "stream": False,
                "format": "json",
                "options": {
                    "temperature": 0.05,
                    "top_p": 0.75,
                    "num_predict": 100,
                },
            },
            timeout=90,
        )

        response.raise_for_status()

        data = response.json()
        raw_answer = data.get("response", "")
        parsed = parse_ollama_json(raw_answer)

        if not parsed:
            print(f"Ollama no devolvió JSON válido: {raw_answer}")
            return None, None, None

        renglon = str(parsed.get("renglon", "")).strip()
        confidence = normalize_confidence(parsed.get("confianza", 60))

        valid_codes = {line.renglon for line in candidates}

        if renglon not in valid_codes:
            print(f"Ollama devolvió un renglón fuera de candidatos: {renglon}")
            return None, None, None

        budget_line = get_budget_line_by_code(db, renglon)

        if not budget_line:
            print(f"Ollama devolvió un renglón inválido: {renglon}")
            return None, None, None

        return budget_line, confidence, "IA_LOCAL_CLASIFICADOR"

    except Exception as exc:
        print(f"No se pudo clasificar con Ollama: {exc}")
        return None, None, None


def classify_by_rules(
    db: Session,
    description: str,
) -> tuple[BudgetLine | None, Decimal | None, str | None]:
    normalized = normalize_text(description)

    if not normalized:
        return None, None, None

    rules = (
        db.query(ClassificationRule)
        .filter(ClassificationRule.activo.is_(True))
        .order_by(ClassificationRule.priority.desc())
        .all()
    )

    for rule in rules:
        keyword = normalize_text(rule.keyword)

        if keyword and keyword in normalized:
            return rule.budget_line, Decimal("95"), "REGLA"

    return None, None, None


def classify_by_similarity_fallback(
    db: Session,
    description: str,
    tipo: str | None = None,
) -> tuple[BudgetLine | None, Decimal | None, str | None]:
    candidates = get_candidate_budget_lines(
        db=db,
        description=description,
        tipo=tipo,
        limit=1,
    )

    if candidates:
        return candidates[0], Decimal("50"), "SIMILITUD_FALLBACK"

    return None, None, None


def classify_fallback(
    db: Session,
    tipo: str | None = None,
) -> tuple[BudgetLine | None, Decimal | None, str | None]:
    normalized_tipo = normalize_text(tipo)

    if normalized_tipo == "bien":
        fallback = get_budget_line_by_code(db, "299")

        if fallback:
            return fallback, Decimal("35"), "FALLBACK"

    fallback = get_budget_line_by_code(db, "199")

    if fallback:
        return fallback, Decimal("35"), "FALLBACK"

    fallback = (
        db.query(BudgetLine)
        .filter(BudgetLine.activo.is_(True))
        .order_by(BudgetLine.renglon.asc())
        .first()
    )

    if fallback:
        return fallback, Decimal("30"), "FALLBACK"

    return None, None, None


def classify_item(
    db: Session,
    description: str,
    tipo: str | None = None,
) -> tuple[BudgetLine | None, Decimal | None, str | None]:
    budget_line, confidence, origin = classify_by_ollama(db, description, tipo)

    if budget_line:
        return budget_line, confidence, origin

    budget_line, confidence, origin = classify_by_rules(db, description)

    if budget_line:
        return budget_line, confidence, origin

    budget_line, confidence, origin = classify_by_similarity_fallback(
        db,
        description,
        tipo,
    )

    if budget_line:
        return budget_line, confidence, origin

    return classify_fallback(db, tipo)


def preview_classification_candidates(
    db: Session,
    description: str,
    tipo: str | None = None,
) -> list[dict]:
    descriptions = load_budget_line_descriptions()

    candidates = get_candidate_budget_lines(
        db=db,
        description=description,
        tipo=tipo,
        limit=15,
    )

    result = []

    for candidate in candidates:
        result.append(
            {
                "renglon": candidate.renglon,
                "concepto": candidate.concepto,
                "descripcion": descriptions.get(candidate.renglon),
            }
        )

    return result