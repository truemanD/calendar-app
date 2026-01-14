#!/usr/bin/env python3
"""
Скрипт для развертывания VPN с запросом токена
"""

import os
import sys
import getpass

# Пытаемся получить токен из разных источников
token = os.environ.get('DIGITALOCEAN_ACCESS_TOKEN')

if not token:
    print("🔑 Токен не найден в переменных окружения")
    print("   Введите токен DigitalOcean API:")
    token = getpass.getpass("Token: ").strip()
    
    if not token:
        print("❌ Токен не предоставлен")
        sys.exit(1)
    
    # Устанавливаем для дочернего процесса
    os.environ['DIGITALOCEAN_ACCESS_TOKEN'] = token

# Импортируем и запускаем основной скрипт
sys.path.insert(0, os.path.dirname(__file__))
from deploy_vpn import main

if __name__ == '__main__':
    main()
