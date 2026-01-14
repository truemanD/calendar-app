# WireGuard VPN Server на DigitalOcean

Автоматическое развертывание WireGuard VPN сервера на DigitalOcean.

## Требования

- Python 3.7+
- DigitalOcean API токен
- SSH ключ (будет создан автоматически)

## Установка

1. Установите зависимости:
```bash
pip install -r requirements.txt
```

2. Установите переменную окружения с токеном DigitalOcean:
```bash
export DIGITALOCEAN_ACCESS_TOKEN='your-token-here'
```

Получить токен можно здесь: https://cloud.digitalocean.com/account/api/tokens

## Использование

### Развертывание VPN сервера

```bash
python3 deploy_vpn.py
```

Скрипт автоматически:
- Создаст SSH ключ (если его нет)
- Создаст droplet с Ubuntu 22.04
- Установит и настроит WireGuard
- Сгенерирует конфигурацию клиента
- Сохранит конфигурацию в `wg0.conf`

### Подключение к VPN

1. **Установите WireGuard клиент:**
   - Windows/Mac/Linux: https://www.wireguard.com/install/
   - iOS: App Store
   - Android: Google Play

2. **Импортируйте конфигурацию:**
   - Откройте WireGuard клиент
   - Импортируйте файл `wg0.conf`
   - Или отсканируйте QR код (если доступен)

3. **Подключитесь к VPN**

### Удаление VPN сервера

```bash
python3 delete_vpn.py
```

## Конфигурация

По умолчанию используется:
- **Регион:** Frankfurt (fra1) - один из самых дешевых
- **Размер:** s-1vcpu-1gb - самый дешевый ($6/месяц)
- **ОС:** Ubuntu 22.04

Изменить можно в файле `deploy_vpn.py`:
```python
REGION = "fra1"  # Измените на нужный регион
SIZE = "s-1vcpu-1gb"  # Измените на нужный размер
```

## Стоимость

- **Droplet:** ~$6/месяц (s-1vcpu-1gb)
- **Трафик:** Включен в стоимость droplet

## Файлы

- `deploy_vpn.py` - скрипт развертывания
- `delete_vpn.py` - скрипт удаления
- `wg0.conf` - конфигурация WireGuard клиента (создается после развертывания)
- `vpn_info.json` - информация о развернутом сервере

## Безопасность

- SSH ключ хранится в `~/.ssh/vpn_do_key`
- Приватный ключ WireGuard хранится только на сервере
- Конфигурация клиента содержит только необходимые данные

## Устранение неполадок

### SSH подключение не работает

Проверьте, что:
1. Droplet активен и имеет IP адрес
2. SSH ключ правильно создан
3. Firewall не блокирует подключение

### VPN не подключается

Проверьте:
1. WireGuard запущен на сервере: `systemctl status wg-quick@wg0`
2. Порт 51820 открыт в firewall
3. Endpoint IP адрес правильный в конфигурации

### Получить информацию о сервере

```bash
ssh -i ~/.ssh/vpn_do_key root@<IP_ADDRESS>
systemctl status wg-quick@wg0
wg show
```
