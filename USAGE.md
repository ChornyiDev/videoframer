# Використання VideoFramer

## Запуск проекту

1. **Встановлення залежностей:**
```bash
python -m venv .venv
source .venv/bin/activate  # для Linux/Mac
pip install -r requirements.txt
```

2. **Запуск Redis:**
```bash
redis-server
```

3. **Запуск Celery worker:**
```bash
celery -A celery_worker.celery_app worker --loglevel=info
```

4. **Запуск FastAPI сервера:**
```bash
uvicorn app.main:app --reload
```

## API Endpoints

### POST /process

Запускає обробку відео.

#### Request Body

```json
{
    "video_url": "https://example.com/video.mp4",
    "system_prompt": "Optional custom prompt for video description",
    "metadata": {
        "Post Rec ID": "rec203Zwfn0lV9u7G",
        "Config Rec ID": "recEMgrOdYxMK5UvP",
        "User Rec ID": "rec7q2YUCwU4aZn29"
    }
}
```

| Поле | Тип | Опис |
|------|-----|------|
| video_url | string | URL відео для обробки |
| system_prompt | string | (Опціонально) Кастомний промпт для опису відео |
| metadata | object | (Опціонально) Додаткові параметри, які будуть передані у вебхук |

#### Response

```json
{
    "task_id": "8b2c7b9a-1234-5678-90ab-cdef12345678",
    "status": "Processing started"
}
```

### Webhook Response

Після обробки відео, результат буде відправлено на вказаний webhook URL з наступною структурою:

```json
{
    "frames": [
        {
            "timestamp": "00:00:05",
            "description": "Description of the frame"
        }
    ],
    "transcription": "Full video transcription...",
    "description": "Complete video description",
    "Post Rec ID": "rec203Zwfn0lV9u7G",
    "Config Rec ID": "recEMgrOdYxMK5UvP",
    "User Rec ID": "rec7q2YUCwU4aZn29"
}
```

### GET /health

Перевірка статусу сервісу.

#### Response

```json
{
    "status": "healthy"
}
```

## Приклади використання

### cURL

```bash
curl -X POST "http://localhost:8000/process" \
     -H "Content-Type: application/json" \
     -d '{
         "video_url": "https://storage.magicboxpremium.com/preview/result_20241220_072759_f1cb62ca.mp4",
         "metadata": {
             "Post Rec ID": "rec203Zwfn0lV9u7G",
             "Config Rec ID": "recEMgrOdYxMK5UvP",
             "User Rec ID": "rec7q2YUCwU4aZn29"
         }
     }'
```

### Python

```python
import requests

url = "http://localhost:8000/process"
data = {
    "video_url": "https://storage.magicboxpremium.com/preview/result_20241220_072759_f1cb62ca.mp4",
    "metadata": {
        "Post Rec ID": "rec203Zwfn0lV9u7G",
        "Config Rec ID": "recEMgrOdYxMK5UvP",
        "User Rec ID": "rec7q2YUCwU4aZn29"
    }
}

response = requests.post(url, json=data)
print(response.json())
```

## Обробка помилок

Сервіс повертає наступні HTTP коди помилок:

- 400: Неправильний формат запиту
- 404: Відео не знайдено
- 413: Розмір відео перевищує ліміт
- 500: Внутрішня помилка сервера

## Обмеження

- Максимальний розмір відео: 50MB
- Підтримувані формати: MP4, MOV, AVI, WMV
- Максимальний час обробки: 2 хвилини

## Налаштування через змінні оточення

Створіть файл `.env` з наступними змінними:

```env
# Обов'язкові
OPENAI_API_KEY=your-api-key
REDIS_URL=redis://localhost:6379
WEBHOOK_URL=your-webhook-url

# Опціональні
CACHE_ENABLED=true
ENABLE_GZIP=true
```

## Типові помилки та їх вирішення

1. **"Video size exceeds maximum allowed size"**
   - Переконайтеся, що розмір відео менше 50MB
   - Стисніть відео перед завантаженням

2. **"Invalid video format"**
   - Використовуйте підтримувані формати (MP4, MOV, AVI, WMV)
   - Конвертуйте відео в підтримуваний формат

3. **"Task timeout"**
   - Зменшіть тривалість відео
   - Збільште `CELERY_TASK_TIME_LIMIT` в налаштуваннях

4. **"Webhook error"**
   - Перевірте доступність вебхук URL
   - Перевірте формат даних, що відправляються
