# ComprasBotGuatecompras

Sistema local para procesar facturas PDF descargadas desde SAT, extraer datos, clasificar productos o servicios por renglÃ³n presupuestario y preparar la informaciÃ³n para una futura automatizaciÃ³n en GUATECOMPRAS y SICOIN GL.

## Alcance del MVP

- Subida de facturas en PDF con texto seleccionable.
- Una factura por compra.
- MÃ¡ximo 10 PDFs por carga.
- MÃ¡ximo 20 facturas pendientes o procesando por usuario.
- MÃ¡ximo 10 MB por PDF.
- Procesamiento en cola con Redis.
- 2 workers en paralelo.
- ClasificaciÃ³n con una sola sugerencia de renglÃ³n.
- RenglÃ³n editable manualmente.
- Actividad seleccionada desde lista.
- Fuente de financiamiento seleccionada desde lista.
- PostgreSQL como base de datos.
- Ollama en Docker con modelo qwen2.5:0.5b.

## Stack

- Backend: FastAPI.
- Frontend: React + Vite.
- Base de datos: PostgreSQL.
- Cola: Redis.
- IA local: Ollama.
- Modelo IA: qwen2.5:0.5b.
- AutomatizaciÃ³n futura: Playwright.

## Servicios Docker iniciales

- postgres
- redis
- ollama

## Comandos principales

Levantar infraestructura:

docker compose up -d

Descargar modelo de IA:

powershell -ExecutionPolicy Bypass -File scripts/init_ai_model.ps1

Probar modelo:

powershell -ExecutionPolicy Bypass -File scripts/test_ai_model.ps1
