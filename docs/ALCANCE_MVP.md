# Alcance MVP

## Entrada

El sistema recibirÃ¡ facturas Ãºnicamente en PDF con texto seleccionable.

## Datos a extraer

- Serie.
- NÃºmero DTE.
- NIT emisor.
- Proveedor.
- NIT receptor si aparece.
- Nombre receptor.
- Moneda.
- Total factura.
- Productos o servicios.
- Cantidad.
- Precio unitario.
- Total por lÃ­nea.
- DescripciÃ³n.

## ClasificaciÃ³n

Cada producto o servicio tendrÃ¡ un solo renglÃ³n sugerido.

No existirÃ¡ campo de alternativa.

El usuario podrÃ¡ editar manualmente el renglÃ³n.

## Actividad y fuente

La actividad y la fuente de financiamiento se seleccionarÃ¡n por cada lÃ­nea de factura.

Ambos campos serÃ¡n listas desplegables.

## Procesamiento local

El sistema usarÃ¡ Redis y workers para procesar facturas sin trabar la computadora.

LÃ­mites:

- 10 PDFs por lote.
- 20 facturas pendientes o procesando por usuario.
- 10 MB por PDF.
- 2 workers.
