FROM python:3.11-slim

WORKDIR /app

COPY dependencias.txt .
RUN pip install --no-cache-dir -r dependencias.txt

COPY app ./app

EXPOSE 8000

CMD ["python", "-m", "app.server"]