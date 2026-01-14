#!/usr/bin/env python3
"""
Скрипт для автоматического развертывания OpenVPN сервера на DigitalOcean
"""

import os
import sys
import json
import time
import subprocess
import requests
from pathlib import Path

# Конфигурация
DROPLET_NAME = "openvpn-server"
REGION = "fra1"  # Frankfurt - один из самых дешевых регионов
SIZE = "s-1vcpu-1gb"  # Самый дешевый размер
IMAGE = "ubuntu-22-04-x64"
SSH_KEY_NAME = "openvpn-ssh-key"

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
    key_path = Path.home() / ".ssh" / "openvpn_do_key"
    pub_key_path = key_path.with_suffix('.pub')
    
    if not key_path.exists():
        subprocess.run([
            'ssh-keygen', '-t', 'ed25519', '-f', str(key_path),
            '-N', '', '-C', 'openvpn-server-key'
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
    """Создать droplet с OpenVPN сервером"""
    print(f"🚀 Создание droplet {DROPLET_NAME}...")
    
    # User data скрипт для установки OpenVPN
    user_data = """#!/bin/bash
export DEBIAN_FRONTEND=noninteractive

# Обновляем систему
apt-get update -qq
apt-get upgrade -y -qq

# Устанавливаем OpenVPN и Easy-RSA
apt-get install -y -qq openvpn easy-rsa iptables curl

# Включаем IP forwarding
echo "net.ipv4.ip_forward=1" >> /etc/sysctl.conf
sysctl -p > /dev/null

# Настраиваем firewall
iptables -t nat -A POSTROUTING -s 10.8.0.0/24 -o eth0 -j MASQUERADE
iptables -A FORWARD -i tun0 -o eth0 -s 10.8.0.0/24 -j ACCEPT
iptables -A FORWARD -i eth0 -o tun0 -d 10.8.0.0/24 -j ACCEPT

# Сохраняем правила iptables
mkdir -p /etc/iptables
iptables-save > /etc/iptables/rules.v4

# Создаем скрипт для восстановления правил при перезагрузке
cat > /etc/network/if-up.d/iptables <<'IPTABLES_EOF'
#!/bin/bash
iptables-restore < /etc/iptables/rules.v4
IPTABLES_EOF
chmod +x /etc/network/if-up.d/iptables

# Настраиваем Easy-RSA
cd /etc/openvpn
make-cadir /etc/openvpn/easy-rsa
cd /etc/openvpn/easy-rsa

# Настраиваем переменные
cat > vars <<'VARS_EOF'
export KEY_COUNTRY="US"
export KEY_PROVINCE="CA"
export KEY_CITY="SanFrancisco"
export KEY_ORG="OpenVPN"
export KEY_EMAIL="admin@openvpn.local"
export KEY_OU="MyOrganizationalUnit"
export KEY_NAME="server"
VARS_EOF

# Инициализируем PKI
./easyrsa init-pki <<< "yes"
./easyrsa --batch build-ca nopass
./easyrsa --batch gen-req server nopass
./easyrsa --batch sign-req server server
./easyrsa gen-dh

# Генерируем ключ для TLS
openvpn --genkey --secret ta.key

# Создаем конфигурацию сервера
cat > /etc/openvpn/server.conf <<'SERVER_EOF'
port 1194
proto udp
dev tun
ca /etc/openvpn/easy-rsa/pki/ca.crt
cert /etc/openvpn/easy-rsa/pki/issued/server.crt
key /etc/openvpn/easy-rsa/pki/private/server.key
dh /etc/openvpn/easy-rsa/pki/dh.pem
tls-auth /etc/openvpn/easy-rsa/ta.key 0
server 10.8.0.0 255.255.255.0
ifconfig-pool-persist ipp.txt
push "redirect-gateway def1 bypass-dhcp"
push "dhcp-option DNS 8.8.8.8"
push "dhcp-option DNS 8.8.4.4"
keepalive 10 120
cipher AES-256-CBC
auth SHA256
user nobody
group nogroup
persist-key
persist-tun
status openvpn-status.log
verb 3
explicit-exit-notify 1
SERVER_EOF

# Создаем клиентский ключ
./easyrsa --batch gen-req client1 nopass
./easyrsa --batch sign-req client client1

# Получаем IP сервера
SERVER_IP=$(curl -s ifconfig.me)

# Создаем конфигурацию клиента
cat > /root/client1.ovpn <<CLIENT_EOF
client
dev tun
proto udp
remote $SERVER_IP 1194
resolv-retry infinite
nobind
persist-key
persist-tun
ca [inline]
cert [inline]
key [inline]
tls-auth [inline] 1
cipher AES-256-CBC
auth SHA256
verb 3
redirect-gateway def1

<ca>
$(cat /etc/openvpn/easy-rsa/pki/ca.crt)
</ca>

<cert>
$(cat /etc/openvpn/easy-rsa/pki/issued/client1.crt)
</cert>

<key>
$(cat /etc/openvpn/easy-rsa/pki/private/client1.key)
</key>

<tls-auth>
$(cat /etc/openvpn/easy-rsa/ta.key)
</tls-auth>
CLIENT_EOF

# Запускаем OpenVPN
systemctl enable openvpn@server
systemctl start openvpn@server

# Сохраняем информацию
cat > /root/openvpn_info.txt <<INFO_EOF
=== OpenVPN Server Setup Complete ===
Server IP: $SERVER_IP
Port: 1194
Protocol: UDP
Client config: /root/client1.ovpn
INFO_EOF

echo "OpenVPN Server Setup Complete" > /root/setup_complete.txt
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
    
    key_path = Path.home() / ".ssh" / "openvpn_do_key"
    
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

def get_openvpn_config(ip):
    """Получить конфигурацию OpenVPN с сервера"""
    print("📥 Получение конфигурации OpenVPN...")
    
    key_path = Path.home() / ".ssh" / "openvpn_do_key"
    
    # Ждем пока OpenVPN установится
    print("⏳ Ожидание установки OpenVPN...")
    time.sleep(60)  # OpenVPN требует больше времени для установки
    
    max_attempts = 30
    for attempt in range(max_attempts):
        result = subprocess.run(
            ['ssh', '-i', str(key_path), '-o', 'StrictHostKeyChecking=no',
             f'root@{ip}', 'test -f /root/setup_complete.txt && echo "ready"'],
            capture_output=True,
            timeout=10
        )
        
        if result.returncode == 0 and b'ready' in result.stdout:
            break
        
        print(f"   Попытка {attempt + 1}/{max_attempts}...")
        time.sleep(10)
    
    # Получаем конфигурацию клиента
    result = subprocess.run(
        ['ssh', '-i', str(key_path), '-o', 'StrictHostKeyChecking=no',
         f'root@{ip}', 'cat /root/client1.ovpn'],
        capture_output=True,
        text=True,
        timeout=10
    )
    
    if result.returncode == 0:
        config = result.stdout
        # Обновляем IP адрес если нужно
        return config
    else:
        print(f"❌ Ошибка получения конфигурации: {result.stderr}")
        return None

def save_config(config, ip):
    """Сохранить конфигурацию в файл"""
    config_file = Path('client1.ovpn')
    with open(config_file, 'w') as f:
        f.write(config)
    
    print(f"✅ Конфигурация сохранена в {config_file}")
    print(f"\n📋 Информация о OpenVPN сервере:")
    print(f"   IP адрес: {ip}")
    print(f"   Порт: 1194")
    print(f"   Протокол: UDP")
    print(f"\n📱 Для подключения:")
    print(f"   1. Установите OpenVPN клиент")
    print(f"   2. Импортируйте файл {config_file}")
    print(f"   3. Подключитесь к VPN")
    
    return config_file

def main():
    print("=" * 60)
    print("🚀 Развертывание OpenVPN сервера на DigitalOcean")
    print("=" * 60)
    
    token = get_do_token()
    ssh_key_id = create_ssh_key(token)
    droplet_id = create_droplet(token, ssh_key_id)
    ip = wait_for_droplet(token, droplet_id)
    
    if wait_for_ssh(ip):
        config = get_openvpn_config(ip)
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
            
            with open('openvpn_info.json', 'w') as f:
                json.dump(info, f, indent=2)
            
            print(f"\n✅ OpenVPN сервер успешно развернут!")
            print(f"   Droplet ID: {droplet_id}")
            print(f"   Конфигурация: {config_file}")
            print(f"\n💡 Для удаления сервера:")
            print(f"   python3 delete_openvpn.py")
        else:
            print("❌ Не удалось получить конфигурацию OpenVPN")
    else:
        print("❌ Не удалось подключиться по SSH")

if __name__ == '__main__':
    main()
