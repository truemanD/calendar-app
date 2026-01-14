#!/bin/bash
# Скрипт для развертывания WireGuard VPN через doctl

set -e

DROPLET_NAME="vpn-server"
REGION="fra1"
SIZE="s-1vcpu-1gb"
IMAGE="ubuntu-22-04-x64"

echo "============================================================"
echo "🚀 Развертывание WireGuard VPN сервера на DigitalOcean"
echo "============================================================"

# Проверяем doctl
if ! command -v doctl &> /dev/null; then
    echo "❌ doctl не установлен. Установите: brew install doctl"
    exit 1
fi

# Проверяем авторизацию
if ! doctl auth list &> /dev/null; then
    echo "🔐 Требуется авторизация..."
    doctl auth init
fi

# Создаем SSH ключ если его нет
SSH_KEY_PATH="$HOME/.ssh/vpn_do_key"
if [ ! -f "$SSH_KEY_PATH" ]; then
    echo "🔑 Создание SSH ключа..."
    ssh-keygen -t ed25519 -f "$SSH_KEY_PATH" -N "" -C "vpn-server-key" -q
fi

# Получаем публичный ключ
PUBLIC_KEY=$(cat "${SSH_KEY_PATH}.pub")

# Проверяем/создаем SSH ключ в DigitalOcean
echo "🔑 Проверка SSH ключа в DigitalOcean..."
SSH_KEY_ID=$(doctl compute ssh-key list --format ID,Name,PublicKey --no-header | grep -F "$PUBLIC_KEY" | awk '{print $1}' | head -1)

if [ -z "$SSH_KEY_ID" ]; then
    echo "🔑 Добавление SSH ключа в DigitalOcean..."
    SSH_KEY_ID=$(doctl compute ssh-key create vpn-ssh-key --public-key-file "${SSH_KEY_PATH}.pub" --format ID --no-header)
    echo "✅ SSH ключ создан: $SSH_KEY_ID"
else
    echo "✅ SSH ключ уже существует: $SSH_KEY_ID"
fi

# User data для установки WireGuard
USER_DATA=$(cat <<'EOF'
#!/bin/bash
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq wireguard wireguard-tools iptables qrencode curl

# Включаем IP forwarding
echo "net.ipv4.ip_forward=1" >> /etc/sysctl.conf
sysctl -p > /dev/null

# Создаем конфигурацию WireGuard
mkdir -p /etc/wireguard
cd /etc/wireguard

# Генерируем ключи сервера
wg genkey | tee server_private.key | wg pubkey > server_public.key
SERVER_PRIVATE=$(cat server_private.key)
SERVER_PUBLIC=$(cat server_public.key)

# Генерируем ключи клиента
wg genkey | tee client_private.key | wg pubkey > client_public.key
CLIENT_PRIVATE=$(cat client_private.key)
CLIENT_PUBLIC=$(cat client_public.key)

# Получаем IP сервера
SERVER_IP=$(curl -s ifconfig.me)

# Создаем конфигурацию сервера
cat > /etc/wireguard/wg0.conf <<WGEOF
[Interface]
PrivateKey = $SERVER_PRIVATE
Address = 10.0.0.1/24
ListenPort = 51820
PostUp = iptables -A FORWARD -i wg0 -j ACCEPT; iptables -A FORWARD -o wg0 -j ACCEPT; iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE
PostDown = iptables -D FORWARD -i wg0 -j ACCEPT; iptables -D FORWARD -o wg0 -j ACCEPT; iptables -t nat -D POSTROUTING -o eth0 -j MASQUERADE

[Peer]
PublicKey = $CLIENT_PUBLIC
AllowedIPs = 10.0.0.2/32
WGEOF

# Запускаем WireGuard
systemctl enable wg-quick@wg0
systemctl start wg-quick@wg0

# Создаем конфигурацию клиента
cat > /root/client.conf <<CLIENTEOF
[Interface]
PrivateKey = $CLIENT_PRIVATE
Address = 10.0.0.2/24
DNS = 8.8.8.8

[Peer]
PublicKey = $SERVER_PUBLIC
Endpoint = $SERVER_IP:51820
AllowedIPs = 0.0.0.0/0
PersistentKeepalive = 25
CLIENTEOF

# Генерируем QR код
qrencode -t ansiutf8 < /root/client.conf > /root/qr_code.txt 2>/dev/null || true

# Сохраняем информацию
cat > /root/vpn_info.txt <<INFOEOF
=== WireGuard VPN Server ===
Server IP: $SERVER_IP
Server Public Key: $SERVER_PUBLIC
Client Public Key: $CLIENT_PUBLIC
Port: 51820
Client config: /root/client.conf
INFOEOF

echo "VPN Server Setup Complete" > /root/setup_complete.txt
EOF
)

# Сохраняем user data во временный файл
USER_DATA_FILE=$(mktemp)
echo "$USER_DATA" > "$USER_DATA_FILE"

echo "🚀 Создание droplet..."
DROPLET_ID=$(doctl compute droplet create "$DROPLET_NAME" \
    --region "$REGION" \
    --size "$SIZE" \
    --image "$IMAGE" \
    --ssh-keys "$SSH_KEY_ID" \
    --user-data-file "$USER_DATA_FILE" \
    --wait \
    --format ID --no-header)

rm "$USER_DATA_FILE"

if [ -z "$DROPLET_ID" ]; then
    echo "❌ Ошибка создания droplet"
    exit 1
fi

echo "✅ Droplet создан: $DROPLET_ID"

# Получаем IP адрес
echo "⏳ Получение IP адреса..."
sleep 10

MAX_ATTEMPTS=30
for i in $(seq 1 $MAX_ATTEMPTS); do
    DROPLET_IP=$(doctl compute droplet get "$DROPLET_ID" --format PublicIPv4 --no-header | head -1)
    if [ -n "$DROPLET_IP" ] && [ "$DROPLET_IP" != "null" ]; then
        break
    fi
    echo "   Попытка $i/$MAX_ATTEMPTS..."
    sleep 5
done

if [ -z "$DROPLET_IP" ] || [ "$DROPLET_IP" = "null" ]; then
    echo "❌ Не удалось получить IP адрес"
    exit 1
fi

echo "✅ IP адрес: $DROPLET_IP"

# Ждем доступности SSH
echo "⏳ Ожидание доступности SSH..."
MAX_ATTEMPTS=30
for i in $(seq 1 $MAX_ATTEMPTS); do
    if ssh -i "$SSH_KEY_PATH" -o ConnectTimeout=5 -o StrictHostKeyChecking=no root@"$DROPLET_IP" "echo 'SSH ready'" &>/dev/null; then
        echo "✅ SSH доступен!"
        break
    fi
    echo "   Попытка $i/$MAX_ATTEMPTS..."
    sleep 5
done

# Ждем установки WireGuard
echo "⏳ Ожидание установки WireGuard..."
MAX_ATTEMPTS=40
for i in $(seq 1 $MAX_ATTEMPTS); do
    if ssh -i "$SSH_KEY_PATH" -o StrictHostKeyChecking=no root@"$DROPLET_IP" "test -f /root/setup_complete.txt" &>/dev/null; then
        echo "✅ WireGuard установлен!"
        break
    fi
    echo "   Попытка $i/$MAX_ATTEMPTS..."
    sleep 5
done

# Получаем конфигурацию клиента
echo "📥 Получение конфигурации VPN..."
sleep 5

CLIENT_CONFIG=$(ssh -i "$SSH_KEY_PATH" -o StrictHostKeyChecking=no root@"$DROPLET_IP" "cat /root/client.conf" 2>/dev/null)

if [ -z "$CLIENT_CONFIG" ]; then
    echo "❌ Не удалось получить конфигурацию"
    exit 1
fi

# Обновляем Endpoint с реальным IP
CLIENT_CONFIG=$(echo "$CLIENT_CONFIG" | sed "s/Endpoint = .*/Endpoint = $DROPLET_IP:51820/")

# Сохраняем конфигурацию
CONFIG_FILE="wg0.conf"
echo "$CLIENT_CONFIG" > "$CONFIG_FILE"
echo "✅ Конфигурация сохранена в $CONFIG_FILE"

# Сохраняем информацию
INFO_FILE="vpn_info.json"
cat > "$INFO_FILE" <<EOF
{
  "droplet_id": $DROPLET_ID,
  "ip": "$DROPLET_IP",
  "name": "$DROPLET_NAME",
  "region": "$REGION",
  "size": "$SIZE"
}
EOF

# Получаем QR код если доступен
QR_CODE=$(ssh -i "$SSH_KEY_PATH" -o StrictHostKeyChecking=no root@"$DROPLET_IP" "cat /root/qr_code.txt" 2>/dev/null || echo "")

echo ""
echo "============================================================"
echo "✅ VPN сервер успешно развернут!"
echo "============================================================"
echo ""
echo "📋 Информация о сервере:"
echo "   Droplet ID: $DROPLET_ID"
echo "   IP адрес: $DROPLET_IP"
echo "   Порт: 51820"
echo "   Протокол: WireGuard"
echo ""
echo "📱 Для подключения:"
echo "   1. Установите WireGuard клиент"
echo "   2. Импортируйте файл: $CONFIG_FILE"
echo ""

if [ -n "$QR_CODE" ]; then
    echo "📱 QR код для подключения:"
    echo "$QR_CODE"
    echo ""
fi

echo "💡 Для удаления сервера:"
echo "   ./delete_vpn_doctl.sh"
echo ""
