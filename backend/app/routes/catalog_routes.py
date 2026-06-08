from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Activity, BudgetLine, FundingSource

router = APIRouter(prefix="/catalogs", tags=["Catalogs"])


@router.get("/activities")
def list_activities(db: Session = Depends(get_db)):
    activities = db.query(Activity).filter(Activity.activo.is_(True)).order_by(Activity.code.asc()).all()

    return [
        {
            "id": activity.id,
            "code": activity.code,
            "name": activity.name,
        }
        for activity in activities
    ]


@router.get("/funding-sources")
def list_funding_sources(db: Session = Depends(get_db)):
    sources = db.query(FundingSource).filter(FundingSource.activo.is_(True)).order_by(FundingSource.code.asc()).all()

    return [
        {
            "id": source.id,
            "code": source.code,
            "description": source.description,
        }
        for source in sources
    ]


@router.get("/budget-lines")
def list_budget_lines(
    search: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    query = db.query(BudgetLine).filter(BudgetLine.activo.is_(True))

    if search:
        like = f"%{search}%"
        query = query.filter(
            (BudgetLine.renglon.ilike(like)) |
            (BudgetLine.concepto.ilike(like))
        )

    lines = query.order_by(BudgetLine.renglon.asc()).all()

    return [
        {
            "id": line.id,
            "grupo": line.grupo,
            "subgrupo": line.subgrupo,
            "renglon": line.renglon,
            "concepto": line.concepto,
        }
        for line in lines
    ]
