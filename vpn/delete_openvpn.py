#!/usr/bin/env python3
"""
Скрипт для удаления OpenVPN сервера с DigitalOcean
"""

import os
import sys
import json
import requests
from pathlib import Path

def get_do_token():
    """Получить токен DigitalOcean из переменной окружения"""
    token = os.environ.get('DIGITALOCEAN_ACCESS_TOKEN')
    if not token:
        print("❌ Ошибка: Установите переменную окружения DIGITALOCEAN_ACCESS_TOKEN")
        sys.exit(1)
    return token

def delete_droplet(token, droplet_id):
    """Удалить droplet"""
    print(f"🗑️  Удаление droplet {droplet_id}...")
    
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    response = requests.delete(
        f'https://api.digitalocean.com/v2/droplets/{droplet_id}',
        headers=headers
    )
    
    if response.status_code == 204:
        print(f"✅ Droplet {droplet_id} удален")
        return True
    else:
        print(f"❌ Ошибка удаления: {response.text}")
        return False

def main():
    info_file = Path('openvpn_info.json')
    
    if not info_file.exists():
        print("❌ Файл openvpn_info.json не найден")
        print("   Укажите droplet_id вручную или запустите скрипт из директории с openvpn_info.json")
        sys.exit(1)
    
    with open(info_file, 'r') as f:
        info = json.load(f)
    
    droplet_id = info.get('droplet_id')
    
    if not droplet_id:
        print("❌ droplet_id не найден в openvpn_info.json")
        sys.exit(1)
    
    token = get_do_token()
    
    confirm = input(f"⚠️  Вы уверены, что хотите удалить droplet {droplet_id}? (yes/no): ")
    if confirm.lower() != 'yes':
        print("Отменено")
        sys.exit(0)
    
    if delete_droplet(token, droplet_id):
        # Удаляем локальные файлы
        info_file.unlink()
        config_file = Path('client1.ovpn')
        if config_file.exists():
            config_file.unlink()
        print("✅ Локальные файлы удалены")

if __name__ == '__main__':
    main()
