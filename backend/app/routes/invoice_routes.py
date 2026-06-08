from pathlib import Path
from uuid import uuid4
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session, joinedload

from app.core.config import get_settings
from app.database import get_db
from app.models import Invoice, UploadBatch
from app.queues.redis_queue import get_invoice_queue
from app.services.pdf_extractor_service import extract_pdf_text, get_clean_lines
from app.workers.invoice_tasks import process_invoice_job

router = APIRouter(prefix="/invoices", tags=["Invoices"])
settings = get_settings()


def ensure_upload_dir() -> Path:
    upload_dir = Path("/app") / settings.upload_dir
    upload_dir.mkdir(parents=True, exist_ok=True)
    return upload_dir


@router.post("/upload")
async def upload_invoices(
    files: list[UploadFile] = File(...),
    user_id: int = Query(default=1),
    db: Session = Depends(get_db),
):
    if len(files) == 0:
        raise HTTPException(status_code=400, detail="Debes subir al menos un PDF.")

    if len(files) > settings.max_pdfs_per_batch:
        raise HTTPException(
            status_code=400,
            detail=f"Solo puedes subir máximo {settings.max_pdfs_per_batch} PDFs por lote.",
        )

    pending_count = db.query(Invoice).filter(
        Invoice.uploaded_by == user_id,
        Invoice.estado.in_(["SUBIDA", "EN_COLA", "PROCESANDO"]),
    ).count()

    if pending_count + len(files) > settings.max_pending_invoices_per_user:
        raise HTTPException(
            status_code=400,
            detail=f"No puedes tener más de {settings.max_pending_invoices_per_user} facturas pendientes o procesando.",
        )

    batch = UploadBatch(
        uploaded_by=user_id,
        total_files=len(files),
        accepted_files=0,
        rejected_files=0,
        status="CREATED",
    )
    db.add(batch)
    db.commit()
    db.refresh(batch)

    upload_dir = ensure_upload_dir()
    queue = get_invoice_queue()

    accepted = []
    rejected = []

    max_bytes = settings.max_pdf_size_mb * 1024 * 1024

    for file in files:
        filename_lower = file.filename.lower() if file.filename else ""

        if not filename_lower.endswith(".pdf"):
            rejected.append({
                "filename": file.filename,
                "reason": "Solo se permiten archivos PDF.",
            })
            continue

        content = await file.read()

        if len(content) > max_bytes:
            rejected.append({
                "filename": file.filename,
                "reason": f"El PDF supera el límite de {settings.max_pdf_size_mb} MB.",
            })
            continue

        stored_name = f"{uuid4()}_{file.filename}"
        stored_path = upload_dir / stored_name

        with stored_path.open("wb") as output:
            output.write(content)

        invoice = Invoice(
            batch_id=batch.id,
            pdf_path=str(stored_path),
            estado="EN_COLA",
            queue_status="EN_COLA",
            uploaded_by=user_id,
        )
        db.add(invoice)
        db.commit()
        db.refresh(invoice)

        queue.enqueue(process_invoice_job, invoice.id)

        accepted.append({
            "invoice_id": invoice.id,
            "filename": file.filename,
            "status": "EN_COLA",
        })

    batch.accepted_files = len(accepted)
    batch.rejected_files = len(rejected)
    batch.status = "FINALIZADO"
    db.commit()

    return {
        "batch_id": batch.id,
        "accepted_files": len(accepted),
        "rejected_files": len(rejected),
        "accepted": accepted,
        "rejected": rejected,
    }


@router.get("")
def list_invoices(db: Session = Depends(get_db)):
    invoices = db.query(Invoice).order_by(Invoice.id.desc()).limit(50).all()

    return [
        {
            "id": invoice.id,
            "serie": invoice.serie,
            "numero_dte": invoice.numero_dte,
            "proveedor": invoice.proveedor,
            "moneda": invoice.moneda,
            "total_factura": float(invoice.total_factura) if invoice.total_factura is not None else None,
            "estado": invoice.estado,
            "queue_status": invoice.queue_status,
            "created_at": invoice.created_at,
            "error_message": invoice.error_message,
        }
        for invoice in invoices
    ]


@router.get("/{invoice_id}/raw-text")
def get_invoice_raw_text(invoice_id: int, db: Session = Depends(get_db)):
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()

    if not invoice:
        raise HTTPException(status_code=404, detail="Factura no encontrada.")

    text = extract_pdf_text(invoice.pdf_path)
    lines = get_clean_lines(text)

    return {
        "invoice_id": invoice.id,
        "pdf_path": invoice.pdf_path,
        "line_count": len(lines),
        "lines": [
            {
                "number": index + 1,
                "text": line,
            }
            for index, line in enumerate(lines)
        ],
        "raw_text": text,
    }


@router.get("/{invoice_id}")
def get_invoice(invoice_id: int, db: Session = Depends(get_db)):
    invoice = db.query(Invoice).options(
        joinedload(Invoice.items)
    ).filter(Invoice.id == invoice_id).first()

    if not invoice:
        raise HTTPException(status_code=404, detail="Factura no encontrada.")

    ordered_items = sorted(invoice.items, key=lambda item: item.line_number or 0)

    return {
        "id": invoice.id,
        "serie": invoice.serie,
        "numero_dte": invoice.numero_dte,
        "nit_emisor": invoice.nit_emisor,
        "proveedor": invoice.proveedor,
        "nit_receptor": invoice.nit_receptor,
        "nombre_receptor": invoice.nombre_receptor,
        "moneda": invoice.moneda,
        "total_factura": float(invoice.total_factura) if invoice.total_factura is not None else None,
        "estado": invoice.estado,
        "queue_status": invoice.queue_status,
        "error_message": invoice.error_message,
        "items": [
            {
                "id": item.id,
                "line_number": item.line_number,
                "tipo": item.tipo,
                "descripcion": item.descripcion,
                "cantidad": float(item.cantidad) if item.cantidad is not None else None,
                "precio_unitario": float(item.precio_unitario) if item.precio_unitario is not None else None,
                "total": float(item.total) if item.total is not None else None,
                "budget_line_id": item.budget_line_id,
                "renglon_sugerido": item.budget_line.renglon if item.budget_line else None,
                "concepto_sugerido": item.budget_line.concepto if item.budget_line else None,
                "activity_id": item.activity_id,
                "funding_source_id": item.funding_source_id,
                "classification_confidence": float(item.classification_confidence) if item.classification_confidence is not None else None,
                "classification_origin": item.classification_origin,
                "estado_revision": item.estado_revision,
            }
            for item in ordered_items
        ],
    }
