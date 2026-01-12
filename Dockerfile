FROM python:3.11-slim

# cron нужен для встроенного планировщика в Docker
RUN apt-get update \
  && apt-get install -y --no-install-recommends cron \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Сначала зависимости (лучше кешируется)
COPY requirements_task6.txt /app/requirements_task6.txt
RUN pip install --no-cache-dir -r /app/requirements_task6.txt

# Потом код
COPY . /app

RUN chmod +x /app/entrypoint.sh

ENV CRON_SCHEDULE="0 6 * * *"

ENTRYPOINT ["/app/entrypoint.sh"]

