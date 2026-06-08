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
        invoice.processing_finished_at = None
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
        invoice.estado = "EXTRAIDA"
        invoice.queue_status = "CLASIFICANDO"

        db.query(InvoiceItem).filter(InvoiceItem.invoice_id == invoice.id).delete()
        db.commit()

        items = extracted.get("items", [])

        if not items:
            invoice.estado = "ERROR_EXTRACCION"
            invoice.queue_status = "ERROR"
            invoice.error_message = "No se detectaron productos o servicios en la factura."
            invoice.processing_finished_at = datetime.now(timezone.utc)
            db.commit()
            print(f"No se detectaron items en la factura {invoice_id}")
            return

        for item_data in items:
            item = InvoiceItem(
                invoice_id=invoice.id,
                line_number=item_data.get("line_number"),
                tipo=item_data.get("tipo"),
                descripcion=item_data.get("descripcion") or "",
                cantidad=item_data.get("cantidad"),
                precio_unitario=item_data.get("precio_unitario"),
                total=item_data.get("total"),
                budget_line_id=None,
                classification_confidence=None,
                classification_origin=None,
                estado_revision="PENDIENTE",
            )
            db.add(item)

        db.commit()

        saved_items = (
            db.query(InvoiceItem)
            .filter(InvoiceItem.invoice_id == invoice.id)
            .order_by(InvoiceItem.line_number.asc())
            .all()
        )

        for item in saved_items:
            try:
                budget_line, confidence, origin = classify_item(
                    db,
                    item.descripcion,
                    item.tipo,
                )

                item.budget_line_id = budget_line.id if budget_line else None
                item.classification_confidence = confidence
                item.classification_origin = origin
                db.commit()

            except Exception as item_error:
                db.rollback()

                item = db.query(InvoiceItem).filter(InvoiceItem.id == item.id).first()

                if item:
                    item.classification_origin = "ERROR_CLASIFICACION"
                    item.classification_confidence = None
                    db.commit()

                print(f"Error clasificando item {item.id if item else 'desconocido'}: {item_error}")

        invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()

        if invoice:
            invoice.estado = "CLASIFICADA"
            invoice.queue_status = "FINALIZADA"
            invoice.processing_finished_at = datetime.now(timezone.utc)
            invoice.error_message = None
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