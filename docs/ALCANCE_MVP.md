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
