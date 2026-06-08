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
    "usar", "cuando", "solamente", "incluyendo", "similares",
    "municipalidad", "municipio", "departamento", "durante", "dias",
    "mes", "anio", "año",
}


def normalize_text(value: str | None) -> str:
    if not value:
        return ""

    value = value.lower().strip()

    replacements = {
        "p.v.c.": "pvc",
        "p.v.c": "pvc",
        "p v c": "pvc",
        "pvc.": "pvc",
        "diésel": "diesel",
        "diesél": "diesel",
        "súper": "super",
        "superior": "super",
    }

    for old, new in replacements.items():
        value = value.replace(old, new)

    value = unicodedata.normalize("NFD", value)
    value = "".join(char for char in value if unicodedata.category(char) != "Mn")
    value = re.sub(r"[^a-z0-9\s]", " ", value)
    value = re.sub(r"\bp\s+v\s+c\b", "pvc", value)

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


def get_description_file_paths() -> list[Path]:
    return [
        Path("/app/database/catalogos/descripciones_renglones.csv"),
    ]


def load_budget_line_descriptions() -> dict[str, str]:
    descriptions: dict[str, str] = {}

    descriptions_path = None

    for path in get_description_file_paths():
        if path.exists():
            descriptions_path = path
            break

    if descriptions_path is None:
        print("No se encontró descripciones_renglones.csv.")
        return descriptions

    try:
        with descriptions_path.open("r", encoding="utf-8-sig", newline="") as file:
            reader = csv.DictReader(file)

            for row in reader:
                normalized_row = {
                    normalize_text(key): value
                    for key, value in row.items()
                    if key
                }

                renglon = str(normalized_row.get("renglon", "")).strip()
                descripcion = str(
                    normalized_row.get("descripcion", "")
                    or normalized_row.get("description", "")
                ).strip()

                if renglon and descripcion:
                    descriptions[renglon] = descripcion

        print(f"Descripciones cargadas: {len(descriptions)} desde {descriptions_path}")

    except Exception as exc:
        print(f"No se pudieron cargar descripciones_renglones.csv: {exc}")

    return descriptions


def split_description_context(extra_description: str | None) -> tuple[str, str]:
    if not extra_description:
        return "", ""

    value = extra_description.strip()

    patterns = [
        "No usar para",
        "no usar para",
        "NO USAR PARA",
    ]

    for pattern in patterns:
        if pattern in value:
            positive_part, negative_part = value.split(pattern, 1)
            return positive_part.strip(), negative_part.strip()

    return value, ""


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
    positive_description, _ = split_description_context(extra_description)
    return f"{line.renglon} {line.concepto} {positive_description or ''}"


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
            score += 14
        elif token in line_text:
            score += 8
        else:
            for line_token in line_tokens:
                if token in line_token or line_token in token:
                    score += 4
                    break

    concept_tokens = set(tokenize(line.concepto))

    for token in description_tokens:
        if token in concept_tokens:
            score += 10

    return score


def exclusion_penalty(
    description: str,
    extra_description: str | None = None,
) -> int:
    _, negative_description = split_description_context(extra_description)

    if not negative_description:
        return 0

    description_tokens = set(tokenize(description))
    negative_tokens = set(tokenize(negative_description))

    if not description_tokens or not negative_tokens:
        return 0

    penalty = 0

    for token in description_tokens:
        if token in negative_tokens:
            penalty += 30
        else:
            for negative_token in negative_tokens:
                if token in negative_token or negative_token in token:
                    penalty += 18
                    break

    return penalty


def type_group_score(tipo: str | None, line: BudgetLine) -> int:
    normalized_tipo = normalize_text(tipo)
    renglon = str(line.renglon)

    if normalized_tipo == "bien":
        if renglon.startswith("2"):
            return 35

        if renglon.startswith("3"):
            return 20

        if renglon.startswith("1"):
            return -80

    if normalized_tipo == "servicio":
        if renglon.startswith("1"):
            return 40

        if renglon.startswith("2"):
            return -90

        if renglon.startswith("3"):
            return -90

    return 0


def is_generic_line(line: BudgetLine) -> bool:
    concepto = normalize_text(line.concepto)
    return concepto.startswith("otros") or concepto.startswith("otras")


def generic_penalty(line: BudgetLine) -> int:
    if is_generic_line(line):
        return 20

    return 0


def is_valid_by_tipo(tipo: str | None, line: BudgetLine) -> bool:
    normalized_tipo = normalize_text(tipo)
    renglon = str(line.renglon)

    if normalized_tipo == "servicio":
        return renglon.startswith("1")

    if normalized_tipo == "bien":
        return renglon.startswith("2") or renglon.startswith("3")

    return True


def get_candidate_budget_lines_with_scores(
    db: Session,
    description: str,
    tipo: str | None = None,
    limit: int = 8,
) -> list[tuple[int, BudgetLine]]:
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
        score -= exclusion_penalty(description, extra_description)
        score -= generic_penalty(line)

        if score > 0:
            scored_candidates.append((score, line))

    scored_candidates.sort(
        key=lambda item: (
            -item[0],
            is_generic_line(item[1]),
            item[1].renglon,
        )
    )

    normalized_tipo = normalize_text(tipo)

    if normalized_tipo in {"bien", "servicio"}:
        filtered_by_tipo = [
            item for item in scored_candidates
            if is_valid_by_tipo(tipo, item[1])
        ]

        if filtered_by_tipo:
            return filtered_by_tipo[:limit]

    return scored_candidates[:limit]


def get_candidate_budget_lines(
    db: Session,
    description: str,
    tipo: str | None = None,
    limit: int = 8,
) -> list[BudgetLine]:
    scored_candidates = get_candidate_budget_lines_with_scores(
        db=db,
        description=description,
        tipo=tipo,
        limit=limit,
    )

    candidates = [line for _, line in scored_candidates]

    if candidates:
        return candidates

    normalized_tipo = normalize_text(tipo)

    if normalized_tipo == "bien":
        fallback_codes = ["299", "298", "279"]
    elif normalized_tipo == "servicio":
        fallback_codes = ["199", "142", "141"]
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


def should_override_ai_choice(
    chosen_line: BudgetLine,
    scored_candidates: list[tuple[int, BudgetLine]],
) -> BudgetLine | None:
    if not scored_candidates:
        return None

    best_score, best_line = scored_candidates[0]

    chosen_score = None

    for score, candidate in scored_candidates:
        if candidate.renglon == chosen_line.renglon:
            chosen_score = score
            break

    if chosen_score is None:
        return best_line

    if is_generic_line(chosen_line) and not is_generic_line(best_line):
        return best_line

    if best_score >= chosen_score + 25:
        return best_line

    return None


def classify_by_ollama(
    db: Session,
    description: str,
    tipo: str | None = None,
) -> tuple[BudgetLine | None, Decimal | None, str | None]:
    scored_candidates = get_candidate_budget_lines_with_scores(
        db=db,
        description=description,
        tipo=tipo,
        limit=8,
    )

    candidates = [line for _, line in scored_candidates]

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

Reglas obligatorias:
1. Si el tipo es Servicio, elige solamente renglones de servicios, normalmente códigos 1xx.
2. Si el tipo es Bien, elige solamente renglones de materiales, suministros, bienes o equipo, normalmente códigos 2xx o 3xx.
3. Debes preferir renglones específicos sobre renglones genéricos.
4. Los renglones que empiezan con "Otros" solo deben usarse si ningún candidato específico aplica.
5. Si existe un candidato específico que coincide con la naturaleza del gasto, no elijas 199 ni 299.
6. Si la descripción tiene "traslado de personal", "transporte de personas" o "pasajeros", corresponde a transporte de personas.
7. Si la descripción tiene "flete", "traslado de bienes", "traslado de materiales" o "carga", corresponde a fletes.
8. Si la descripción tiene gasolina, super, regular, diesel, combustible, lubricante o aceite, corresponde a combustibles y lubricantes.
9. Si la descripción tiene vajilla, platos, vasos, cubiertos, ollas, sartenes o utensilios de comedor, corresponde a útiles de cocina y comedor.
10. Si no estás totalmente seguro, elige el candidato más cercano y usa confianza baja.

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
                    "temperature": 0.02,
                    "top_p": 0.70,
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

        override_line = should_override_ai_choice(
            chosen_line=budget_line,
            scored_candidates=scored_candidates,
        )

        if override_line:
            return override_line, Decimal("75"), "SIMILITUD_VALIDADA"

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
    scored_candidates = get_candidate_budget_lines_with_scores(
        db=db,
        description=description,
        tipo=tipo,
        limit=1,
    )

    if scored_candidates:
        score, candidate = scored_candidates[0]

        confidence = Decimal("50")

        if score >= 80:
            confidence = Decimal("85")
        elif score >= 55:
            confidence = Decimal("75")
        elif score >= 35:
            confidence = Decimal("60")

        return candidate, confidence, "SIMILITUD_FALLBACK"

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

    if normalized_tipo == "servicio":
        fallback = get_budget_line_by_code(db, "199")

        if fallback:
            return fallback, Decimal("35"), "FALLBACK"

    fallback = get_budget_line_by_code(db, "299")

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

    scored_candidates = get_candidate_budget_lines_with_scores(
        db=db,
        description=description,
        tipo=tipo,
        limit=8,
    )

    result = []

    for score, candidate in scored_candidates:
        result.append(
            {
                "renglon": candidate.renglon,
                "concepto": candidate.concepto,
                "descripcion": descriptions.get(candidate.renglon),
                "score": score,
            }
        )

    return result


def debug_description_loader() -> dict:
    paths = []

    for path in get_description_file_paths():
        paths.append(
            {
                "path": str(path),
                "exists": path.exists(),
            }
        )

    descriptions = load_budget_line_descriptions()

    return {
        "paths_revisadas": paths,
        "total_descripciones": len(descriptions),
        "tiene_112": "112" in descriptions,
        "tiene_141": "141" in descriptions,
        "tiene_142": "142" in descriptions,
        "tiene_211": "211" in descriptions,
        "tiene_262": "262" in descriptions,
        "tiene_268": "268" in descriptions,
        "tiene_296": "296" in descriptions,
        "tiene_299": "299" in descriptions,
        "descripcion_141": descriptions.get("141"),
        "descripcion_262": descriptions.get("262"),
        "descripcion_296": descriptions.get("296"),
    }