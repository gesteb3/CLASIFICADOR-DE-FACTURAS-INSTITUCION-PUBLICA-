import csv
from pathlib import Path
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import Activity, BudgetLine, ClassificationRule, FundingSource, User

settings = get_settings()


def str_to_bool(value: str) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes", "si", "sí"}


def fix_text(value: str) -> str:
    if value is None:
        return value

    replacements = {
        "Ãš": "Ú",
        "Ãº": "ú",
        "Ã¡": "á",
        "Ã©": "é",
        "Ã­": "í",
        "Ã³": "ó",
        "Ã±": "ñ",
        "Ã‘": "Ñ",
        "Ã¼": "ü",
        "Â": "",
    }

    fixed = value

    for wrong, correct in replacements.items():
        fixed = fixed.replace(wrong, correct)

    return fixed.strip()


def seed_default_user(db: Session) -> None:
    existing = db.query(User).filter(User.email == "admin@local.test").first()
    if existing:
        return

    user = User(
        name="Administrador Local",
        email="admin@local.test",
        password_hash="pendiente_configurar_auth",
        role="ADMIN",
        is_active=True,
    )
    db.add(user)
    db.commit()


def seed_activities(db: Session, catalog_dir: Path) -> None:
    path = catalog_dir / "actividades.csv"
    if not path.exists():
        print("No se encontró actividades.csv")
        return

    with path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)

        for row in reader:
            code = int(row["codigo"])
            name = fix_text(row["nombre"])
            activo = str_to_bool(row.get("activo", "true"))

            existing = db.query(Activity).filter(Activity.code == code).first()

            if existing:
                existing.name = name
                existing.activo = activo
            else:
                db.add(
                    Activity(
                        code=code,
                        name=name,
                        activo=activo,
                    )
                )

    db.commit()


def seed_funding_sources(db: Session, catalog_dir: Path) -> None:
    path = catalog_dir / "fuentes_financiamiento.csv"
    if not path.exists():
        print("No se encontró fuentes_financiamiento.csv")
        return

    with path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)

        for row in reader:
            code = row["codigo"].strip()
            description = fix_text(row["descripcion"])
            activo = str_to_bool(row.get("activo", "true"))

            existing = db.query(FundingSource).filter(FundingSource.code == code).first()

            if existing:
                existing.description = description
                existing.activo = activo
            else:
                db.add(
                    FundingSource(
                        code=code,
                        description=description,
                        activo=activo,
                    )
                )

    db.commit()


def seed_budget_lines(db: Session, catalog_dir: Path) -> None:
    path = catalog_dir / "renglones_presupuestarios_base.csv"
    if not path.exists():
        print("No se encontró renglones_presupuestarios_base.csv")
        return

    with path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)

        for row in reader:
            renglon = str(row["renglon"]).strip()
            concepto = fix_text(row["concepto"])
            activo = str_to_bool(row.get("activo", "true"))

            existing = db.query(BudgetLine).filter(BudgetLine.renglon == renglon).first()

            if existing:
                existing.grupo = int(row["grupo"])
                existing.subgrupo = int(row["subgrupo"])
                existing.concepto = concepto
                existing.activo = activo
            else:
                db.add(
                    BudgetLine(
                        grupo=int(row["grupo"]),
                        subgrupo=int(row["subgrupo"]),
                        renglon=renglon,
                        concepto=concepto,
                        activo=activo,
                    )
                )

    db.commit()


def seed_classification_rules(db: Session, catalog_dir: Path) -> None:
    path = catalog_dir / "reglas_clasificacion_base.csv"
    if not path.exists():
        print("No se encontró reglas_clasificacion_base.csv")
        return

    with path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)

        for row in reader:
            keyword = fix_text(row["keyword"]).lower()
            renglon = str(row["renglon"]).strip()

            budget_line = db.query(BudgetLine).filter(BudgetLine.renglon == renglon).first()
            if not budget_line:
                continue

            existing = db.query(ClassificationRule).filter(
                ClassificationRule.keyword == keyword,
                ClassificationRule.budget_line_id == budget_line.id,
            ).first()

            if existing:
                existing.priority = int(row.get("prioridad", 50))
                existing.activo = str_to_bool(row.get("activo", "true"))
            else:
                db.add(
                    ClassificationRule(
                        keyword=keyword,
                        budget_line_id=budget_line.id,
                        priority=int(row.get("prioridad", 50)),
                        activo=str_to_bool(row.get("activo", "true")),
                    )
                )

    db.commit()


def repair_existing_bad_text(db: Session) -> None:
    budget_lines = db.query(BudgetLine).all()
    for line in budget_lines:
        line.concepto = fix_text(line.concepto)

    activities = db.query(Activity).all()
    for activity in activities:
        activity.name = fix_text(activity.name)

    sources = db.query(FundingSource).all()
    for source in sources:
        source.description = fix_text(source.description)

    rules = db.query(ClassificationRule).all()
    for rule in rules:
        rule.keyword = fix_text(rule.keyword).lower()

    db.commit()


def seed_all_catalogs(db: Session) -> None:
    catalog_dir = Path(settings.catalog_dir)

    seed_default_user(db)
    seed_activities(db, catalog_dir)
    seed_funding_sources(db, catalog_dir)
    seed_budget_lines(db, catalog_dir)
    seed_classification_rules(db, catalog_dir)
    repair_existing_bad_text(db)

    print("Catálogos iniciales cargados y corregidos correctamente.")