# Инструкция по развертыванию VPN сервера

## Быстрый старт

### 1. Получите API токен DigitalOcean

1. Перейдите на https://cloud.digitalocean.com/account/api/tokens
2. Нажмите "Generate New Token"
3. Дайте имя токену (например, "VPN Deployment")
4. Выберите "Write" права
5. Скопируйте токен

### 2. Установите токен

**Вариант A: Для Python скрипта**
```bash
export DIGITALOCEAN_ACCESS_TOKEN='your-token-here'
```

**Вариант B: Для doctl**
```bash
doctl auth init
# Введите токен когда попросит
```

### 3. Запустите развертывание

**Через Python (рекомендуется):**
```bash
cd vpn
pip3 install -r requirements.txt
python3 deploy_vpn.py
```

**Через doctl:**
```bash
cd vpn
./deploy_vpn_doctl.sh
```

### 4. Получите конфигурацию

После успешного развертывания:
- Конфигурация будет в файле `wg0.conf`
- Информация о сервере в `vpn_info.json`

### 5. Подключитесь к VPN

1. Установите WireGuard клиент
2. Импортируйте файл `wg0.conf`
3. Подключитесь

## Удаление

```bash
cd vpn
python3 delete_vpn.py
# или
./delete_vpn_doctl.sh
```

## Стоимость

- **Droplet:** ~$6/месяц (s-1vcpu-1gb)
- **Трафик:** Включен

## GitHub

Код доступен в репозитории: https://github.com/truemanD/calendar-app/tree/main/vpn
