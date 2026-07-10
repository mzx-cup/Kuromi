# 数据库渐进合并设计

**日期：** 2026-07-08
**状态：** 设计待 review
**作者：** Brainstorming 会话

---

## 1. 背景与目标

### 1.1 当前状态

项目存在两套独立的数据库系统：

| 系统 | 引擎 | 文件 | 规模 |
|------|------|------|------|
| **SQLAlchemy ORM** | async SQLAlchemy 2.0 + aiosqlite | `xingshi_v2.db` | 13 张表，约 20 个端点 |
| **db.py** | 同步 SQLite/pymysql/JSON 三级回退 | `xingshi.db`（或 MySQL `xingshi`） | 35+ 张表，~90 个端点 |

两套系统在同一进程中运行，共享部分表名（`messages`、`quiz_records`、`classroom_sessions` 等），但 schema 不兼容：
- 列名差异：`metadata` vs `msg_metadata`
- 时区差异：naive vs aware datetime
- 主键类型差异：INT AUTO_INCREMENT vs VARCHAR UUID
- 缺失字段差异：db.py 多出 `teacher_mode` 等字段

### 1.2 目标

将所有数据访问统一到 SQLAlchemy ORM，**废弃 db.py**，满足以下约束：

1. **测试优先**：先建立完整测试覆盖（契约 + 快照 + 性能），用测试作为迁移的安全网
2. **零用户退化**：迁移期间用户视角的功能与性能不退化
3. **可回滚**：任意切片可独立回滚到 db.py 路径
4. **风险渐进**：低风险切片先做，高风险切片（聊天、教室、user 表统一）最后做

### 1.3 非目标

- 不改变业务逻辑（仅替换数据访问层）
- 不重构前端 hub 页面（保持 hub.html / hub.js 不变）
- 不引入新的 ORM 框架（保持 SQLAlchemy 2.0）
- 不做实时性能优化（延迟到收尾后单独规划）

---

## 2. 整体架构

### 2.1 目录结构

新增/修改的关键路径：

```
Kuromi-main/
├── app/
│   ├── core/
│   │   ├── database.py          # 已有，不变
│   │   ├── feature_flags.py     # 🆕 用户哈希分流 + 读路径选择
│   │   └── config.py            # 修改：增加 READ_BACKEND_PERCENTAGE
│   ├── models/
│   │   ├── user.py              # 已有（User/StudentProfile）
│   │   ├── preferences.py       # 🆕
│   │   ├── learning.py          # 🆕
│   │   ├── knowledge.py         # 🆕
│   │   ├── focus.py             # 🆕
│   │   ├── gamification.py      # 🆕
│   │   ├── chat.py              # 🆕（修正 metadata 列名）
│   │   └── classroom.py         # 已有（扩展字段）
│   ├── repositories/            # 🆕 数据访问层抽象
│   │   ├── base.py              # 接口定义
│   │   ├── dual_write.py        # 双写装饰器
│   │   ├── legacy/              # db.py 封装
│   │   │   ├── preferences.py
│   │   │   ├── learning.py
│   │   │   └── ...
│   │   └── orm/                 # SQLAlchemy 实现
│   │       ├── preferences.py
│   │       ├── learning.py
│   │       └── ...
├── tests/
│   ├── conftest.py              # 修改：DB fixtures, dual_backend
│   ├── contracts/               # 🆕 契约测试（关键端点）
│   ├── snapshots/               # 🆕 快照测试（次要端点）
│   ├── perf/                    # 🆕 性能测试
│   │   ├── test_relative_regression.py
│   │   └── benchmark_local.py
│   ├── repositories/            # 🆕 repository 单元测试
│   └── fixtures/                # 🆕 种子数据
├── scripts/
│   ├── reconcile_databases.py   # 🆕 双套数据库对账
│   └── migrate_user_table.py    # 🆕 收尾阶段 user 表迁移
├── perf-results/                # 🆕 本地基准结果（gitignored）
└── SLICE_STATUS.md              # 🆕 切片进度追踪
```

### 2.2 关键模块

#### 2.2.1 Repository 抽象（`app/repositories/base.py`）

每个领域有独立接口，ORM/Legacy/DualWrite 三种实现并存于迁移期间。

```python
class LearningRepository(Protocol):
    async def get_overview(self, user_id: str) -> dict: ...
    async def get_trend(self, user_id: str, days: int) -> list[dict]: ...
    async def get_heatmap(self, user_id: str) -> dict: ...
    async def record_session(self, user_id: str, session_data: dict) -> None: ...
```

#### 2.2.2 双写装饰器（`app/repositories/dual_write.py`）

```python
class DualWriteRepository:
    def __init__(self, primary: Repository, shadow: Repository): ...

    async def record_session(self, user_id: str, data: dict) -> None:
        try:
            await self.primary.record_session(user_id, data)
        except Exception as e:
            # 主写失败必须抛错
            metrics.counter("dual_write.primary_failure").inc()
            raise
        try:
            await self.shadow.record_session(user_id, data)
        except Exception as e:
            # 影子写失败记录但不抛错
            metrics.counter("dual_write.shadow_failure").inc()
            enqueue_shadow_retry(user_id=user_id, data=data, error=str(e))
```

**关键原则：** 主写永远抛错；影子写失败记录后异步重试。

#### 2.2.3 Feature Flag（`app/core/feature_flags.py`）

```python
def user_in_orm_read_path(user_id: str, percentage: int) -> bool:
    """基于 user_id 稳定哈希，决定是否走 SQLAlchemy 读路径"""
    if percentage <= 0:
        return False
    if percentage >= 100:
        return True
    h = hashlib.md5(f"orm-read:{user_id}".encode()).hexdigest()
    bucket = int(h[:8], 16) % 100
    return bucket < percentage

def get_read_percentage() -> int:
    return int(os.getenv("READ_BACKEND_PERCENTAGE", "0"))

def is_dual_write_enabled() -> bool:
    return os.getenv("DUAL_WRITE_LEGACY", "false").lower() == "true"
```

用户哈希保证同一用户在同一百分比下路径稳定，避免单次请求内路径切换。

#### 2.2.4 端点改造模板

```python
@app.get("/api/stats/overview/{user_id}")
async def get_overview(user_id: str, db: AsyncSession = Depends(get_db)):
    if user_in_orm_read_path(user_id, get_read_percentage()):
        repo = SqlAlchemyLearningRepository(db)
        return await repo.get_overview(user_id)
    legacy_repo = DbPyLearningRepository()
    return await run_in_threadpool(legacy_repo.get_overview, user_id)

@app.post("/api/cockpit/learning-time")
async def record_learning_time(user_id: str, data: LearningTimeUpdate,
                                db: AsyncSession = Depends(get_db)):
    if is_dual_write_enabled():
        primary = SqlAlchemyLearningRepository(db)
        shadow = DbPyLearningRepository()
        repo = DualWriteRepository(primary=primary, shadow=shadow)
        return await repo.record_session(user_id, data.dict())
    primary = SqlAlchemyLearningRepository(db)
    return await primary.record_session(user_id, data.dict())
```

---

## 3. 测试分层

### 3.1 分层结构

| 层级 | 用途 | 位置 | 运行时 | 阻塞合并 |
|------|------|------|--------|---------|
| **契约层** | 关键端点双套后端产出字段级一致 | `tests/contracts/` | CI + 本地 | 🔴 是 |
| **快照层** | 次要端点响应稳定 | `tests/snapshots/` | CI | 🟡 否（仅警告） |
| **性能层（CI）** | 切换前后相对延迟比值 | `tests/perf/test_relative_regression.py` | CI | 🟡 否 |
| **性能层（本地）** | 完整基准测试 | `tests/perf/benchmark_local.py` | 手动 | ❌ 否 |
| **双写一致性** | 验证两套数据库最终一致 | `tests/contracts/test_dual_write_consistency.py` | CI | 🔴 是 |

### 3.2 契约测试

**关键端点清单（共 25 个契约测试）：**

| 切片 | 契约端点 |
|------|---------|
| #1 认证 | `/api/login`, `/api/register`, `/api/login-v2`, `/api/login/guest` |
| #2 偏好 | `/api/user/preferences/{user_id}`, `/api/settings/load/{user_id}` |
| #3 统计读 | `/api/stats/overview`, `/api/stats/trend`, `/api/stats/heatmap`, `/api/stats/mastery`, `/api/daily-route/status` |
| #4 统计写 | `/api/cockpit/learning-time`, `/api/cockpit/stats/sync` |
| #5 进度 | `/api/progress/save`, `/api/progress/load`, `/api/progress/summary` |
| #6 知识 | `/api/knowledge/nodes`, `/api/knowledge/pending`, `/api/knowledge/records` |
| #7 焦点 | `/api/cockpit/analysis/{user_id}`, `/api/focus/load/{user_id}` |
| #8 游戏化 | `/api/garden/load/{user_id}`, `/api/pet/load/{user_id}` |
| #9 聊天 | `/api/chat/history`, `/api/v2/chat/stream` |
| #10 教室 | `/api/v2/classroom/{course_id}` |

**Fixture 设计：**

```python
@pytest.fixture
def dual_db_environment(tmp_path):
    legacy_db = tmp_path / "legacy.db"
    orm_db = tmp_path / "orm.db"

    setup_legacy_schema(legacy_db)
    init_orm_schema_sync(orm_db)

    seed_data = generate_seed_dataset()
    populate_legacy(legacy_db, seed_data)
    populate_orm(orm_db, seed_data)

    return DualDbEnv(legacy_path=legacy_db, orm_path=orm_db)

@pytest.fixture
def contract_runner(dual_db_environment):
    legacy_client = build_test_client(backend="legacy", db=dual_db_environment.legacy_path)
    orm_client = build_test_client(backend="orm", db=dual_db_environment.orm_path)

    class Runner:
        def assert_contract(self, method, path, **kwargs):
            legacy_resp = legacy_client.request(method, path, **kwargs)
            orm_resp = orm_client.request(method, path, **kwargs)
            assert legacy_resp.status_code == orm_resp.status_code
            assert normalize(legacy_resp.json()) == normalize(orm_resp.json())
    return Runner()
```

`normalize()` 剥除噪声字段：`updated_at`、`last_synced_at`、`created_at`（精确到秒的字段）。

### 3.3 快照测试

覆盖剩余 ~65 个次要端点。首次运行记录基线，迁移过程中**绝不更新快照**，除非明确接受该变更。

工具自实现（不引入 pytest-snapshot），避免新依赖。

### 3.4 性能测试（CI）

```python
def test_overview_latency_stable(client):
    legacy_p50 = measure_p50(client, "/api/stats/overview/perf_user",
                              backend="legacy", iterations=10)
    orm_p50 = measure_p50(client, "/api/stats/overview/perf_user",
                          backend="orm", iterations=10)

    # 容差：ORM 不能比 legacy 慢 2 倍以上
    assert orm_p50 <= legacy_p50 * 2.0

    # 记录数据到 perf-results/ 用于追踪趋势
    record_metric("overview_p50_legacy", legacy_p50)
    record_metric("overview_p50_orm", orm_p50)
```

每次 warm-up 3 次，取 10 次中位数。同一 commit 跑 3 次取中位数降低误报。

### 3.5 性能测试（本地）

```bash
python tests/perf/benchmark_local.py \
    --user perf_user \
    --iterations 1000 \
    --warmup 50 \
    --output perf-results/$(date +%Y-%m-%d)-$(git branch --show-current).json
```

**切读决策门槛：**

- p95 ≤ 50ms
- memory ≤ 60MB
- 否则不切读比例

### 3.6 双写一致性测试

```python
def test_learning_time_write_lands_in_both(dual_db_environment):
    write_via_orm("/api/cockpit/learning-time", {...})

    legacy_count = count_legacy_records("learning_records", user_id)
    orm_count = count_orm_records("LearningRecord", user_id=user_id)

    assert legacy_count == orm_count == 1
```

---

## 4. 切片划分

### 4.1 依赖图

- 认证必须先做（所有 API 都需要 user_id 解析）
- 只读优先于写入（建立信心）
- 聊天/教室放到最后（高风险，依赖最多）
- user 表统一作为收尾（影响所有外键）

### 4.2 10 个垂直切片

| # | 切片 | 路由数 | 涉及 db.py 表 | 风险 | 工作日 |
|---|------|-------|--------------|------|--------|
| 1 | 用户认证 | 6 | `user`, `user_login_records`, `user_profile` | 🔴 高 | 4 |
| 2 | 用户偏好与设置 | 8 | `user_preferences`, `user_settings` | 🟢 低 | 2 |
| 3 | 学习统计只读 | 12 | `learning_records`, `study_sessions`, `user_stats`, `weekly_summary` | 🟡 中 | 3 |
| 4 | 学习统计写入 | 10 | `learning_records`, `study_sessions`, `learning_goals` | 🟡 中 | 3 |
| 5 | 课程与学习路径 | 14 | `learning_path`, `learning_path_nodes`, `user_evaluations`, `course_generation_status` | 🟡 中 | 3 |
| 6 | 知识节点 | 8 | `knowledge_*`（5 张表） | 🟢 低 | 2 |
| 7 | 焦点与心流 | 8 | `user_focus_history`, `focus_*`（3 张表） | 🟢 低 | 2 |
| 8 | 游戏化（花园/宠物/成就） | 12 | `user_garden`, `user_pet`, `user_achievements`, `user_eco_data` | 🟢 低 | 2 |
| 9 | 聊天与消息 | 14 | `messages`, `conversation_summaries`, `user_memories`, `agent_turn_records` | 🔴 高 | 5 |
| 10 | 教室与会话 | 16 | `classroom_sessions`, `classroom_records`, `quiz_records` | 🔴 高 | 4 |
| **收尾** | user 表统一 + 清理 db.py | — | 全部 | 🔴 极高 | 5 |

**总计：** 约 35 开发工作日；考虑每切片灰度期（7 天）和串行约束后，总日历时间约 10 周（详见 §10）。

### 4.3 切片 #1 用户认证（4 天）

**路由：** `/api/register`, `/api/login`, `/api/login-v2`, `/api/login/guest`, `/api/user/delete`, `/api/user/update`

**db.py 表：** `user` (PK INT), `user_login_records` (PK INT), `user_profile` (PK VARCHAR)

**冲突解决：** `user` 表保持 INT PK 但**新建 `users` 表**作为 SQLAlchemy 入口。两个表**共存**，通过 `user_id_mapping` 表做 ID 转换。

### 4.4 切片 #2 用户偏好与设置（2 天）

**路由：** `/api/user/preferences/*`, `/api/settings/*`, `/api/user/theme/*`, `/api/user/meta`, `/api/user/state/*`

**db.py 表：** `user_preferences` (JSON value), `user_settings` (key-value)

**模型设计：**

```python
class UserPreference(Base):
    __tablename__ = "user_preferences"
    user_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    key: Mapped[str] = mapped_column(String(128), primary_key=True)
    value: Mapped[dict] = mapped_column(JSON)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
```

### 4.5 切片 #3 学习统计只读（3 天）

**路由：** `/api/stats/overview/{user_id}`, `/api/stats/trend/*`, `/api/stats/heatmap/*`, `/api/stats/mastery/*`, `/api/daily-route/status`, `/api/stats/load/*`, `/api/user/stats/*`

**db.py 表：** `learning_records`, `study_sessions`, `user_stats`, `weekly_summary`

### 4.6 切片 #4 学习统计写入（3 天）

**路由：** `/api/cockpit/learning-time`, `/api/cockpit/stats/sync`, `/api/cockpit/analysis/*`, `/api/study/sessions/*`, `/api/goals/*`, `/api/stats/save`

**db.py 表：** `learning_records`, `study_sessions`, `learning_goals`

### 4.7 切片 #5 课程与学习路径（3 天）

**路由：** `/api/progress/save`, `/api/progress/load`, `/api/progress/summary/*`, `/api/v2/course/*` (除 brainstorm/chat), `/api/user/evaluations/*`

**db.py 表：** `learning_path`, `learning_path_nodes`, `user_evaluations`, `course_generation_status`

### 4.8 切片 #6 知识节点（2 天）

**路由：** `/api/knowledge/nodes/*`, `/api/knowledge/pending/*`, `/api/knowledge/records/*`, `/api/knowledge/review`, `/api/knowledge/analyze-relations`

**db.py 表：** `knowledge_nodes`, `knowledge_relations`, `knowledge_reviews`, `knowledge_records`, `knowledge_pending`

### 4.9 切片 #7 焦点与心流（2 天）

**路由：** `/api/cockpit/analysis/*`, `/api/focus/*`, `/api/user/focus/*`

**db.py 表：** `user_focus_history`, `focus_sessions`, `focus_events`

### 4.10 切片 #8 游戏化（2 天）

**路由：** `/api/garden/*`, `/api/pet/*`, `/api/achievements/*`, `/api/eco/*`, `/api/user/eco/*`

**db.py 表：** `user_garden`, `user_pet`, `user_achievements`, `user_eco_data`

### 4.11 切片 #9 聊天与消息（5 天）⚠️ 高风险

**路由：** `/api/chat`, `/api/chat/history`, `/api/v2/chat`, `/api/v2/chat/stream`, `/api/v2/chat/onboard*`, `/api/v2/agents/*`, `/api/v2/state/*`, `/api/v2/proactive/*`, `/api/v2/flashcard/*`, `/api/v2/telemetry/*`

**db.py 表：** `messages`, `conversation_summaries`, `user_memories`, `agent_turn_records`

**冲突点：**

| 问题 | db.py | SQLAlchemy | 解决方案 |
|------|-------|-----------|---------|
| 列名 | `metadata TEXT` | `msg_metadata JSON` | 选 `msg_metadata`，db.py 端做列重命名迁移 |
| 时区 | naive DATETIME | `DateTime(timezone=True)` | SQLAlchemy 端用 aware，统一 UTC |
| 删除策略 | 硬删除 | 软删除（`deleted_at`） | 短期保留硬删除 |

**特殊步骤：** `app/services/memory_extractor.py:247` 中 `from db import save_user_memory, update_user_memory` 需要同步迁移。

### 4.12 切片 #10 教室与会话（4 天）⚠️ 高风险

**路由：** `/api/v2/classroom/*`, `/api/classroom.html`, `/api/v2/course/quiz/grade`, `/api/v2/grade/batch`, `/api/quiz/grade`

**db.py 表：** `classroom_sessions`, `classroom_records`, `quiz_records`

**特殊处理：** 反向切片——SQLAlchemy 模型已有但 db.py 字段更多，需要**扩字段**兼容 db.py 功能。

### 4.13 收尾阶段：user 表统一（5 天）⚠️ 极高风险

**触发条件：** 切片 1-10 全部完成。

**步骤：**
1. 把所有 `user.id` (INT) 引用替换为 `users.id` (VARCHAR)
2. 创建新 `users` 表，包含原 db.py `user` 表的所有字段
3. 数据迁移脚本：逐行把 `user` 表数据导入 `users`，生成 UUID 映射
4. 所有外键列改为 FK to users.id，迁移数据
5. 删除 `user` 表
6. 删除 `db.py`、`Navicat/setup_database.py`

**安全门：** 迁移脚本 dry-run + rollback + 外键完整性测试 + staging 24h 验证。

---

## 5. 切片生命周期

### 5.1 5 阶段流程

```
Phase 1: 测试搭建      → 契约 + 快照 + 双写一致性测试
Phase 2: 模型与 Repo   → ORM/Legacy/DualWrite 三实现
Phase 3: 路由切换      → 双写开启，PR 合并
Phase 4: 灰度切读      → 1% → 10% → 50% → 100%（每档 ≥24h）
Phase 5: 关闭双写      → 删除 Legacy Repo 与 if/else 分支
```

### 5.2 低风险切片时间线（以切片 #2 为例，2 天）

| 时段 | 活动 | 产出 |
|------|------|------|
| Day 1 上午 | Phase 1：8 个契约 + 4 个快照 | `tests/contracts/test_preferences_contract.py` |
| Day 1 下午 | Phase 2：模型 + ORM/Legacy Repo + DualWrite | `app/models/preferences.py` |
| Day 1 晚上 | repository 单元测试 | `tests/repositories/test_preferences_repo.py` |
| Day 2 上午 | Phase 3：改 8 个 endpoint | 修改 main.py 中 8 处 |
| Day 2 下午 | PR + CI | 合并 |
| Day 3-9 | Phase 4：1% → 10% → 50% → 100% | 监控 7 天 |
| Day 10 | Phase 5：关闭双写 | 代码清理 |

### 5.3 高风险切片时间线（以切片 #9 为例，5 天 + 7 天灰度）

| 时段 | 活动 | 产出 |
|------|------|------|
| Day 1-2 | Phase 1：14 个契约 + 5 个双写一致性 | metadata 列名、时区、UUID 严格覆盖 |
| Day 2-3 | Phase 2：4 张表模型 + 4 个 Repository | `app/models/chat.py` + 4 个 repository |
| Day 3-4 | Phase 3：14 个 endpoint + memory_extractor.py | main.py + memory_extractor.py 改写 |
| Day 4-5 | 端到端测试 + PR + CI | 合并 |
| Day 6-12 | Phase 4：7 天灰度（聊天节奏放慢） | 监控 7 天 |
| Day 13 | Phase 5：关闭双写 | 收尾 |

### 5.4 Phase 4 灰度切换检查清单

每次切比例前必须满足：

- 当前比例运行 ≥24 小时
- 双写一致性测试 0 失败
- 错误率 <0.1%（基于 feature flag 错误日志）
- 性能基准（p95）< 切换前 2 倍
- 没有新增 P0/P1 用户报告

### 5.5 Phase 5 关闭双写操作

```bash
DUAL_WRITE_LEGACY=false
pytest tests/                            # 完整测试套件
pytest tests/contracts/ --backend=legacy # 确认 legacy 仍能读

# 代码删除
# - DualWriteRepository 类
# - Legacy Repository 实现
# - feature_flags.is_dual_write_enabled() 调用
# - endpoint 中 if/else 分支（如果 100% 已切读）
```

---

## 6. 错误处理与回滚

### 6.1 错误分级

| 级别 | 描述 | 检测方式 | 自动响应 | 手动响应 |
|------|------|---------|---------|---------|
| **L1** | Schema 不匹配 | 双启动时表结构差异 | CI 阻断 | 修改 schema 重新迁移 |
| **L2** | 双写单边失败 | DualWriteRepository 异常捕获 | 写入 metric + 异步重试 | 定时对账补数据 |
| **L3** | 读路径崩溃 | p99 错误率 > 5% | 自动回退到 legacy | 诊断后修复 |
| **L4** | 数据不一致 | 对账脚本差异 > 0 | 暂停切读 + 告警 | 选数据库为真值，修复另一侧 |
| **L5** | 性能严重退化 | p95 > legacy × 3 | 灰度比例自动回退一档 | 优化 SQL/连接池 |
| **L6** | 用户报告故障 | 工单/客服 | 立即回退该 user 到 legacy | 修复后逐步恢复 |

### 6.2 对账脚本（`scripts/reconcile_databases.py`）

```python
async def reconcile_table(table_name: str, primary: Database, shadow: Database):
    primary_rows = await primary.fetch_all(f"SELECT * FROM {table_name}")
    shadow_rows = await shadow.fetch_all(f"SELECT * FROM {table_name}")

    primary_index = {row["id"]: row for row in primary_rows}
    shadow_index = {row["id"]: row for row in shadow_rows}

    missing_in_shadow = set(primary_index) - set(shadow_index)
    extra_in_shadow = set(shadow_index) - set(primary_index)

    divergent = []
    for id_ in set(primary_index) & set(shadow_index):
        if not rows_equal(primary_index[id_], shadow_index[id_], noise_fields=NOISE_FIELDS):
            divergent.append(id_)

    return ReconciliationResult(
        table=table_name,
        missing_in_shadow=missing_in_shadow,
        extra_in_shadow=extra_in_shadow,
        divergent=divergent,
    )
```

**运行模式：**

```bash
# 每小时定时任务
python scripts/reconcile_databases.py \
    --primary sqlite:///xingshi.db \
    --shadow sqlite:///xingshi_v2.db \
    --tables user_preferences,user_settings \
    --output logs/reconcile-$(date +%Y%m%d-%H).json

# 紧急全面对账
python scripts/reconcile_databases.py --full --notify
```

**关键：** 对账只告警，不自动修复。修复脚本单独维护。

### 6.3 回滚机制

**单切片回滚（最常见）：**

```bash
READ_BACKEND_PERCENTAGE=0   # 灰度归零
DUAL_WRITE_LEGACY=true      # 保持双写
pytest tests/contracts/ --backend=legacy  # 验证回滚成功
```

**整切片回滚：**

```bash
git log --oneline | grep "slice-9-chat"
git revert <slice-9-commit>
pytest tests/
```

**紧急全量回滚（最坏）：**

```bash
READ_BACKEND_PERCENTAGE=0
ORM_ENABLED=false            # 完全禁用 ORM 路由
```

**触发条件：** 大于 5% 用户受影响 + 影响时长超过 1 小时 + 多个切片同时异常。

---

## 7. 风险预案

### 7.1 风险清单

| 风险 | 等级 | 预案 |
|------|------|------|
| 双写一致性问题 | 🔴 高 | 切片启动前**只迁移 schema 不动数据**，幂等迁移脚本，自动备份 |
| 性能严重退化 | 🔴 高 | 1% 切读时立即跑性能基准；连接池调优；关键查询加索引；必要时 `asyncio.to_thread` |
| 外键完整性破坏 | 🟡 中 | 迁移前 FK 审计脚本；迁移后 `PRAGMA foreign_key_check`；修复脚本可重入 |
| 测试覆盖不全 | 🟡 中 | 收尾前 7 天"零 P0 报告"窗口；模糊测试；dogfooding |
| CI 基础设施不稳定 | 🟢 低 | 相对值（比值）+ 同 commit 跑 3 次取中位数 |
| 项目无人维护 | 🔴 高 | 每切片必须**完整收尾**（含 Phase 5）；`SLICE_STATUS.md` 强制每周更新 |

### 7.2 切片 #9 metadata 列名冲突详细预案

1. 启动前**只迁移 schema**：SQLAlchemy 创建新表，db.py 表保持原样
2. 数据迁移脚本：`scripts/migrate_messages_metadata.py`
   - 必须幂等（多次跑结果一致）
   - 运行前自动备份 `cp xingshi.db xingshi.db.backup-$(date +%Y%m%d)`
   - 复制 `metadata` 列内容到 `msg_metadata` JSON 格式
3. 迁移后跑双写一致性测试验证
4. 7 天灰度期间持续监控 `messages` 表差异

### 7.3 收尾阶段特殊预案

**user 表迁移脚本大纲（`scripts/migrate_user_table.py`）：**

```python
async def migrate_user_table():
    backup_databases()
    create_orm_users_table()                # 含原 user 表所有字段

    user_id_map = {}                         # old_id (int) → new_id (UUID str)
    for old_user in fetch_all_legacy_users():
        new_id = generate_uuid()
        user_id_map[old_user.id] = new_id
        insert_orm_user(new_id, old_user)

    migrate_foreign_keys(user_id_map)        # 所有 FK 列迁移
    verify_foreign_keys()                    # PRAGMA foreign_key_check
    # drop_legacy_user_table()               # 默认不执行，需手动确认
    return MigrationReport(...)
```

**安全门：** dry-run 模式 + rollback 脚本 + FK 完整性测试 + staging 24h 验证。

---

## 8. 监控与状态追踪

### 8.1 监控指标

每个切片在 Phase 4 期间必须有：

| 指标 | 阈值 | 测量方式 |
|------|------|---------|
| 双写失败率 | < 0.1% | DualWriteRepository metric |
| 双写一致性 | 差异数 = 0 | 对账脚本 |
| ORM 错误率 | < 0.5% | endpoint 错误日志 |
| Legacy 错误率 | < 0.1% | endpoint 错误日志 |
| p95 延迟 | < legacy × 2 | 性能测试 |
| 数据库连接数 | < 25 | pool 监控 |

### 8.2 `SLICE_STATUS.md` 模板

```markdown
# 数据库合并切片状态

最后更新：2026-07-08

## 已完成切片

### 切片 #1 用户认证
- 完成日期：2026-XX-XX
- 灰度天数：7 天
- 关闭双写：是
- 已知问题：无

## 进行中切片

### 切片 #3 学习统计只读
- 启动日期：`<待填>`
- 当前阶段：Phase 4 灰度 50%
- 负责人：`<待填>`
- 已知问题：1 个对账不一致已修复

## 待启动切片

### 切片 #4 学习统计写入
- 计划启动：2026-XX-XX
- 前置依赖：切片 #3 完成
- 预估工作日：3 天

## 全局风险

| 风险 | 当前状态 | 应对 |
|------|---------|------|
| 双写一致性 | 监控中，无告警 | 持续监控 |
| 性能退化 | ORM p95 < 2x legacy | 持续监控 |
```

---

## 9. 验收标准

### 9.1 单切片完成标准

- [ ] Phase 1-5 全部走完
- [ ] 契约测试在该切片所有端点通过
- [ ] 性能基准满足切读门槛（p95 ≤ 50ms，memory ≤ 60MB）
- [ ] 双写一致性测试 0 失败
- [ ] 100% 切读运行 ≥7 天无 P0 故障
- [ ] 代码清理完成（DualWrite 装饰器、Legacy Repo、if/else 分支删除）
- [ ] `SLICE_STATUS.md` 更新

### 9.2 整体完成标准

- [ ] 所有 10 个切片 + 收尾阶段完成
- [ ] `db.py` 已删除
- [ ] `Navicat/setup_database.py` 已删除
- [ ] 所有路由使用 SQLAlchemy ORM
- [ ] `READ_BACKEND_PERCENTAGE=100` 永久生效
- [ ] 性能基准全量通过
- [ ] 用户报告 7 天内无 P0/P1
- [ ] 文档与代码同步更新

---

## 10. 时间线总览

| 周 | 切片 | 阶段 |
|----|------|------|
| W1 | #1 用户认证 | Phase 1-5 |
| W2 | #2 用户偏好 + #3 统计读 | Phase 1-3 |
| W3 | #3 统计读 | Phase 4-5 + #4 统计写 Phase 1-3 |
| W4 | #4 统计写 + #5 课程 | Phase 4-5 + Phase 1-3 |
| W5 | #6 知识 + #7 焦点 + #8 游戏化 | Phase 1-5 |
| W6 | #9 聊天 | Phase 1-3 |
| W7 | #9 聊天 | Phase 4-5 + #10 教室 Phase 1-3 |
| W8 | #10 教室 | Phase 4-5 |
| W9 | 收尾：user 表统一 | - |
| W10 | 收尾收尾 + 缓冲 | - |

**总计：** 10 周（含 1 周缓冲）。

---

## 11. 待决问题

> 这些问题在实施前必须解决或明确接受风险。

1. **SQLAlchemy 异步迁移到同步 db.py 的性能影响**——实测 legacy vs ORM 性能差异
2. **MySQL 兼容性测试**——目前测试主要用 SQLite，生产用 MySQL 是否一致
3. **JSON 回退机制保留**——db.py 在 SQLite 不可用时降级到 local_storage.json，SQLAlchemy 不支持此降级，是否保留
4. **Alembic 迁移基线**——重新生成 migrations 目录的基线是否影响 CI
5. **前端 localStorage 同步逻辑**——hub 页面在迁移期间是否需要双写 localStorage（与双写数据库一致）

---

**文档版本：** 1.0
**下一步：** 用户 review → writing-plans skill