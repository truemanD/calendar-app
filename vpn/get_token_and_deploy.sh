#!/bin/bash
# Скрипт для автоматического получения токена и развертывания VPN

set -e

echo "🔍 Поиск DigitalOcean токена..."

# Проверяем переменную окружения
if [ -n "$DIGITALOCEAN_ACCESS_TOKEN" ]; then
    echo "✅ Токен найден в переменной окружения"
    TOKEN="$DIGITALOCEAN_ACCESS_TOKEN"
elif [ -f ~/.config/doctl/config.yaml ]; then
    # Пытаемся извлечь токен из doctl конфигурации
    TOKEN=$(grep -A 5 "access-token" ~/.config/doctl/config.yaml 2>/dev/null | grep -oP '(?<=access-token: ).*' | head -1 || echo "")
    if [ -n "$TOKEN" ]; then
        echo "✅ Токен найден в doctl конфигурации"
        export DIGITALOCEAN_ACCESS_TOKEN="$TOKEN"
    fi
fi

if [ -z "$TOKEN" ]; then
    echo "❌ Токен не найден"
    echo ""
    echo "Пожалуйста, установите токен одним из способов:"
    echo "1. export DIGITALOCEAN_ACCESS_TOKEN='your-token'"
    echo "2. doctl auth init"
    echo ""
    echo "Получить токен: https://cloud.digitalocean.com/account/api/tokens"
    exit 1
fi

# Запускаем развертывание
echo "🚀 Запуск развертывания VPN..."
cd "$(dirname "$0")"

if command -v python3 &> /dev/null && [ -f deploy_vpn.py ]; then
    python3 deploy_vpn.py
else
    ./deploy_vpn_doctl.sh
fi
