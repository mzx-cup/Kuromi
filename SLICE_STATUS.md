# 数据库合并切片状态

最后更新：2026-07-09

## 已完成切片

### M0 基础设施（已完成 2026-07-08）

- 0.1 pytest 配置 + dev 依赖（commit 05e5c82）
- 0.2 feature_flags 模块（commit ffbaac9）
- 0.3 Repository 协议 + 工厂 + DualWrite 装饰器（commit e4e7daf）
- 0.4 conftest dual-db fixtures（commit 595f6fd）
- 0.5 SLICE_STATUS.md 初始化（commit 6a400a6）

**M0 总结：**
- 17/17 单元测试通过
- 建立了契约测试、双写测试、性能测试的脚手架
- Feature flag + Repository 抽象层就绪

### 切片 #1 用户认证 — Phase 3 双写开启（2026-07-09）

**已完成：**
- M1.1 契约测试（commit e2d77ab，3/4 通过，1 个 pre-existing 失败：/api/login/guest 随机 ID）
- M1.2 User 模型 + Repositories（commit 31775ab，5/5 通过）
- M1.3 认证端点双写（commit 3e443f0，2/2 dual-write 测试通过）

**当前阶段：** Phase 3（双写开启）完成，等待 Phase 4 灰度切读

**契约端点覆盖：**
- POST /api/register — 通过
- POST /api/login — 通过
- POST /api/login-v2 — 待测试
- POST /api/login/guest — 已知问题（随机 user_id 字段导致契约失败，非迁移问题）

**已知问题：**
1. `/api/login/guest` 返回随机 user_id，无法用 normalize 消除差异。建议：M1.5 灰度时修复端点使 user_id 可预测，或在 normalize.py 中增加 `guest_user_id` 到 NOISE_FIELDS。
2. 测试隔离问题：dual-write 测试 reload 模块后影响后续 contract 测试（次要，CI 中按字母序运行会暴露）。

**负责人：** `<待填>`

## 进行中切片

（无 — 等待 #1 完成 Phase 4-5）

## 待启动切片

| # | 切片 | 工作日 | 依赖 | 状态 |
|---|------|-------|------|------|
| 2 | 用户偏好 | 2 | #1 完成 Phase 5 | 待启动 |
| 3 | 学习统计读 | 3 | #2 完成 | 待启动 |
| 4 | 学习统计写 | 3 | #3 完成 | 待启动 |
| 5 | 课程与学习路径 | 3 | #2 完成 | 待启动 |
| 6 | 知识节点 | 2 | #2 完成 | 待启动 |
| 7 | 焦点与心流 | 2 | #2 完成 | 待启动 |
| 8 | 游戏化 | 2 | #2 完成 | 待启动 |
| 9 | 聊天与消息 | 5 | #4, #5 完成 | 待启动 |
| 10 | 教室与会话 | 4 | #9 完成 | 待启动 |
| 收尾 | user 表统一 | 5 | #1-#10 完成 | 待启动 |

## 全局风险

| 风险 | 状态 | 应对 |
|------|------|------|
| 双写一致性 | #1 监控中，2/2 dual-write 测试通过 | 持续监控 |
| 性能退化 | 未测 | 切片启动前本地基准 |
| 外键完整性 | 未测 | 收尾前 FK 审计 |
| /api/login/guest 随机 ID | 影响 1/4 契约测试 | M1.5 灰度时修复 |

## Phase 4 灰度操作指南（#1）

环境变量：
```bash
# 1% 切读
READ_BACKEND_PERCENTAGE=1 DUAL_WRITE_LEGACY=true

# 10% 切读
READ_BACKEND_PERCENTAGE=10 DUAL_WRITE_LEGACY=true

# 50% 切读
READ_BACKEND_PERCENTAGE=50 DUAL_WRITE_LEGACY=true

# 100% 切读
READ_BACKEND_PERCENTAGE=100 DUAL_WRITE_LEGACY=true
```

每档比例需运行 ≥24 小时无故障才能进下一档。错误率阈值 <0.1%，双写一致性差异数 = 0。
