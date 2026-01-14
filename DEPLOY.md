# Инструкция по публикации календаря на DigitalOcean

## Вариант 1: Через веб-интерфейс (Самый простой способ)

1. **Подготовьте код для GitHub:**
   ```bash
   git init
   git add .
   git commit -m "Initial commit: Calendar app"
   git remote add origin https://github.com/YOUR_USERNAME/calendar-app.git
   git push -u origin main
   ```

2. **Создайте приложение на DigitalOcean:**
   - Перейдите на https://cloud.digitalocean.com/apps
   - Нажмите "Create App"
   - Выберите "GitHub" как источник
   - Авторизуйтесь и выберите репозиторий `calendar-app`
   - Выберите ветку `main`

3. **Настройте Static Site:**
   - DigitalOcean автоматически определит тип как "Static Site"
   - Убедитесь, что:
     - **Build Command:** `echo "No build needed"` (или оставьте пустым)
     - **Output Directory:** `/` (корневая директория)
   - Нажмите "Next"

4. **Выберите план:**
   - Выберите самый дешевый план (обычно бесплатный для первых 3 статических сайтов)
   - Нажмите "Create Resources"

5. **Дождитесь деплоя:**
   - Приложение будет развернуто автоматически
   - Вы получите URL вида: `https://calendar-app-xxxxx.ondigitalocean.app`

## Вариант 2: Через DigitalOcean CLI

Если у вас установлен `doctl`:

```bash
# Установите doctl, если еще не установлен
# macOS: brew install doctl
# Linux: https://docs.digitalocean.com/reference/doctl/how-to/install/

# Авторизуйтесь
doctl auth init

# Создайте приложение
doctl apps create --spec .do/app.yaml
```

**Важно:** Перед этим обновите `.do/app.yaml` с вашим GitHub репозиторием.

## Вариант 3: Прямая загрузка (через веб-интерфейс)

1. Перейдите на https://cloud.digitalocean.com/apps
2. Нажмите "Create App"
3. Выберите "Upload Source Code"
4. Загрузите ZIP-архив с файлами проекта
5. Настройте как Static Site

## Стоимость

- **Бесплатно:** Первые 3 статических сайта на DigitalOcean App Platform
- **После:** $3/месяц за каждый дополнительный статический сайт

Это самый дешевый вариант для хостинга статического веб-приложения!

## Проверка работы

После деплоя откройте URL приложения и проверьте:
- ✅ Календарь отображается корректно
- ✅ Навигация по месяцам работает
- ✅ Можно добавлять события
- ✅ События сохраняются (в localStorage браузера)

## Обновление приложения

Если вы используете GitHub:
- Просто сделайте `git push` в репозиторий
- DigitalOcean автоматически задеплоит изменения

Если используете прямую загрузку:
- Загрузите новый ZIP-архив через веб-интерфейс
