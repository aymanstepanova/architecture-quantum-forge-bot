#!/bin/sh
set -eu

SCHEDULE="${CRON_SCHEDULE:-0 6 * * *}"

echo "[entrypoint] CRON_SCHEDULE=$SCHEDULE"

# /etc/cron.d формат требует: <schedule> <user> <command>
CRON_FILE="/etc/cron.d/update_index"
echo "$SCHEDULE root cd /app && python update_index.py >> /var/log/update_index_cron.log 2>&1" > "$CRON_FILE"
chmod 0644 "$CRON_FILE"

# Логи cron (удобно смотреть docker logs)
touch /var/log/update_index_cron.log

echo "[entrypoint] Installed cron job:"
cat "$CRON_FILE"

# Запускаем cron в foreground
exec cron -f

