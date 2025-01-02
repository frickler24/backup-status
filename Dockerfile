FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -git ap /app/logdir
USER nobody

CMD ["python3", "backup-report.py"]
