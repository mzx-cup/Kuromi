# 演示手册 (Runbook)

> 比赛现场用的逐步操作清单. 现场操作员 (非开发) 也能照表执行.

## 1. 启动顺序

1. 设置 `JWT_SECRET`:
   ```bash
   export JWT_SECRET=$(python -c "import secrets; print(secrets.token_urlsafe(48))")
   ```
2. 启动比赛模式:
   ```bash
   bash scripts/start_competition.sh
   ```
3. 等待健康检查通过:
   ```bash
   bash scripts/health_check.sh
   ```
   期望输出结尾含 `service ready: ok` 或 `degraded`.
4. 浏览器打开 `http://localhost:8000/html/login.html`
5. 用演示账号 `demo_student_1` / `Demo@123` 登录

## 2. 演示主链 (10-12 分钟)

| 步骤 | 操作 | 预期 | 截图位 |
|---|---|---|---|
| 1. 画像 | 进入 personal 页 | 显示已有学习画像 (雷达图) | 顶部 |
| 2. 弱点诊断 | 点击 "诊断我的弱点" | 返回 1-2 个 weak concept | 弱点卡片 |
| 3. 苏格拉底 | 进入教学页, 提问 "什么是勾股定理" | 引导式回答 (含追问) | 对话流 |
| 4. 路径调整 | 系统展示推荐路径变化 | nodes 列表与之前不同 | 路径面板 |
| 5. 微练习 | 完成 1-2 题 | 显示正误 + 掌握度变化 | 练习卡片 |
| 6. 掌握度变化 | 回到 personal 页 | 掌握度条动起来, 数值变化 | "本次学习后" 卡片 |
| 7. 教师观察 | 切换到教师账号 | 看到 AI 建议 + 班级观察 | 教师 dashboard |

## 3. 降级预案

- **LLM 超时**: UI 显示 `fallback` 标记 (右上角徽章), 改用种子响应, 主链继续.
- **KB 不可用**: 静默回退到结构化 SQL 检索, 引用列表变空, 但答案仍生成.
- **任意外部依赖失败**: trace_id 写入 `demo-results/competition-YYYYMMDD/trace.log`,
  演示可继续, 答辩时可现场调出 trace 回放.

## 4. 录像备份

- 主链全屏录制, 备份在 `video/competition-backup/`
- 录像脚本: `scripts/playback.sh <session_dir>`

## 5. 现场事故清单

| 现象 | 立刻做的事 | 不要做的事 |
|---|---|---|
| `/api/health` 一直 down | `bash scripts/reset_demo.sh --json` 后重启 | 不要改代码 |
| 教师页空白 | 切回 student 页后重登 | 不要清浏览器 cookie |
| 浏览器控制台报 403 | 检查 `STARLEARN_ALLOWED_ORIGINS` 环境变量 | 不要禁用中间件 |
| 演示卡在苏格拉底 | 刷新页面 (会读 trace_id 续聊) | 不要重启服务 |
