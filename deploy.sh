#!/bin/bash

# Скрипт для развертывания календаря на DigitalOcean App Platform

echo "🚀 Развертывание календаря на DigitalOcean..."

# Проверяем, установлен ли doctl
if ! command -v doctl &> /dev/null; then
    echo "❌ doctl не установлен. Установите его:"
    echo "   macOS: brew install doctl"
    echo "   Linux: https://docs.digitalocean.com/reference/doctl/how-to/install/"
    exit 1
fi

# Проверяем авторизацию
if ! doctl auth list &> /dev/null; then
    echo "🔐 Требуется авторизация в DigitalOcean..."
    doctl auth init
fi

# Создаем приложение
echo "📦 Создание приложения на DigitalOcean..."
doctl apps create --spec .do/app.yaml

echo "✅ Приложение создано!"
echo "📝 Проверьте статус: doctl apps list"
echo "🌐 URL приложения будет доступен после деплоя"
