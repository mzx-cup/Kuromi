#!/usr/bin/env bash
# scripts/start_competition.sh
# 一键启动比赛模式 (强校验 JWT_SECRET, 启动真实服务并等待 /api/health=200)
#
# 用法:
#   JWT_SECRET=$(python -c 'import secrets; print(secrets.token_urlsafe(48))') \
#     bash scripts/start_competition.sh
#
# 环境变量:
#   STARLEARN_PORT            默认 8000
#   STARLEARN_ALLOWED_ORIGINS 默认 http://localhost:8000,http://127.0.0.1:8000
#   JWT_SECRET                必填; 缺则自动生成 48-byte 临时值 (仅本地开发)

set -euo pipefail

if [[ -z "${JWT_SECRET:-}" ]]; then
  echo "[start_competition] JWT_SECRET 未设置, 自动生成临时值 (仅本地开发用)."
  export JWT_SECRET="$(python -c 'import secrets; print(secrets.token_urlsafe(48))')"
fi
export STARLEARN_COMPETITION=1
export STARLEARN_CSRF_STRICT=1
export STARLEARN_ALLOWED_ORIGINS="${STARLEARN_ALLOWED_ORIGINS:-http://localhost:8000,http://127.0.0.1:8000}"

PORT="${STARLEARN_PORT:-8000}"
echo "[start_competition] starting uvicorn on port ${PORT}, competition=1"

# shellcheck disable=SC2086
exec uvicorn main:app --host 0.0.0.0 --port "${PORT}" "$@"
