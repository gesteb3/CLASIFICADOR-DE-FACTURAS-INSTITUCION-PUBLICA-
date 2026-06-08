# Diseño de Base de Datos Inicial

## users

- id
- name
- email
- password_hash
- role
- is_active
- created_at
- updated_at

## upload_batches

- id
- uploaded_by
- total_files
- accepted_files
- rejected_files
- status
- created_at

## invoices

- id
- batch_id
- serie
- numero_dte
- nit_emisor
- proveedor
- nit_receptor
- nombre_receptor
- moneda
- total_factura
- pdf_path
- estado
- queue_status
- uploaded_by
- processing_started_at
- processing_finished_at
- error_message
- created_at
- updated_at

## invoice_items

- id
- invoice_id
- line_number
- tipo
- descripcion
- cantidad
- precio_unitario
- total
- budget_line_id
- activity_id
- funding_source_id
- classification_confidence
- classification_origin
- estado_revision
- created_at
- updated_at

## budget_lines

- id
- grupo
- subgrupo
- renglon
- concepto
- activo
- created_at
- updated_at

## activities

- id
- code
- name
- activo
- created_at
- updated_at

## funding_sources

- id
- code
- description
- activo
- created_at
- updated_at

## classification_rules

- id
- keyword
- budget_line_id
- priority
- activo
- created_by
- created_at
- updated_at

## classification_history

- id
- normalized_description
- budget_line_id
- times_used
- last_used_at
- created_at
- updated_at

## audit_logs

- id
- user_id
- entity_name
- entity_id
- action
- old_value
- new_value
- created_at
