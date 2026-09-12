FROM python:3.11-slim

WORKDIR /app

COPY dependencias.txt .
RUN pip install --no-cache-dir -r dependencias.txt

COPY app ./app

EXPOSE 9000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "9000"]
