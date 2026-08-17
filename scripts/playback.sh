#!/usr/bin/env bash
# scripts/playback.sh
# 录像回放 (从 artifacts/demo/competition-YYYYMMDD/ 拉取)
#
# 用法:
#   bash scripts/playback.sh artifacts/demo/competition-20260730
#
# 行为:
#   1. 校验 session 目录存在
#   2. 列出 trace.log / screenshots / 等附件
#   3. 打印 trace 摘要, 便于现场问答时快速回忆
#
# 注意: 本脚本**不重放浏览器**, 只展示数据. 真实重放请用录屏软件.

set -euo pipefail

SESSION="${1:?usage: playback.sh <session_dir>}"

if [[ ! -d "${SESSION}" ]]; then
  echo "[playback] session not found: ${SESSION}" >&2
  exit 1
fi

echo "[playback] playing back ${SESSION}"
ls -la "${SESSION}"

if [[ -f "${SESSION}/trace.log" ]]; then
  echo ""
  echo "[playback] trace summary (last 20 lines):"
  tail -n 20 "${SESSION}/trace.log"
else
  echo "[playback] no trace.log found in ${SESSION}" >&2
fi
