#!/usr/bin/env bash
# scripts/health_check.sh
# 一键健康检查 (轮询 /api/health 直至 ok/degraded 或超时)
#
# 用法:
#   bash scripts/health_check.sh
#
# 退出码:
#   0  status 为 ok 或 degraded
#   1  超时 30s 仍未就绪
#   2  status 为 down 或响应格式异常

set -euo pipefail

PORT="${STARLEARN_PORT:-8000}"
URL="http://127.0.0.1:${PORT}/api/health"
DEADLINE=$((SECONDS + 30))

echo "[health_check] polling ${URL} (timeout 30s)"

while (( SECONDS < DEADLINE )); do
  if out="$(curl -fsS "${URL}" 2>/dev/null)"; then
    echo "${out}"
    status="$(echo "${out}" | python -c 'import json,sys; print(json.load(sys.stdin).get("status", "unknown"))')"
    case "${status}" in
      ok|degraded)
        echo "[health_check] service ready: ${status}"
        exit 0
        ;;
      down)
        echo "[health_check] service reports down" >&2
        exit 2
        ;;
      *)
        echo "[health_check] unknown status: ${status}" >&2
        ;;
    esac
  fi
  sleep 1
done

echo "[health_check] timeout after 30s" >&2
exit 1
