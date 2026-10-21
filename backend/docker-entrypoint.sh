#!/bin/sh
set -e
echo "Aplicando migraciones Alembic…"
alembic upgrade head
exec "$@"
