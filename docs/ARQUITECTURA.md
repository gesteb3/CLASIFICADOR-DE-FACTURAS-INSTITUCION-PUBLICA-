# Arquitectura Inicial

## Flujo

Usuario sube PDF
â†“
FastAPI guarda archivo
â†“
Se crea registro en PostgreSQL
â†“
Factura entra a cola Redis
â†“
Worker procesa factura
â†“
Se extrae informaciÃ³n del PDF
â†“
Se clasifica con reglas, historial e IA local
â†“
Se guarda resultado
â†“
Usuario revisa renglÃ³n, actividad y fuente
â†“
Usuario aprueba

## Servicios

### PostgreSQL

Guarda usuarios, facturas, productos, renglones, actividades, fuentes y auditorÃ­a.

### Redis

Administra la cola de facturas.

### Ollama

Ejecuta el modelo local qwen2.5:0.5b para apoyar la clasificaciÃ³n.

### Worker

Procesa PDFs en segundo plano.

### FastAPI

Expone endpoints para frontend.

### React

Interfaz web para subir, revisar y aprobar facturas.
