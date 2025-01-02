FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /app/logdir && chmod 777 /app/logdir
USER nobody
RUN ls -lsa /app/logdir

CMD ["python3", "backup-report.py"]
