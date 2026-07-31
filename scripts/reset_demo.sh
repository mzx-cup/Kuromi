#!/usr/bin/env bash
# scripts/reset_demo.sh
# 一键重置演示数据 (调用 seed_demo --reset, 可选 --json 输出)
#
# 用法:
#   JWT_SECRET=... bash scripts/reset_demo.sh         # 人类可读输出
#   JWT_SECRET=... bash scripts/reset_demo.sh --json  # JSON 输出, 便于验收脚本

set -euo pipefail

export JWT_SECRET="${JWT_SECRET:?JWT_SECRET must be set}"
export STARLEARN_COMPETITION=1

python -m scripts.seed_demo --reset "$@"
