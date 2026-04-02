FROM python:3.11-slim

WORKDIR /app

COPY ingestion/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ingestion/ingest.py .

CMD ["python", "ingest.py"]