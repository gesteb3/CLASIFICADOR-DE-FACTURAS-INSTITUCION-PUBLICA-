# setup.ps1
# Estructura inicial del proyecto ComprasBotGuatecompras

$ProjectRoot = Get-Location

Write-Host "Creando estructura del proyecto..."

# Carpetas principales
mkdir backend -Force
mkdir frontend -Force
mkdir database -Force
mkdir uploads -Force
mkdir docs -Force
mkdir scripts -Force

# Backend
mkdir backend/app -Force
mkdir backend/app/models -Force
mkdir backend/app/routes -Force
mkdir backend/app/services -Force
mkdir backend/app/workers -Force
mkdir backend/app/queues -Force
mkdir backend/app/core -Force
mkdir backend/app/schemas -Force
mkdir backend/app/catalogs -Force
mkdir backend/tests -Force

# Frontend
mkdir frontend/src -Force
mkdir frontend/src/pages -Force
mkdir frontend/src/components -Force
mkdir frontend/src/services -Force
mkdir frontend/src/layouts -Force

# Base de datos
mkdir database/catalogos -Force
mkdir database/migrations -Force
mkdir database/seeds -Force

# Uploads locales
mkdir uploads/invoices -Force
mkdir uploads/temp -Force

# Archivos para mantener carpetas vacías
New-Item backend/app/models/.gitkeep -ItemType File -Force
New-Item backend/app/routes/.gitkeep -ItemType File -Force
New-Item backend/app/services/.gitkeep -ItemType File -Force
New-Item backend/app/workers/.gitkeep -ItemType File -Force
New-Item backend/app/queues/.gitkeep -ItemType File -Force
New-Item frontend/src/pages/.gitkeep -ItemType File -Force
New-Item frontend/src/components/.gitkeep -ItemType File -Force
New-Item uploads/.gitkeep -ItemType File -Force
New-Item uploads/invoices/.gitkeep -ItemType File -Force
New-Item uploads/temp/.gitkeep -ItemType File -Force

# .gitignore
@'
# Python
__pycache__/
*.pyc
.venv/
venv/
env/

# Node
node_modules/
dist/
build/

# Variables de entorno
.env

# Archivos subidos
uploads/*
!uploads/.gitkeep
!uploads/invoices/.gitkeep
!uploads/temp/.gitkeep

# Docker / logs
*.log

# IDE
.vscode/
.idea/

# Sistema operativo
.DS_Store
Thumbs.db
'@ | Set-Content ".gitignore" -Encoding UTF8

# .env.example
@'
APP_NAME=ComprasBotGuatecompras
APP_ENV=local
APP_DEBUG=true

BACKEND_HOST=0.0.0.0
BACKEND_PORT=8000

POSTGRES_DB=compras_bot
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_HOST=postgres
POSTGRES_PORT=5432

REDIS_HOST=redis
REDIS_PORT=6379

OLLAMA_HOST=http://ollama:11434
OLLAMA_MODEL=qwen2.5:0.5b

SECRET_KEY=cambiar_esta_clave_en_desarrollo
ACCESS_TOKEN_EXPIRE_MINUTES=60

MAX_PDFS_PER_BATCH=10
MAX_PENDING_INVOICES_PER_USER=20
MAX_PDF_SIZE_MB=10
MAX_WORKERS=2

UPLOAD_DIR=uploads/invoices
'@ | Set-Content ".env.example" -Encoding UTF8

# docker-compose.yml con PostgreSQL, Redis y Ollama
@'
services:
  postgres:
    image: postgres:16
    container_name: compras_postgres
    restart: always
    environment:
      POSTGRES_DB: compras_bot
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    ports:
      - "5432:5432"
    volumes:
      - compras_postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7
    container_name: compras_redis
    restart: always
    ports:
      - "6379:6379"

  ollama:
    image: ollama/ollama:latest
    container_name: compras_ollama
    restart: always
    ports:
      - "11434:11434"
    volumes:
      - compras_ollama_data:/root/.ollama

volumes:
  compras_postgres_data:
  compras_ollama_data:
'@ | Set-Content "docker-compose.yml" -Encoding UTF8

# Script para descargar el modelo pequeño de IA
@'
Write-Host "Descargando modelo qwen2.5:0.5b dentro del contenedor de Ollama..."
docker exec -it compras_ollama ollama pull qwen2.5:0.5b
Write-Host "Modelo instalado correctamente."
'@ | Set-Content "scripts/init_ai_model.ps1" -Encoding UTF8

# Script para probar la IA
@'
Write-Host "Probando modelo qwen2.5:0.5b..."
docker exec -it compras_ollama ollama run qwen2.5:0.5b
'@ | Set-Content "scripts/test_ai_model.ps1" -Encoding UTF8

# Catálogo de actividades
@'
codigo,nombre,activo
1,"CONCEJO MUNICIPAL",true
2,"ALCALDIA MUNICIPAL",true
3,"SECRETARIA MUNICIPAL",true
4,"DIRECCION DE ADMINISTRACIÓN FINANCIERA MUNICIPAL (DAFIM)",true
5,"DIRECCION MUNICIPAL DE PLANIFICACIÓN (DMP)",true
6,"RECURSOS HUMANOS",true
7,"UNIDAD DE ACCESO A LA INFORMACION PUBLICA",true
8,"JUZGADO DE ASUNTOS MUNICIPALES",true
9,"OFICINA MUNICIPAL DE GESTION AMBIENTAL",true
10,"OFICINA DE CATASTRO MUNICIPAL",true
11,"CONSERVACION SISTEMA DE AGUA POTABLE A TRAVES DE LA OMAS",true
12,"CONSERVACION SERVICIOS TREN DE ASEO MUNICIPAL",true
13,"CONSERVACION MERCADO MUNICIPAL",true
14,"APOYO A LA EDUCACION",true
15,"APOYO INSTITUCIONAL DE LA POLICIA MUNICIPAL",true
16,"CONSERVACION RED DE ALUMBRADO PUBLICO",true
17,"CONSERVACION EDIFICIO MUNICIPALES",true
18,"CONSERVACION INSTITUCIONAL DIRECCION MUNICIPAL DE LA MUJER",true
19,"APOYO A LA SALUD PREVENTIVA Y ASISTENCIA SOCIAL",true
20,"APOYO A LA CULTURA Y DEPORTE Y LA RECREACION",true
21,"CONSERVACION CALLE(S) URBANAS Y CAMINOS RURALES",true
'@ | Set-Content "database/catalogos/actividades.csv" -Encoding UTF8

# Catálogo de fuentes de financiamiento
@'
codigo,descripcion,activo
"21-0101-0001","INGRESOS TRIBUTARIOS IVA PAZ",true
"22-0101-0001","INGRESOS ORDINARIOS DE APORTE CONSTITUCIONAL",true
"29-0101-0002","IMPUESTO DE CIRCULACION DE VEHICULOS",true
"29-0101-0003","IMPUESTO PETROLEO Y DERIVADOS",true
"31-0101-0004","CONSEJO DE DESARROLLO URBANO Y RURAL",true
"31-0151-0001","INGRESOS PROPIOS MUNICIPALES",true
"31-0151-0002","IMPUESTO UNICO SOBRE INMUEBLES IUSI (POR ADMON. MUNICIPAL)",true
"32-0101-0003","SC - INGRESOS TRIBUTARIOS IVA-PAZ",true
"32-0101-0004","SC - INGRESOS ORDINARIOS DE APORTE CONSTITUCIONAL",true
"32-0101-0006","SC - IMPUESTO CIRCULACION DE VEHICULOS",true
"32-0101-0014","SC - INGRESOS TRIBUTARIOS IVA-PAZ",true
"32-0101-0015","SC - INGRESOS ORDINARIOS DE APORTE CONSTITUCIONAL",true
"32-0101-0017","SC - IMPUESTO CIRCULACION DE VEHICULOS",true
"32-0151-0001","SC - INGRESOS PROPIOS MUNICIPALES",true
"32-0151-0002","SC - IUSI FUNCIONAMIENTO (POR ADMON. MUNICIPAL)",true
"32-0151-0003","SC - IUSI INVERSION (POR ADMON. MUNICIPAL)",true
'@ | Set-Content "database/catalogos/fuentes_financiamiento.csv" -Encoding UTF8

# Catálogo base de renglones presupuestarios
@'
grupo,subgrupo,renglon,concepto,activo
1,11,111,"Energía eléctrica",true
1,11,112,"Agua",true
1,11,113,"Telefonía",true
1,14,141,"Transporte de personas",true
1,14,142,"Fletes",true
1,14,143,"Almacenaje",true
1,18,181,"Estudios, investigaciones y proyectos de pre-factibilidad y factibilidad",true
1,18,182,"Servicios médico-sanitarios",true
1,18,183,"Servicios jurídicos",true
1,18,184,"Servicios económicos, financieros, contables y de auditoría",true
1,18,185,"Servicios de capacitación",true
1,18,186,"Servicios de informática y sistemas computarizados",true
1,18,189,"Otros estudios y/o servicios",true
1,19,199,"Otros servicios",true
2,21,211,"Alimentos para personas",true
2,24,241,"Papel de escritorio",true
2,24,242,"Papeles comerciales, cartulinas, cartones y otros",true
2,24,243,"Productos de papel o cartón",true
2,26,262,"Combustibles y lubricantes",true
2,26,266,"Productos medicinales y farmacéuticos",true
2,26,267,"Tintes, pinturas y colorantes",true
2,26,268,"Productos plásticos, nylon, vinil y P.V.C.",true
2,26,269,"Otros productos químicos y conexos",true
2,29,291,"Útiles de oficina",true
2,29,292,"Productos sanitarios, de limpieza y de uso personal",true
2,29,293,"Útiles educacionales y culturales",true
2,29,294,"Útiles deportivos y recreativos",true
2,29,295,"Útiles menores, suministros e instrumental médico-quirúrgicos, de laboratorio y cuidado de la salud",true
2,29,297,"Materiales, productos y accesorios eléctricos, cableado estructurado de redes informáticas y telefónicas",true
2,29,298,"Accesorios y repuestos en general",true
2,29,299,"Otros materiales y suministros",true
3,32,322,"Mobiliario y equipo de oficina",true
3,32,323,"Mobiliario y equipo médico-sanitario y de laboratorio",true
3,32,325,"Equipo de transporte",true
3,32,328,"Equipo de cómputo",true
'@ | Set-Content "database/catalogos/renglones_presupuestarios_base.csv" -Encoding UTF8

# Reglas iniciales de clasificación
@'
keyword,renglon,prioridad,activo
"transporte de personas",141,100,true
"servicio de transporte",141,95,true
"pacientes",141,80,true
"adultos mayores",141,80,true
"flete",142,100,true
"papel bond",241,100,true
"papel",241,80,true
"combustible",262,100,true
"gasolina",262,100,true
"diesel",262,100,true
"medicina",266,100,true
"medicamento",266,100,true
"pintura",267,100,true
"plastico",268,90,true
"plástico",268,90,true
"toner",291,95,true
"tóner",291,95,true
"utiles de oficina",291,100,true
"útiles de oficina",291,100,true
"limpieza",292,100,true
"desinfectante",292,90,true
"escoba",292,90,true
"mopa",292,90,true
"cable",297,90,true
"repuesto",298,90,true
'@ | Set-Content "database/catalogos/reglas_clasificacion_base.csv" -Encoding UTF8

# README principal
@'
# ComprasBotGuatecompras

Sistema local para procesar facturas PDF descargadas desde SAT, extraer datos, clasificar productos o servicios por renglón presupuestario y preparar la información para una futura automatización en GUATECOMPRAS y SICOIN GL.

## Alcance del MVP

- Subida de facturas en PDF con texto seleccionable.
- Una factura por compra.
- Máximo 10 PDFs por carga.
- Máximo 20 facturas pendientes o procesando por usuario.
- Máximo 10 MB por PDF.
- Procesamiento en cola con Redis.
- 2 workers en paralelo.
- Clasificación con una sola sugerencia de renglón.
- Renglón editable manualmente.
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
- Automatización futura: Playwright.

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
'@ | Set-Content "README.md" -Encoding UTF8

# Documento de alcance
@'
# Alcance MVP

## Entrada

El sistema recibirá facturas únicamente en PDF con texto seleccionable.

## Datos a extraer

- Serie.
- Número DTE.
- NIT emisor.
- Proveedor.
- NIT receptor si aparece.
- Nombre receptor.
- Moneda.
- Total factura.
- Productos o servicios.
- Cantidad.
- Precio unitario.
- Total por línea.
- Descripción.

## Clasificación

Cada producto o servicio tendrá un solo renglón sugerido.

No existirá campo de alternativa.

El usuario podrá editar manualmente el renglón.

## Actividad y fuente

La actividad y la fuente de financiamiento se seleccionarán por cada línea de factura.

Ambos campos serán listas desplegables.

## Procesamiento local

El sistema usará Redis y workers para procesar facturas sin trabar la computadora.

Límites:

- 10 PDFs por lote.
- 20 facturas pendientes o procesando por usuario.
- 10 MB por PDF.
- 2 workers.
'@ | Set-Content "docs/ALCANCE_MVP.md" -Encoding UTF8

# Documento de arquitectura
@'
# Arquitectura Inicial

## Flujo

Usuario sube PDF
↓
FastAPI guarda archivo
↓
Se crea registro en PostgreSQL
↓
Factura entra a cola Redis
↓
Worker procesa factura
↓
Se extrae información del PDF
↓
Se clasifica con reglas, historial e IA local
↓
Se guarda resultado
↓
Usuario revisa renglón, actividad y fuente
↓
Usuario aprueba

## Servicios

### PostgreSQL

Guarda usuarios, facturas, productos, renglones, actividades, fuentes y auditoría.

### Redis

Administra la cola de facturas.

### Ollama

Ejecuta el modelo local qwen2.5:0.5b para apoyar la clasificación.

### Worker

Procesa PDFs en segundo plano.

### FastAPI

Expone endpoints para frontend.

### React

Interfaz web para subir, revisar y aprobar facturas.
'@ | Set-Content "docs/ARQUITECTURA.md" -Encoding UTF8

# Documento de base de datos
@'
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
'@ | Set-Content "docs/BASE_DATOS.md" -Encoding UTF8

# README backend
@'
# Backend

Aquí irá la API con FastAPI.

Carpetas:

- models: modelos SQLAlchemy.
- routes: endpoints.
- services: lógica de negocio.
- workers: procesamiento en segundo plano.
- queues: conexión con Redis.
- schemas: validaciones.
- core: configuración.
- catalogs: carga de catálogos.
'@ | Set-Content "backend/README.md" -Encoding UTF8

# README frontend
@'
# Frontend

Aquí irá la interfaz con React + Vite.

Pantallas esperadas:

- Login.
- Subida de facturas.
- Historial.
- Revisión y clasificación.
- Catálogos.
- Auditoría.
'@ | Set-Content "frontend/README.md" -Encoding UTF8

# README scripts
@'
# Scripts

Scripts auxiliares del proyecto:

- init_ai_model.ps1: descarga el modelo qwen2.5:0.5b.
- test_ai_model.ps1: prueba el modelo.
'@ | Set-Content "scripts/README.md" -Encoding UTF8

git init

Write-Host ""
Write-Host "Estructura creada correctamente."
Write-Host "Siguiente paso:"
Write-Host "docker compose up -d"
Write-Host "powershell -ExecutionPolicy Bypass -File scripts/init_ai_model.ps1"