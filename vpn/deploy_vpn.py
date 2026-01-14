#!/usr/bin/env python3
"""
Скрипт для автоматического развертывания WireGuard VPN сервера на DigitalOcean
"""

import os
import sys
import json
import time
import subprocess
import requests
from pathlib import Path

# Конфигурация
DROPLET_NAME = "vpn-server"
REGION = "fra1"  # Frankfurt - один из самых дешевых регионов
SIZE = "s-1vcpu-1gb"  # Самый дешевый размер
IMAGE = "ubuntu-22-04-x64"
SSH_KEY_NAME = "vpn-ssh-key"

def get_do_token():
    """Получить токен DigitalOcean из переменной окружения"""
    token = os.environ.get('DIGITALOCEAN_ACCESS_TOKEN')
    if not token:
        print("❌ Ошибка: Установите переменную окружения DIGITALOCEAN_ACCESS_TOKEN")
        print("   export DIGITALOCEAN_ACCESS_TOKEN='your-token'")
        sys.exit(1)
    return token

def create_ssh_key(token):
    """Создать SSH ключ для доступа к droplet"""
    print("🔑 Создание SSH ключа...")
    
    # Генерируем SSH ключ если его нет
    key_path = Path.home() / ".ssh" / "vpn_do_key"
    pub_key_path = key_path.with_suffix('.pub')
    
    if not key_path.exists():
        subprocess.run([
            'ssh-keygen', '-t', 'ed25519', '-f', str(key_path),
            '-N', '', '-C', 'vpn-server-key'
        ], check=True, capture_output=True)
    
    # Читаем публичный ключ
    with open(pub_key_path, 'r') as f:
        public_key = f.read().strip()
    
    # Проверяем, существует ли ключ в DO
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    response = requests.get('https://api.digitalocean.com/v2/account/keys', headers=headers)
    if response.status_code == 200:
        keys = response.json().get('ssh_keys', [])
        for key in keys:
            if key.get('public_key') == public_key:
                print(f"✅ SSH ключ уже существует: {key['name']} (ID: {key['id']})")
                return key['id']
    
    # Создаем новый ключ
    data = {
        'name': SSH_KEY_NAME,
        'public_key': public_key
    }
    
    response = requests.post(
        'https://api.digitalocean.com/v2/account/keys',
        headers=headers,
        json=data
    )
    
    if response.status_code == 201:
        key_id = response.json()['ssh_key']['id']
        print(f"✅ SSH ключ создан: {key_id}")
        return key_id
    else:
        print(f"❌ Ошибка создания SSH ключа: {response.text}")
        sys.exit(1)

def create_droplet(token, ssh_key_id):
    """Создать droplet с VPN сервером"""
    print(f"🚀 Создание droplet {DROPLET_NAME}...")
    
    # User data скрипт для установки WireGuard
    user_data = """#!/bin/bash
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y wireguard wireguard-tools iptables qrencode

# Включаем IP forwarding
echo "net.ipv4.ip_forward=1" >> /etc/sysctl.conf
sysctl -p

# Создаем конфигурацию WireGuard
mkdir -p /etc/wireguard
cd /etc/wireguard
wg genkey | tee server_private.key | wg pubkey > server_public.key

# Создаем конфигурацию сервера
cat > /etc/wireguard/wg0.conf <<EOF
[Interface]
PrivateKey = $(cat server_private.key)
Address = 10.0.0.1/24
ListenPort = 51820
PostUp = iptables -A FORWARD -i wg0 -j ACCEPT; iptables -A FORWARD -o wg0 -j ACCEPT; iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE
PostDown = iptables -D FORWARD -i wg0 -j ACCEPT; iptables -D FORWARD -o wg0 -j ACCEPT; iptables -t nat -D POSTROUTING -o eth0 -j MASQUERADE

EOF

# Генерируем ключи для клиента
wg genkey | tee client_private.key | wg pubkey > client_public.key
CLIENT_PRIVATE=$(cat client_private.key)
CLIENT_PUBLIC=$(cat client_public.key)
SERVER_PUBLIC=$(cat server_public.key)
SERVER_PRIVATE=$(cat server_private.key)

# Добавляем клиента в конфигурацию
cat >> /etc/wireguard/wg0.conf <<EOF

[Peer]
PublicKey = $CLIENT_PUBLIC
AllowedIPs = 10.0.0.2/32
EOF

# Запускаем WireGuard
systemctl enable wg-quick@wg0
systemctl start wg-quick@wg0

# Сохраняем конфигурацию клиента
cat > /root/client.conf <<EOF
[Interface]
PrivateKey = $CLIENT_PRIVATE
Address = 10.0.0.2/24
DNS = 8.8.8.8

[Peer]
PublicKey = $SERVER_PUBLIC
Endpoint = $(curl -s ifconfig.me):51820
AllowedIPs = 0.0.0.0/0
PersistentKeepalive = 25
EOF

# Выводим информацию
echo "=== VPN Server Setup Complete ===" > /root/vpn_info.txt
echo "Server Public Key: $SERVER_PUBLIC" >> /root/vpn_info.txt
echo "Client Public Key: $CLIENT_PUBLIC" >> /root/vpn_info.txt
echo "Client Config saved to /root/client.conf" >> /root/vpn_info.txt
"""
    
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    data = {
        'name': DROPLET_NAME,
        'region': REGION,
        'size': SIZE,
        'image': IMAGE,
        'ssh_keys': [ssh_key_id],
        'user_data': user_data,
        'monitoring': False,
        'backups': False,
        'ipv6': False
    }
    
    response = requests.post(
        'https://api.digitalocean.com/v2/droplets',
        headers=headers,
        json=data
    )
    
    if response.status_code == 202:
        droplet = response.json()['droplet']
        droplet_id = droplet['id']
        print(f"✅ Droplet создан: {droplet_id}")
        print(f"   Имя: {droplet['name']}")
        print(f"   Регион: {droplet['region']['name']}")
        print(f"   Размер: {droplet['size_slug']}")
        return droplet_id
    else:
        print(f"❌ Ошибка создания droplet: {response.text}")
        sys.exit(1)

def wait_for_droplet(token, droplet_id):
    """Ждать пока droplet станет активным"""
    print("⏳ Ожидание активации droplet...")
    
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    max_attempts = 60
    for attempt in range(max_attempts):
        response = requests.get(
            f'https://api.digitalocean.com/v2/droplets/{droplet_id}',
            headers=headers
        )
        
        if response.status_code == 200:
            droplet = response.json()['droplet']
            status = droplet['status']
            
            if status == 'active':
                # Ждем еще немного для получения IP
                time.sleep(10)
                response = requests.get(
                    f'https://api.digitalocean.com/v2/droplets/{droplet_id}',
                    headers=headers
                )
                droplet = response.json()['droplet']
                
                ipv4 = None
                for network in droplet.get('networks', {}).get('v4', []):
                    if network['type'] == 'public':
                        ipv4 = network['ip_address']
                        break
                
                if ipv4:
                    print(f"✅ Droplet активен! IP: {ipv4}")
                    return ipv4
                else:
                    print("⏳ Ожидание назначения IP адреса...")
            else:
                print(f"   Статус: {status}...")
        
        time.sleep(5)
    
    print("❌ Timeout: Droplet не стал активным")
    sys.exit(1)

def wait_for_ssh(ip, max_attempts=30):
    """Ждать пока SSH станет доступен"""
    print("⏳ Ожидание доступности SSH...")
    
    key_path = Path.home() / ".ssh" / "vpn_do_key"
    
    for attempt in range(max_attempts):
        result = subprocess.run(
            ['ssh', '-i', str(key_path), '-o', 'StrictHostKeyChecking=no',
             '-o', 'ConnectTimeout=5', f'root@{ip}', 'echo "SSH ready"'],
            capture_output=True,
            timeout=10
        )
        
        if result.returncode == 0:
            print("✅ SSH доступен!")
            return True
        
        time.sleep(5)
    
    print("❌ Timeout: SSH не стал доступен")
    return False

def get_vpn_config(ip):
    """Получить конфигурацию VPN с сервера"""
    print("📥 Получение конфигурации VPN...")
    
    key_path = Path.home() / ".ssh" / "vpn_do_key"
    
    # Ждем пока WireGuard установится (может занять время)
    print("⏳ Ожидание установки WireGuard...")
    time.sleep(30)
    
    max_attempts = 20
    for attempt in range(max_attempts):
        result = subprocess.run(
            ['ssh', '-i', str(key_path), '-o', 'StrictHostKeyChecking=no',
             f'root@{ip}', 'test -f /root/client.conf && echo "ready"'],
            capture_output=True,
            timeout=10
        )
        
        if result.returncode == 0 and b'ready' in result.stdout:
            break
        
        time.sleep(5)
    
    # Получаем конфигурацию клиента
    result = subprocess.run(
        ['ssh', '-i', str(key_path), '-o', 'StrictHostKeyChecking=no',
         f'root@{ip}', 'cat /root/client.conf'],
        capture_output=True,
        text=True,
        timeout=10
    )
    
    if result.returncode == 0:
        config = result.stdout
        # Обновляем Endpoint с реальным IP
        config = config.replace('$(curl -s ifconfig.me):51820', f'{ip}:51820')
        return config
    else:
        print(f"❌ Ошибка получения конфигурации: {result.stderr}")
        return None

def save_config(config, ip):
    """Сохранить конфигурацию в файл"""
    config_file = Path('wg0.conf')
    with open(config_file, 'w') as f:
        f.write(config)
    
    print(f"✅ Конфигурация сохранена в {config_file}")
    print(f"\n📋 Информация о VPN сервере:")
    print(f"   IP адрес: {ip}")
    print(f"   Порт: 51820")
    print(f"   Протокол: WireGuard")
    print(f"\n📱 Для подключения:")
    print(f"   1. Установите WireGuard клиент")
    print(f"   2. Импортируйте файл {config_file}")
    print(f"   3. Или отсканируйте QR код (если доступен)")
    
    return config_file

def main():
    print("=" * 60)
    print("🚀 Развертывание WireGuard VPN сервера на DigitalOcean")
    print("=" * 60)
    
    token = get_do_token()
    ssh_key_id = create_ssh_key(token)
    droplet_id = create_droplet(token, ssh_key_id)
    ip = wait_for_droplet(token, droplet_id)
    
    if wait_for_ssh(ip):
        config = get_vpn_config(ip)
        if config:
            config_file = save_config(config, ip)
            
            # Сохраняем информацию о droplet
            info = {
                'droplet_id': droplet_id,
                'ip': ip,
                'name': DROPLET_NAME,
                'region': REGION,
                'size': SIZE
            }
            
            with open('vpn_info.json', 'w') as f:
                json.dump(info, f, indent=2)
            
            print(f"\n✅ VPN сервер успешно развернут!")
            print(f"   Droplet ID: {droplet_id}")
            print(f"   Конфигурация: {config_file}")
            print(f"\n💡 Для удаления сервера:")
            print(f"   python3 delete_vpn.py")
        else:
            print("❌ Не удалось получить конфигурацию VPN")
    else:
        print("❌ Не удалось подключиться по SSH")

if __name__ == '__main__':
    main()
