# 技术问答准备

> 答辩时评委可能追问的问题与建议答案. 团队成员各自熟悉一段, 现场不会卡壳.

## 1. 智能体与普通 Prompt 链有何区别?

答: 智能体用结构化 Envelope (trace_id / role / payload / fallback) 通信, 每步可独立
重试和降级; Prompt 链是一次性拼接, 难以定位失败. 我们的 Socratic / Planner /
Recommend 是 6 个独立 AgentRole, 通过 `app.agents.io_schema.AgentEnvelope` 串联,
每步都有 `latency_ms` 和 `fallback` 标记, 现场任何断点都能秒级回放.

## 2. 哪些事件会更新学习画像? 如何控制错误级联?

答: 通过 `DemoRepository.save_mastery` (P1 阶段) 统一入口; 任一上游失败都打 fallback
标记, 不污染画像. 画像读也走 `DemoRepository.load_profile`, 出错返回 `fallback=True`
的种子数据, 前端永远拿到结构正确的 JSON.

## 3. 学习路径为什么改? 决策依据能否复现?

答: 见 `docs/data-flow.md` 中 Planner + Recommend 节点; 每条建议都带
`goal_evidence` (用户目标) 和 `capability_rationale` (能力评估). 路径调整的
每一步都有 `trace_id`, 现场能调出"为什么改了这条"的完整决策链.

## 4. 长期记忆 / 关系数据库 / 向量库分别保存什么?

- 关系库 (`xingshi.db` / MySQL): 用户 / 课程 / 班级结构化数据
- 向量库 (Qdrant): 知识点语料, 用于 RAG 检索
- 长期记忆 (`agents.py` 中的长记忆模块): 用户事件流 (时序), 用于画像和个性化

## 5. 如何处理模型幻觉 / 提示词注入 / 恶意输入?

- `AuditAgent` + `HallucinationGuard` (L0-L4 四层校验, 见
  `app/services/tutor_engine/hallucination_guard.py`)
- `jailbreak_detector` (L0 输入层)
- 全部走结构化校验, 不允许裸字符串透传到下一层

## 6. 外部模型失败时, 教学循环能否完成?

答: 可以. `app/services/llm/retry_strategy.py` 实现 1 次重试 + fallback 种子响应,
主链不断. Qdrant 不可用时回退到结构化 SQL 检索 (见
`app/services/kb/citation_retriever.py`).

## 7. 教师和学生之间如何隔离学生数据?

答: Repository 强制带 `user_id`; 教师视图通过 `teacher_suggestions` 接口聚合,
不会直接读取其他用户画像. 具体隔离测试见 `tests/security/test_teacher_user_isolation.py`
(P0 阶段 Task 21).

## 8. 代码执行如何隔离? 为什么比赛版关闭当前实现?

答: 当前实现是黑名单 + subprocess, 不能防御多租户不可信代码; 比赛版默认关闭
(`STARLEARN_COMPETITION=1` 时 `run_python` 直接返回
`{"blocked": True, "reason": "competition_mode_disabled"}`), 真实展示用预生成
结果 + 独立容器隔离 (P2 阶段做).

## 9. 系统能支持多少并发? 瓶颈在哪?

答: 当前 FastAPI 单实例约 ~50 RPS, 瓶颈在 LLM 外部调用; 可通过 uvicorn workers 与
LLM 缓存横向扩展. 详细压测数据见 `perf-results/`.

## 10. 为什么现在不拆微服务或迁移前端框架?

答: 比赛优先; 改动面越大风险越大; 当前边界已用模块化隔离 (6 层架构), 迁移可在
P2 阶段做. 比赛一周内的目标是把"主链一次跑通", 不是"系统重构".

## 11. 哪些功能是实时真实能力, 哪些是降级演示?

- **实时**: 画像 / 苏格拉底 / 路径调整 / 掌握度变化 / 教师观察
- **降级**: TTS / ASR / Bilibili / 视频生成 (P2 阶段补)

## 12. CI 如何证明主链没有发生回归?

答: `tests/demo/test_live_path_smoke.py` 20 次连续跑通, 失败必阻塞合并.
CI 工作流在 `.github/workflows/test.yml`, 移除了 `|| echo` 假绿灯 (Task 10).
