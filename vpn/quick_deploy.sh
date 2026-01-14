#!/bin/bash
# Быстрое развертывание VPN с токеном

set -e

cd "$(dirname "$0")"

echo "============================================================"
echo "🚀 Быстрое развертывание WireGuard VPN"
echo "============================================================"
echo ""

# Проверяем токен
if [ -z "$DIGITALOCEAN_ACCESS_TOKEN" ]; then
    echo "🔑 Введите DigitalOcean API токен:"
    echo "   (или установите: export DIGITALOCEAN_ACCESS_TOKEN='your-token')"
    echo ""
    read -sp "Token: " TOKEN
    echo ""
    export DIGITALOCEAN_ACCESS_TOKEN="$TOKEN"
fi

# Проверяем Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 не установлен"
    exit 1
fi

# Устанавливаем зависимости
echo "📦 Проверка зависимостей..."
pip3 install -q requests 2>/dev/null || pip3 install requests

# Запускаем развертывание
echo "🚀 Запуск развертывания..."
python3 deploy_vpn.py
