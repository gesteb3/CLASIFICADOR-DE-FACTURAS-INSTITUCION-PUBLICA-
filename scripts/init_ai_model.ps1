Write-Host "Descargando modelo qwen2.5:0.5b dentro del contenedor de Ollama..."
docker exec -it compras_ollama ollama pull qwen2.5:0.5b
Write-Host "Modelo instalado correctamente."
