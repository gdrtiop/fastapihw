## Важно!
Лежит только `.env.example`, чтобы всё работало нужно создать свой `.env` в соответствии с примером

---
 
## Запуск
 
```bash
docker compose up --build -d
```
 
Сервис: `http://localhost:8000/`
 
Данные хранятся в volumes и сохраняются при перезапуске. Сбросить:
```bash
docker compose down --volumes
```
 
---
 
## Docker Swarm
 
```bash
docker swarm init
docker build -t fastapi_app:latest .
export $(cat .env | xargs)
docker stack deploy -c docker-compose.swarm.yml taskstack
docker stack services taskstack
```
 
Остановка:
```bash
docker stack rm taskstack
docker swarm leave --force
```

---

## Тесты

### Запуск тестов
```bash
pytest tests/
```

### Запуск с отчётом покрытия
```bash
coverage run -m pytest tests/
coverage report
```

### Генерация HTML-отчёта покрытия
```bash
coverage html
```

## Результаты

### Покрытие кода
HTML-отчёт лежит в `htmlcov/index.html`

Итоговое покрытие: **90%**

### Результаты тестов
Лежат в `test_results.txt`

### Нагрузочное тестирование
HTML-отчёт лежит в `load_test_results.html`

20 пользователей, 30 секунд, 902 запроса:
- 0 failures
- медиана ответа: 8ms
- RPS: ~31

### Запуск нагрузочных тестов
Нужен запущенный `docker compose up --build`, затем:
```bash
locust -f tests/locustfile.py --headless -u 20 -r 5 -t 30s --host http://localhost:8000
```