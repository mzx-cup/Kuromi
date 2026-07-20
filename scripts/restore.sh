#!/bin/bash
# ============================================================================
# 星识 (Star-Learn) 数据库恢复脚本
# 用途：从备份文件恢复 MySQL 数据
# 用法：
#   ./scripts/restore.sh backups/db/xingshi_20260720_030000.sql.gz
# ============================================================================

set -euo pipefail

if [ $# -ne 1 ]; then
    echo "Usage: $0 <backup-file.sql.gz>"
    echo "Example: $0 backups/db/xingshi_20260720_030000.sql.gz"
    exit 1
fi

BACKUP_FILE="$1"

if [ ! -f "$BACKUP_FILE" ]; then
    echo "ERROR: Backup file not found: $BACKUP_FILE"
    exit 1
fi

# ─── 配置 ───
MYSQL_HOST="${MYSQL_HOST:-127.0.0.1}"
MYSQL_PORT="${MYSQL_PORT:-3306}"
MYSQL_USER="${MYSQL_USER:-root}"
DB_NAME="${DB_NAME:-xingshi}"

echo "=============================================="
echo "  Star-Learn DB Restore"
echo "=============================================="
echo "  Source: $BACKUP_FILE"
echo "  Target: ${MYSQL_USER}@${MYSQL_HOST}:${MYSQL_PORT}/${DB_NAME}"
echo "----------------------------------------------"
read -p "  This will OVERWRITE the database. Continue? [y/N] " CONFIRM

if [ "$CONFIRM" != "y" ] && [ "$CONFIRM" != "Y" ]; then
    echo "Aborted."
    exit 0
fi

echo "Restoring..."
gunzip < "$BACKUP_FILE" | mysql \
    --host="$MYSQL_HOST" \
    --port="$MYSQL_PORT" \
    --user="$MYSQL_USER" \
    --password="${MYSQL_PASSWORD:-}" \
    --default-character-set=utf8mb4 \
    "$DB_NAME"

echo "Restore complete. Verifying table count..."
mysql --host="$MYSQL_HOST" --port="$MYSQL_PORT" --user="$MYSQL_USER" --password="${MYSQL_PASSWORD:-}" \
    -e "USE ${DB_NAME}; SHOW TABLES;" 2>/dev/null | wc -l | xargs echo "Tables:"