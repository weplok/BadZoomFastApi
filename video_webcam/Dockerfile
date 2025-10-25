# Используем легковесный официальный Python образ
FROM python:3.11-slim

# Рабочая директория внутри контейнера
WORKDIR /app

# Копируем файл зависимостей в контейнер
COPY requirements.txt .

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем все файлы проекта в контейнер
COPY . .

# Открываем порт 8000
EXPOSE 8008

# Запуск uvicorn с вашим приложением
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8008"]
