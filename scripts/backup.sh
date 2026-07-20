#!/bin/bash
# ============================================================================
# 星识 (Star-Learn) 数据库备份脚本
# 用途：每日全量备份 MySQL 数据库 + 应用数据目录
# 用法：
#   1. 编辑下方环境变量
#   2. chmod +x scripts/backup.sh
#   3. 加入 crontab：0 3 * * * /opt/starlearn/app/scripts/backup.sh
# ============================================================================

set -euo pipefail

# ─── 配置 ───
APP_DIR="${APP_DIR:-/opt/starlearn/app}"
BACKUP_ROOT="${BACKUP_ROOT:-/opt/starlearn/backups}"
MYSQL_HOST="${MYSQL_HOST:-127.0.0.1}"
MYSQL_PORT="${MYSQL_PORT:-3306}"
MYSQL_USER="${MYSQL_USER:-starlearn}"
MYSQL_PASSWORD="${MYSQL_PASSWORD:-}"
DB_NAME="${DB_NAME:-xingshi}"
RETENTION_DAYS="${RETENTION_DAYS:-14}"

# ─── 初始化 ───
TS=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="${BACKUP_ROOT}/db"
APP_BACKUP_DIR="${BACKUP_ROOT}/storage"
LOG_FILE="${BACKUP_ROOT}/backup.log"

mkdir -p "$BACKUP_DIR" "$APP_BACKUP_DIR"
echo "[$TS] Starting backup..." | tee -a "$LOG_FILE"

# ─── MySQL 全量备份 ───
echo "[$TS] Dumping MySQL database '$DB_NAME'..." | tee -a "$LOG_FILE"
if ! mysqldump \
    --host="$MYSQL_HOST" \
    --port="$MYSQL_PORT" \
    --user="$MYSQL_USER" \
    --password="$MYSQL_PASSWORD" \
    --single-transaction \
    --routines \
    --triggers \
    --events \
    --default-character-set=utf8mb4 \
    "$DB_NAME" 2>>"$LOG_FILE" | gzip > "$BACKUP_DIR/${DB_NAME}_${TS}.sql.gz"; then
    echo "[$TS] ERROR: mysqldump failed" | tee -a "$LOG_FILE"
    exit 1
fi
BACKUP_SIZE=$(du -h "$BACKUP_DIR/${DB_NAME}_${TS}.sql.gz" | cut -f1)
echo "[$TS] OK: db backup $BACKUP_SIZE → ${DB_NAME}_${TS}.sql.gz" | tee -a "$LOG_FILE"

# ─── 应用数据备份（storage / audio） ───
echo "[$TS] Archiving storage + audio..." | tee -a "$LOG_FILE"
if [ -d "$APP_DIR/storage" ] || [ -d "$APP_DIR/audio" ]; then
    tar -czf "$APP_BACKUP_DIR/storage_${TS}.tar.gz" \
        -C "$APP_DIR" \
        --exclude='__pycache__' \
        --exclude='*.tmp' \
        storage audio 2>>"$LOG_FILE" || true
    SIZE=$(du -h "$APP_BACKUP_DIR/storage_${TS}.tar.gz" | cut -f1)
    echo "[$TS] OK: storage backup $SIZE" | tee -a "$LOG_FILE"
fi

# ─── 清理过期备份 ───
echo "[$TS] Cleaning backups older than $RETENTION_DAYS days..." | tee -a "$LOG_FILE"
find "$BACKUP_DIR" -name "*.sql.gz" -mtime +$RETENTION_DAYS -delete 2>/dev/null || true
find "$APP_BACKUP_DIR" -name "*.tar.gz" -mtime +$RETENTION_DAYS -delete 2>/dev/null || true

# ─── 汇总 ───
DB_COUNT=$(find "$BACKUP_DIR" -name "*.sql.gz" | wc -l)
APP_COUNT=$(find "$APP_BACKUP_DIR" -name "*.tar.gz" | wc -l)
echo "[$TS] Backup done. Current retention: $DB_COUNT db / $APP_COUNT storage files." | tee -a "$LOG_FILE"
echo "---" >> "$LOG_FILE"