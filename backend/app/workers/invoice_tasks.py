from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Invoice, InvoiceItem
from app.services.pdf_extractor_service import extract_invoice_data
from app.services.classification_service import classify_item


def process_invoice_job(invoice_id: int) -> None:
    db: Session = SessionLocal()

    try:
        invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()

        if not invoice:
            print(f"No existe la factura {invoice_id}")
            return

        invoice.estado = "PROCESANDO"
        invoice.queue_status = "PROCESANDO"
        invoice.processing_started_at = datetime.now(timezone.utc)
        invoice.error_message = None
        db.commit()

        extracted = extract_invoice_data(invoice.pdf_path)

        invoice.serie = extracted.get("serie")
        invoice.numero_dte = extracted.get("numero_dte")
        invoice.nit_emisor = extracted.get("nit_emisor")
        invoice.proveedor = extracted.get("proveedor")
        invoice.nit_receptor = extracted.get("nit_receptor")
        invoice.nombre_receptor = extracted.get("nombre_receptor")
        invoice.moneda = extracted.get("moneda") or "GTQ"
        invoice.total_factura = extracted.get("total_factura")

        db.query(InvoiceItem).filter(InvoiceItem.invoice_id == invoice.id).delete()

        items = extracted.get("items", [])

        for item_data in items:
            budget_line, confidence, origin = classify_item(db, item_data["descripcion"])

            item = InvoiceItem(
                invoice_id=invoice.id,
                line_number=item_data["line_number"],
                tipo=item_data["tipo"],
                descripcion=item_data["descripcion"],
                cantidad=item_data["cantidad"],
                precio_unitario=item_data["precio_unitario"],
                total=item_data["total"],
                budget_line_id=budget_line.id if budget_line else None,
                classification_confidence=confidence,
                classification_origin=origin,
                estado_revision="PENDIENTE",
            )
            db.add(item)

        invoice.estado = "CLASIFICADA"
        invoice.queue_status = "FINALIZADA"
        invoice.processing_finished_at = datetime.now(timezone.utc)
        db.commit()

        print(f"Factura {invoice_id} procesada correctamente.")

    except Exception as exc:
        db.rollback()

        invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
        if invoice:
            invoice.estado = "ERROR_EXTRACCION"
            invoice.queue_status = "ERROR"
            invoice.error_message = str(exc)
            invoice.processing_finished_at = datetime.now(timezone.utc)
            db.commit()

        print(f"Error procesando factura {invoice_id}: {exc}")

    finally:
        db.close()
