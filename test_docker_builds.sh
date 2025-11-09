#!/bin/bash

# Script para testar builds dos Dockerfiles
echo "🐳 Testando builds dos Dockerfiles..."

services=("media_manager" "metadata_enricher" "scheduler_ai" "normalization_worker" "scene_analyzer")
failed_builds=()

for service in "${services[@]}"; do
    echo "📦 Testando build do $service..."
    
    if docker build -t "test-$service" -f "$service/Dockerfile" .; then
        echo "✅ Build do $service: SUCESSO"
        # Limpa a imagem de teste
        docker rmi "test-$service" > /dev/null 2>&1
    else
        echo "❌ Build do $service: FALHOU"
        failed_builds+=("$service")
    fi
    echo ""
done

echo "📊 Resumo dos testes:"
if [ ${#failed_builds[@]} -eq 0 ]; then
    echo "✅ Todos os 5 Dockerfiles foram construídos com sucesso!"
    echo "🎉 Pronto para deploy no Render!"
else
    echo "❌ Falhas nos builds:"
    for failed in "${failed_builds[@]}"; do
        echo "  - $failed"
    done
    exit 1
fi