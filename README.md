# VideoFramer

VideoFramer - це сервіс для обробки відео, який автоматично витягує ключові кадри, транскрибує аудіо та генерує описовий контент для блогерів та контент-мейкерів.

## Швидкий старт

1. Клонуйте репозиторій:
```bash
cd /root/Scripts
git clone https://github.com/ChornyiDev/videoframer.git
cd videoframer
```

2. Створіть віртуальне середовище та встановіть залежності:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

3. Встановіть FFmpeg та Redis:
```bash
# Встановлення FFmpeg
sudo apt-get update
sudo apt-get install ffmpeg

# Встановлення Redis
sudo apt-get install redis-server

# Налаштування Redis для автозапуску
sudo systemctl enable redis-server
sudo systemctl start redis-server

# Перевірка статусу Redis
sudo systemctl status redis-server
```

4. Налаштуйте Redis:
```bash
# Відкрийте конфіг Redis
sudo nano /etc/redis/redis.conf
```

Важливі налаштування в redis.conf:
```conf
# Прослуховування всіх інтерфейсів (за замовчуванням тільки localhost)
bind 0.0.0.0

# Порт (за замовчуванням 6379)
port 6379

# Налаштування пам'яті (приклад: 256MB)
maxmemory 256mb
maxmemory-policy allkeys-lru

# Налаштування персистентності
save 900 1
save 300 10
save 60 10000
```

Після зміни конфігурації перезапустіть Redis:
```bash
sudo systemctl restart redis-server
```

5. Створіть файл .env з необхідними змінними оточення:
```env
OPENAI_API_KEY=your-api-key
REDIS_URL=redis://localhost:6379
WEBHOOK_URL=your-webhook-url

# Optional settings
CACHE_ENABLED=true
ENABLE_GZIP=false
MAX_VIDEO_SIZE=52428800  # 50MB in bytes
```

## Налаштування системного сервісу

1. Створіть файл сервісу для FastAPI:
```bash
sudo nano /etc/systemd/system/videoframer.service
```

Додайте наступний конфіг:
```ini
[Unit]
Description=VideoFramer FastAPI Service
After=network.target

[Service]
User=root
WorkingDirectory=/root/Scripts/videoframer
Environment="PATH=/root/Scripts/videoframer/.venv/bin"
EnvironmentFile=/root/Scripts/videoframer/.env
ExecStart=/root/Scripts/videoframer/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

2. Створіть файл сервісу для Celery:
```bash
sudo nano /etc/systemd/system/videoframer-worker.service
```

Додайте наступний конфіг:
```ini
[Unit]
Description=VideoFramer Celery Worker
After=network.target

[Service]
User=root
WorkingDirectory=/root/Scripts/videoframer
Environment="PATH=/root/Scripts/videoframer/.venv/bin"
EnvironmentFile=/root/Scripts/videoframer/.env
ExecStart=/root/Scripts/videoframer/.venv/bin/celery -A celery_worker.celery_app worker --loglevel=info
Restart=always

[Install]
WantedBy=multi-user.target
```

3. Активуйте та запустіть сервіси:
```bash
# Перезавантажте systemd
sudo systemctl daemon-reload

# Активуйте сервіси
sudo systemctl enable videoframer
sudo systemctl enable videoframer-worker

# Запустіть сервіси
sudo systemctl start videoframer
sudo systemctl start videoframer-worker
```

4. Перевірте статус сервісів:
```bash
sudo systemctl status videoframer
sudo systemctl status videoframer-worker
```

5. Перегляд логів:
```bash
# Для FastAPI
sudo journalctl -u videoframer -f

# Для Celery
sudo journalctl -u videoframer-worker -f
```

## Корисні команди для управління сервісом

```bash
# Перезапуск сервісів
sudo systemctl restart videoframer
sudo systemctl restart videoframer-worker

# Зупинка сервісів
sudo systemctl stop videoframer
sudo systemctl stop videoframer-worker

# Перевірка статусу Redis
sudo systemctl status redis
```

## Функціональність

- Завантаження відео за URL
- Витяг ключових кадрів з відео
- Транскрипція аудіо за допомогою OpenAI Whisper
- Генерація описового контенту на основі кадрів та транскрипції
- Асинхронна обробка з використанням Celery
- Кешування результатів у Redis
- Відправка результатів через вебхуки

## Структура проекту

```
videoframer/
├── app/
│   ├── core/
│   │   ├── celery_app.py    # Конфігурація Celery
│   │   ├── config.py        # Налаштування застосунку
│   │   └── redis_client.py  # Клієнт Redis для кешування
│   ├── services/
│   │   └── video_service.py # Сервіс обробки відео
│   └── main.py             # FastAPI застосунок
├── .env                    # Змінні оточення
└── celery_worker.py       # Воркер Celery
```

## Конфігурація

Налаштування здійснюється через змінні оточення в файлі `.env`:

```env
OPENAI_API_KEY=your-api-key
REDIS_URL=redis://localhost:6379
WEBHOOK_URL=your-webhook-url
```

### Основні налаштування (config.py)

- `MAX_VIDEO_SIZE`: Максимальний розмір відео (50MB)
- `MAX_FRAMES`: Максимальна кількість кадрів (8)
- `JPEG_QUALITY`: Якість JPEG (70)
- `CACHE_EXPIRE_TIME`: Час життя кешу (24 години)
- `CELERY_TASK_TIME_LIMIT`: Ліміт часу завдання (2 хвилини)
- `CELERY_WORKER_CONCURRENCY`: Кількість паралельних завдань (2)

### Правила витягу кадрів

- Відео до 30 секунд: кадри кожні 5 секунд
- Відео 30-60 секунд: кадри кожні 10 секунд
- Відео довше 60 секунд: кадри кожні 20 секунд

## Оптимізації

1. **Мережеві оптимізації:**
   - Обмеження розміру відео (50MB)
   - GZIP стиснення для API відповідей
   - Валідація відео перед завантаженням

2. **Оптимізації обробки:**
   - Зменшення розміру кадрів до 512px
   - Оптимізація якості JPEG
   - Конвертація аудіо в моно з бітрейтом 48k

3. **Кешування:**
   - Кешування результатів обробки в Redis
   - Унікальні ключі кешу на основі URL та промпту
   - Автоматичне очищення кешу після 24 годин

## Вимоги до системи

- Python 3.8+
- Redis
- FFmpeg
- OpenAI API ключ

## Залежності

Основні залежності проекту:
```
fastapi
celery
redis
httpx
python-dotenv
moviepy
Pillow
openai
```

## Моніторинг та логування

- Детальне логування процесу обробки відео
- Логування помилок вебхуків
- Моніторинг статусу завдань Celery

## Обробка помилок

- Валідація розміру та формату відео
- Обробка помилок завантаження
- Обробка помилок транскрипції
- Обробка помилок вебхуків

## Безпека

- Валідація URL відео
- Обмеження розміру файлів
- Безпечне зберігання API ключів
- Тимчасові директорії для файлів
