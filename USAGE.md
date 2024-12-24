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

**Запит:**
```bash
curl -X POST "http://localhost:8000/process" \
     -H "Content-Type: application/json" \
     -d '{
           "video_url": "https://example.com/video.mp4",
           "system_prompt": "Analyze this video for social media content"
         }'
```

**Відповідь:**
```json
{
    "status": "processing",
    "task_id": "3d942ae3-5ff3-4769-b6ea-d9debf6b6c9a",
    "message": "Video processing started. Results will be sent to webhook."
}
```

### GET /health

Перевіряє статус сервісу.

```bash
curl "http://localhost:8000/health"
```

## Формат вебхук відповіді

```json
{
    "status": "success",
    "transcription": "Повний текст транскрипції...",
    "description": "Детальний опис відео...",
    "word_count": 98
}
```

## Приклади використання

### 1. Обробка короткого відео

```bash
curl -X POST "http://localhost:8000/process" \
     -H "Content-Type: application/json" \
     -d '{
           "video_url": "https://example.com/short-video.mp4"
         }'
```

### 2. Обробка з кастомним промптом

```bash
curl -X POST "http://localhost:8000/process" \
     -H "Content-Type: application/json" \
     -d '{
           "video_url": "https://example.com/video.mp4",
           "system_prompt": "Analyze this video focusing on technical tutorials and educational content"
         }'
```

### 3. Обробка відео для соціальних мереж

```bash
curl -X POST "http://localhost:8000/process" \
     -H "Content-Type: application/json" \
     -d '{
           "video_url": "https://example.com/social-video.mp4",
           "system_prompt": "Create engaging social media content with hashtags and key points"
         }'
```

## Обмеження та вимоги

1. **Формати відео:**
   - MP4
   - QuickTime
   - AVI

2. **Обмеження:**
   - Максимальний розмір: 50MB
   - Максимальна кількість кадрів: 8
   - Таймаут завдання: 2 хвилини

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
   - Використовуйте підтримувані формати (MP4, QuickTime, AVI)
   - Конвертуйте відео в підтримуваний формат

3. **"Task timeout"**
   - Зменшіть тривалість відео
   - Збільште `CELERY_TASK_TIME_LIMIT` в налаштуваннях

4. **"Webhook error"**
   - Перевірте доступність вебхук URL
   - Перевірте формат даних, що відправляються
