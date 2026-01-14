#!/bin/bash
# Скрипт для удаления VPN сервера

set -e

if [ ! -f "vpn_info.json" ]; then
    echo "❌ Файл vpn_info.json не найден"
    exit 1
fi

DROPLET_ID=$(grep -o '"droplet_id": [0-9]*' vpn_info.json | grep -o '[0-9]*')

if [ -z "$DROPLET_ID" ]; then
    echo "❌ droplet_id не найден в vpn_info.json"
    exit 1
fi

echo "⚠️  Вы уверены, что хотите удалить droplet $DROPLET_ID? (yes/no)"
read -r CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo "Отменено"
    exit 0
fi

echo "🗑️  Удаление droplet $DROPLET_ID..."
doctl compute droplet delete "$DROPLET_ID" -f

# Удаляем локальные файлы
rm -f vpn_info.json wg0.conf

echo "✅ Droplet удален и локальные файлы очищены"
