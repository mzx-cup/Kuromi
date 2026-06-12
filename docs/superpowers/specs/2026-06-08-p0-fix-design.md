# P0 前端技术债修复 — 设计文档

**日期**: 2026-06-08
**状态**: 待用户审阅
**关联报告**: `docs/superpowers/notes/frontend-tech-debt-2026-06-08.md`
**关联 spec**: `docs/superpowers/specs/2026-06-08-frontend-tech-debt-inventory-design.md` (上一阶段产出)

---

## Context（背景）

2026-06-08 完成的前端技术债清点识别出 **217 个 P0 阻塞项**：
- **212 个真未定义 CSS 变量** (truly_undefined 类别)
- **5 个复合全局选择器外溢** 文件 (classroom-premium-dna / hub / index / personal / plant)

这些 P0 问题导致：
- 视觉回退到浏览器默认色（页面缺色、对比度低、品牌不一致）
- 选择器冲突导致样式不稳定（`*, *::before, *::after` 在多个文件覆盖规则）

**本 spec 目标**：在不引入视觉 regression 的前提下，**单 commit** 修复全部 217 个 P0 项。

---

## 用户已确认的设计决策

1. **变量修复策略**: 轻量补全 — 把 212 个 var 原样补到 `tokens.css` 的 `:root` 块，附语义推断的色值。调用点不动。
2. **选择器修复策略**: 删除重复规则 — 5 个外溢文件中删去 `*` / `html` / `body` 顶层规则，保留 `app-base.css` 中的官方版。
3. **变量赋值方法**: 语义推断 — 基于 var 名推断（如 `accent-amber` → `#f59e0b`）。不调用 LLM/外部 API。
4. **提交粒度**: 单 commit — 全部 217 个修复合并为 1 个 commit。
5. **验收方法**: 安装 Playwright + 跑 `visual.spec.js`，无降级 fallback。
6. **范围**: Playwright 安装合并进本 plan。

---

## 架构（Architecture）

```
┌──────────────────────────────────────────────────────────────┐
│                 P0 修复总体架构                                │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  Layer 1: 数据读取                                            │
│  ┌────────────────────────────────────┐                     │
│  │ 读 output/audit_undefined_css_     │                     │
│  │ vars.json → 212 个 P0 var 列表      │                     │
│  │ 读 output/audit_compound_          │                     │
│  │ selectors.json → 5 个外溢文件列表   │                     │
│  └────────────────────────────────────┘                     │
│                              │                                │
│                              ▼                                │
│  Layer 2: 修复生成器 (1 个 Python 脚本)                       │
│  ┌────────────────────────────────────┐                     │
│  │ fix_p0_tech_debt.py                │                     │
│  │ ┌────────────────────────────┐     │                     │
│  │ │ 语义推断规则 (静态 dict)    │     │ ← 人类预先定义     │
│  │ │ accent-amber → #f59e0b     │     │                     │
│  │ │ avatar-gradient-student    │     │                     │
│  │ │   → #3b82f6                │     │                     │
│  │ │ ...                        │     │                     │
│  │ └────────────────────────────┘     │                     │
│  │ + 5 个外溢文件的处理逻辑            │ ← 直接删除重复规则 │
│  └────────────────────────────────────┘                     │
│                              │                                │
│                              ▼                                │
│  Layer 3: 应用变更                                            │
│  - tokens.css 追加 ~212 行                                    │
│  - 5 个外溢 CSS 删 ~X 行                                     │
│  - 1 个 commit: "fix(css): 修复 217 个 P0 前端技术债"         │
│                                                              │
│  Layer 4: 验收 (3 重, 无降级)                                 │
│  ① 重跑 audit 3 个脚本 → P0 计数 = 0                        │
│  ② 跑 visual_verify_static.py → 5 页面 200                  │
│  ③ 跑 Playwright visual.spec.js → 截图与基准对比            │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

### 关键设计决策
- **数据驱动**: 修复脚本读 audit JSON 而非硬编码 212 个 var 名 — 与 inventory 体系解耦
- **语义推断 + 静态规则**: 不调用 LLM / 外部 API — 0 依赖、0 token、可重复
- **3 重验收, 无降级**: 静态检查 (L1) + HTTP 200 (L2) + 视觉对比 (L3) — 层层递进, 任何失败都阻断 commit
- **单 commit**: 用户已确认所有 217 个修复合并为 1 个 commit

---

## 组件（Components）

### 4.1 语义推断规则（静态映射表）

**核心结构**：`scripts/inference_rules.py` 模块化导出，包含 3 张表 + 1 个函数：

```python
# 颜色名 → 十六进制
COLOR_NAMES = {
    "amber": "#f59e0b", "rose": "#f43f5e", "violet": "#8b5cf6",
    "purple": "#8b5cf6", "teal": "#14b8a6", "blue": "#3b82f6",
    "green": "#10b981", "orange": "#f97316", "red": "#ef4444",
    "yellow": "#eab308", "pink": "#ec4899", "cyan": "#06b6d4",
    "indigo": "#6366f1", "lime": "#84cc16", "fuchsia": "#d946ef",
    "sky": "#0ea5e9", "glow": "#fef3c7", "hover": "#fde68a",
    "strong": "#1e40af", "index": "#3b82f6",
}

# 角色 → 颜色 (avatar-gradient-* 模式)
ROLE_COLORS = {
    "agent": "#8b5cf6", "moderator": "#f59e0b",
    "student": "#3b82f6", "teacher": "#10b981",
    "user": "#3b82f6", "system": "#6b7280",
}

FALLBACK_COLOR = "#9ca3af"


def infer_value(var_name: str) -> tuple[str, str]:
    """返回 (value, source_tag), source_tag: 'mapped'|'role'|'fallback'"""
    for token in var_name.split("-"):
        if token in COLOR_NAMES:
            return COLOR_NAMES[token], "mapped"
    if var_name.startswith("avatar-gradient-"):
        role = var_name.replace("avatar-gradient-", "")
        if role in ROLE_COLORS:
            return ROLE_COLORS[role], "role"
    return FALLBACK_COLOR, "fallback"
```

**自动注释**: fallback 的 var 会在 `tokens.css` 旁加 `/* TODO: refine color */` 注释，便于后续 P1 调优时定位。

### 4.2 `scripts/fix_p0_tech_debt.py`

**主流程**:
1. 读 `output/audit_undefined_css_vars.json` → 提取 `category=="truly_undefined"` 的 212 个 var
2. 读 `output/audit_compound_selectors.json` → 提取 `allowed==false` 的 5 个文件
3. 对每个 var 调用 `infer_value()` 得到 `(value, source)`
4. 追加到 `css/tokens.css` 末尾的 `:root { }` 块（按字母排序，注释标注 source）
5. 对 5 个外溢文件：解析文件，找到 `* { }` / `html { }` / `body { }` 规则，删除，写回
6. 输出修复摘要（212 vars + 5 files）

**变更前自动备份**: `css/tokens.css.bak-pre-p0-fix`（commit 时不入库，用于紧急回退）

**退出码**:
- `0` = 成功
- `1` = audit JSON 缺失
- `2` = 工具自身故障

### 4.3 5 个外溢文件处理逻辑

外溢文件：`classroom-premium-dna.css` / `hub.css` / `index.css` / `personal.css` / `plant.css`

**判定规则**:
- `* { ... }` → 删除
- `html { ... }` → 删除（前提：`app-base.css` 中已有 html 规则）
- `body { ... }` → 删除（前提：`app-base.css` 中已有 body 规则）
- 复合如 `*, *::before, *::after { ... }` → 整体删除

**安全检查**: 删除前 diff 与 `app-base.css` 中的对应规则对比，内容不一致 → 报警（手动决策），不自动删。

### 4.4 三重验收（无降级）

| 层 | 工具 | 期望 | 失败处理 |
|----|------|------|---------|
| L1 静态 | 重跑 3 个 audit 脚本 | P0 计数 = 0 | 阻断 commit，打印剩余 P0 |
| L2 HTTP | 跑 `scripts/visual_verify_static.py` | 5 高风险页 200 | 阻断 commit，输出失败 URL |
| L3 视觉 | `npx playwright test visual.spec.js` | 0 视觉 diff | 阻断 commit，输出 diff 截图 |

**L3 Playwright 验收流程**:
1. `npx playwright install chromium` (从 npm 缓存下载，已修复 ACL 问题)
2. `npx playwright test visual.spec.js --update-snapshots` (首次生成基准)
3. 修完 P0 后 `npx playwright test visual.spec.js` (回归对比)
4. 失败时查看 `test-results/` 下的 diff 截图

**L3 浏览器下载失败处理（无降级）**:
1. 重试 3 次（指数退避：1s / 4s / 16s）
2. 仍失败 → 切换镜像源：`PLAYWRIGHT_DOWNLOAD_HOST=https://npmmirror.com/mirrors/playwright`
3. 仍失败 → 输出明确错误信息（具体 URL、磁盘空间、代理设置提示），要求人工干预
4. **任何一步都不自动跳过 L3**

---

## 错误处理（Error Handling）

| 失败场景 | 行为 | 退出码 |
|---------|------|--------|
| audit JSON 缺失 | 报错 `MISSING: output/xxx.json`，提示跑 audit | 1 |
| 某个 var 推断失败 | 已用 fallback 灰 + 注释，不报错 | 0 |
| 5 个外溢文件中某个删除规则后文件变 0 行 | 不阻断，记录 warning | 0 |
| `css/tokens.css` 写入失败 | 报错，保留 `.bak-pre-p0-fix` 备份 | 2 |
| L1 验收：P0 ≠ 0 | **阻断 commit**，打印剩余 P0 列表 | 1 |
| L2 验收：HTTP 200 失败 | 阻断 commit，输出失败 URL | 1 |
| L3 验收：浏览器下载失败 | 触发 3 重试 + 镜像源，**不降级** | 1 |
| L3 验收：视觉对比失败 | 输出 diff 截图，**阻断 commit** | 1 |

---

## YAGNI（不做什么）

- ❌ 不写 dry-run / `--check` 模式
- ❌ 不做自动 commit（外部 `git commit` 即可）
- ❌ 不修 P1/P2/P3 问题（出后续 plan）
- ❌ 不修改 audit 脚本
- ❌ 不动 `app-base.css`（外溢文件的规则若与 `app-base.css` 冲突仅报警，不自动合并）
- ❌ 不做主题切换适配（只补 var 默认值，深色/浅色主题由 P1 处理）
- ❌ 不写 CI workflow（out of spec scope）

---

## 验收标准（Acceptance Criteria）

| # | 验收项 | 期望 |
|---|--------|------|
| AC1 | 3 个 audit 重跑 | P0 总数 = 0 |
| AC2 | `css/tokens.css` 含 212 个新 var 定义 | `grep -c '^\s*--' tokens.css` 比 fix 前 +212 |
| AC3 | 5 个外溢文件不再含 `*`/`html`/`body` 顶层规则 | audit 验证 |
| AC4 | `visual_verify_static.py` 通过 | 5 高风险页 200 |
| AC5 | `visual.spec.js` 通过 | 0 视觉 diff |
| AC6 | 单 commit | 中文 message: `fix(css): 修复 217 个 P0 前端技术债` |
| AC7 | 备份文件 | `tokens.css.bak-pre-p0-fix` 在 commit 前可回退（commit 时不入库） |

---

## 风险与缓解（Risks）

| 风险 | 概率 | 影响 | 缓解 |
|------|------|------|------|
| 推断色值不准导致 visual regression | 中 | L3 视觉测试失败 | L3 必跑，失败阻断 commit |
| 5 个外溢文件删错规则导致样式破损 | 低 | 视觉破损 | 删除前 diff 与 app-base.css 验证 |
| `npx playwright install chromium` 慢/网络 | 中 | L3 阻塞 | 3 重试 + 镜像源切换（无降级） |
| Chromium 300MB 占用磁盘 | 已确认 82GB 可用 | 无 | — |
| 修复后 tokens.css 行数 +212，文件可读性下降 | 低 | 可维护性 | 按字母排序 + 注释分组 |

---

## 后续步骤

spec 批准后 → 调用 `writing-plans` skill → 产出实施计划 → 阶段式实施：
- Phase 1: 安装 Playwright 浏览器（npx install chromium）
- Phase 2: 跑 inventory audit 3 个脚本 + 收集 212 vars / 5 files
- Phase 3: 写 `inference_rules.py` + 单元测试
- Phase 4: 写 `fix_p0_tech_debt.py` + 应用修复
- Phase 5: 三重验收 (L1 + L2 + L3)
- Phase 6: 单 commit
