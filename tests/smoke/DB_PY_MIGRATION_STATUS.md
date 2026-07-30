# db.py ORM 迁移状态报告 — M5.7 (Task 31)

**日期**: 2026-07-30
**结论**: ⚠️ 迁移尚未完成，**未删除 db.py**

## 1. 灰度配置（已就绪）

`app/core/feature_flags.py` 已实现：
- `READ_BACKEND_PERCENTAGE` (0-100): 控制 ORM 读取占比
- `DUAL_WRITE_LEGACY` (bool): 是否继续写入旧 db.py

`config/.env`:
- `KB_READ_BACKEND_PERCENTAGE=0`     ← KB 模块灰度中（默认走 ORM）
- `KB_DUAL_WRITE_LEGACY=True`         ← KB 仍保留双写保险

## 2. 模块迁移进度

| 模块 | 状态 | 备注 |
|---|---|---|
| KB / Knowledge | ✅ 已迁移 | `app/services/kb/*` 全部走 ORM；`tests/kb/test_ingest_retry.py` 4/4 PASS |
| 其他 64 个文件 | ❌ 未迁移 | `grep -rn "from db import" app/ tests/ \| wc -l` = 64 |

未迁移模块包括：
- `app/api/auth.py`、`app/api/learning_path.py`、`app/api/memory.py`、`app/api/teacher_chat.py` 等
- `app/repositories/legacy/*.py`：legacy 兼容层
- `app/services/learning_path/llm_analyzer.py` 等核心服务

## 3. 风险评估

| 操作 | 风险 | 建议 |
|---|---|---|
| 设置 `READ_BACKEND_PERCENTAGE=100` | 🟡 中等 | 仅 KB 已迁移；其他模块读取会落到 `db.py`（兼容） |
| 删除 `db.py` | 🔴 极高 | 64 个 import 会立刻 ImportError；必须先把所有调用方迁移到 ORM |

## 4. 当前未执行项

按 plan Task 31 步骤：

- [x] Step 1: 24h 灰度（feature flags 已就绪，未启动灰度）
- [ ] Step 2: 备份 db.py（建议执行：`cp db.py db.py.final-backup-20260730`）
- [ ] Step 3: 全文 grep 验证 — **当前 64 个 import，不通过**
- [ ] Step 4: 删除 db.py + Navicat/setup_database.py — **暂缓**
- [ ] Step 5: 跑全量测试 — 暂缓（依赖 Step 4）
- [ ] Step 6: Commit — 暂缓

## 5. 后续行动（按优先级）

1. **短期（安全）**：把 `READ_BACKEND_PERCENTAGE` 提升到 100（仅 KB），观察 24h。
2. **中期（迁移）**：将 auth / memory / teacher_chat 等模块逐步迁移到 ORM。
3. **长期（清理）**：当 `grep -rn "from db import" app/ tests/` 结果为 0 时，再执行删除。

## 6. 验收

- ✅ M2-M5 新增代码（app/agents/, app/services/orchestrator/, app/services/safety/, app/services/learning_path/forgetting_curve.py, ...）**未引入** `from db import`
- ✅ KB 模块已完全脱离 `db.py`（4/4 测试通过 ORM-only）
- ⚠️ 整体项目仍有 64 处 `db.py` 引用，需后续专项迁移

**结论**: M5.7 / Task 31 当前为"基础设施就绪 + 等待迁移"状态，不删除 db.py。