# 前端技术债清点与阶段式修复 — 设计文档

**日期**: 2026-06-08
**状态**: 待用户审阅
**关联报告**: `docs/superpowers/notes/frontend-style-conflict-resolution-final-report-2026-06-08.md` §已知遗留问题

---

## Context（背景）

2026-06-08 完成的前端样式冲突解决方案留下 3 项明确标记的「已知遗留问题」：

1. CSS 变量引用完整性：406 个未定义变量（多数是 Tailwind 编译产物，少数是真正应迁到 `tokens.css` 的设计 token）
2. Playwright L3 测试：环境未装，测试文件已创建待环境就绪
3. 复合全局选择器 (`*, *::before, *::after`)：审计脚本未覆盖，已知存在于 `plant.css` 等文件

同时，整个前端（31 个 HTML / 20+ CSS / 30+ JS）经过 4-6 月的多轮重构（Constellation Prism 主题、Wave 1-3 卡片统一、Alpine.js 迁移），但**没有做过一次系统性的技术债扫描**。本次工作的目标：

- 解决报告遗留问题
- 同时做一次全量前端技术债扫描
- 输出一份带优先级的清点报告
- 后续按 P0 → P1 → P2 → P3 阶段式推进修复（修复在后续 plan 中，本 spec 只负责清点）

---

## Goals（目标）

### In scope
- 报告遗留 3 项的 100% 解决（产出结构化数据）
- 全量前端技术债扫描
- 输出一份带 P0/P1/P2/P3 优先级的清点 Markdown 报告
- 3 个新审计脚本可在 CI 中独立运行
- 合并报告生成器复用 6 个已有脚本的输出，不重复扫描

### Out of scope
- 实际修复任何代码（修复在后续 plan）
- 后端 Python 技术债扫描
- 引入新 Python 依赖
- 改动现有 6 个审计脚本的源码
- CI workflow 配置

---

## 架构（Architecture）

```
┌──────────────────────────────────────────────────────────────┐
│                  遗留问题解决总体架构                          │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  Layer 1: 数据采集 (3 个新审计脚本)                           │
│  ┌──────────────────┐  ┌──────────────────┐                  │
│  │ audit_undefined  │  │ audit_compound   │  ┌────────────┐ │
│  │ _css_vars.py     │  │ _selectors.py    │  │ audit_     │ │
│  │                  │  │                  │  │ frontend_  │ │
│  │ 扫所有 CSS 文件  │  │ 扫 *, *::before, │  │ smells.py  │ │
│  │ 提取 var() 引用  │  │ *::after, html,  │  │            │ │
│  │ 分类输出         │  │ body, :root 等   │  │ 多维 smell │ │
│  └──────────────────┘  └──────────────────┘  └────────────┘ │
│           │                     │                  │         │
│           └─────────────────────┴──────────────────┘         │
│                              │ JSON                           │
│                              ▼                                │
│  Layer 2: 合并报告生成器                                      │
│  ┌──────────────────────────────────────┐                    │
│  │ build_tech_debt_inventory.py         │                    │
│  │ - 聚合 3 个新脚本 + 6 个已有脚本     │                    │
│  │ - 按 P0/P1/P2/P3 优先级排序          │                    │
│  │ - 每项含: 位置 / 影响 / 修复成本     │                    │
│  │ - 输出: docs/superpowers/notes/       │                    │
│  │   frontend-tech-debt-2026-06-XX.md   │                    │
│  └──────────────────────────────────────┘                    │
│                              │                                │
│                              ▼                                │
│  Layer 3: 阶段式修复 (在后续 plan 中)                          │
│  - P0: 阻塞性 / 风险高 → 立即修复                              │
│  - P1: 重要但非阻塞 → 排期修复                                 │
│  - P2: 改进项 → 视情况修复                                    │
│  - P3: 记录但不修复                                           │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

### 关键设计决策
- **数据 / 报告分离**：脚本只产出原始数据 (JSON)，报告生成器负责排版和分级。这样未来可单独重跑报告而无需重扫。
- **复用而非重写**：6 个已有脚本的输出（特别是 `verify_css_vars.py`）作为 Layer 2 的输入，不重复扫描。
- **优先级定义**：
  - P0 = 阻塞性 / 跨页面功能破损（如真未定义变量导致视觉回退）
  - P1 = 影响一致性 / 可维护性显著下降（如 `*, *::after` 在多个文件外溢）
  - P2 = 代码 smell，修复收益中等（如魔法数字、console.log 残留）
  - P3 = 锦上添花，记录备查（如 `*, *::before` 在 CSS reset 中是预期行为）

---

## 组件（Components）

### 3.1 `scripts/audit_undefined_css_vars.py`

**输入**: `css/` 目录下所有 `.css` 文件

**处理**:
1. 用正则 `var\(\s*--([a-z0-9-]+)\s*[,)]` 提取所有变量引用
2. 用正则 `--([a-z0-9-]+)\s*:` 提取所有变量定义
3. 差集 = 未定义变量
4. 对每个未定义变量判断来源：
   - `tailwind.css` 内部出现的 → `[Tailwind 编译产物]`
   - 出现在 `tailwind.css` 且 Tailwind 官方 utility 中存在的类名 → `[Tailwind class-as-var]`
   - 出现在 `tokens.css` 但未定义的 → `[应迁 tokens.css]`
   - 其他 → `[真未定义]`

**输出**: `output/audit_undefined_css_vars.json`
```json
{
  "scan_date": "2026-06-XX",
  "total_refs": 534,
  "total_defs": 150,
  "undefined_count": 406,
  "categories": {
    "tailwind_product": 350,
    "tailwind_class_as_var": 30,
    "should_migrate_to_tokens": 20,
    "truly_undefined": 6
  },
  "items": [
    {
      "var": "--my-color",
      "category": "should_migrate_to_tokens",
      "files_using": ["hub.css", "personal.css"],
      "first_seen_line": "hub.css:42"
    }
  ]
}
```

### 3.2 `scripts/audit_compound_selectors.py`

**输入**: `css/` 目录下所有 `.css` 文件

**处理**: 匹配以下模式并报告
- `*` 选择器（含 `*, *::before, *::after`）
- `html` / `body` 单元素选择器（项目要求只能在 `app-base.css`）
- 出现位置 = `file_path:line_number`

**输出**: `output/audit_compound_selectors.json` + 终端 `OK` / `FAIL` 摘要

### 3.3 `scripts/audit_frontend_smells.py`（多维扫描）

**输入**: `html/` + `js/` + `css/` 全量

**检测项**:
| # | Smell | 检测方法 |
|---|-------|---------|
| 1 | HTML 内联 `style="..."` | 正则 `style\s*=\s*"` |
| 2 | JS 内联 `onclick="..."` 等 | 正则 `on\w+\s*=\s*"` |
| 3 | 单文件 > 1000 行 | `wc -l` |
| 4 | 重复 CSS 规则（跨文件同选择器 + 同属性） | 后缀树 / 哈希 |
| 5 | 未使用 CSS 类（HTML 中无引用的类） | 反向查找 |
| 6 | 魔法数字（颜色/尺寸硬编码） | 正则 `#[0-9a-f]{3,6}` / `\d+px` |
| 7 | `console.log` 残留 | 正则 |
| 8 | `TODO` / `FIXME` / `XXX` 注释 | 正则 |

**输出**: `output/audit_frontend_smells.json`

### 3.4 `scripts/build_tech_debt_inventory.py`

**输入**: 3 个新脚本的 JSON + 6 个已有脚本的输出

**处理**:
1. 聚合所有 findings
2. 按 P0/P1/P2/P3 排序
3. 生成 Markdown 报告

**输出**: `docs/superpowers/notes/frontend-tech-debt-2026-06-XX.md`

**报告结构**:
```markdown
# 前端技术债清单 (2026-06-XX)

## 概览
- 总问题数: N
- P0: X | P1: Y | P2: Z | P3: W

## P0 阻塞项
### [CSS-001] tokens.css 缺失 6 个未定义变量
- 位置: hub.css:42, personal.css:88 ...
- 影响: 视觉回退到浏览器默认色
- 修复成本: 低 (添加 6 行 :root 定义)
- 建议: 一次性提交

## P1 重要项
... (每个问题一节)

## P2 改进项
...

## P3 记录备查
...

## 报告遗留问题解决状态
- [x] 报告遗留 1: 406 undefined vars → 已分类
- [x] 报告遗留 2: Playwright L3 → 已记录 (环境未装, 暂不修)
- [x] 报告遗留 3: compound selectors → 已审计
```

### 数据流图

```
html/ css/ js/                  (项目源)
       │
       ▼
┌──────────────────────────┐
│ 3 新审计脚本 (独立可跑)   │──┐
└──────────────────────────┘  │
┌──────────────────────────┐  │
│ 6 已有审计脚本 (复用)     │──┤
└──────────────────────────┘  │
                             ▼
                    output/*.json (原始数据)
                             │
                             ▼
                  build_tech_debt_inventory.py
                             │
                             ▼
            docs/superpowers/notes/frontend-tech-debt-2026-06-XX.md
                             │
                             ▼
              用户审阅 → 阶段式修复 (后续 plan)
```

---

## 错误处理（Error Handling）

| 失败场景 | 行为 | 用户体验 |
|---------|------|---------|
| 单个 CSS 文件无法读取 | 记录警告到 stderr，继续扫其他文件 | 终端输出 `⚠️ skip: css/xxx.css (PermissionError)` |
| 单个文件 parse 错误（CSS 语法严重损坏） | 用 `try/except` 包裹正则匹配，记录该文件 skipped | 报告中 `skipped_files` 字段列出 |
| 某个新脚本崩溃 | 该脚本退出码非 0，其他 2 个脚本的 JSON 仍可被 Layer 2 读取 | 终端红色 `FAIL: audit_xxx crashed` + 报告顶部告警条标记 partial 状态 |
| 报告生成器发现缺某个 JSON | 列出缺失的输入，提示 `请先运行 python scripts/audit_xxx.py` | 终端红色 `MISSING: output/audit_xxx.json` |
| 报告遗留问题中 Playwright L3（环境未装） | 不报错，标记为 `[Deferred: env not ready]` | 报告 §遗留状态块明确标注 |

**所有脚本的统一约定**:
- 退出码：`0` = OK（无发现 / 全部 P3 级别），`1` = 发现 ≥ P0/P1 失败项，`2` = 工具自身故障
- Windows 兼容（参考已有的 `d8b0ef6` 提交）：脚本入口加 `sys.stdout.reconfigure(encoding='utf-8')`
- 中文输出用 UTF-8 编码

---

## 测试（Testing）

### 单元测试
每个新脚本对应一个 `tests/scripts/test_audit_xxx.py`：

| 测试用例类型 | 数量 | 示例 |
|-------------|------|------|
| 正向：标准输入 | 1 | 给 fixture CSS，验证 JSON 输出结构正确 |
| 反向：边界条件 | 3 | 空文件、仅注释文件、巨文件 (>1MB) |
| 错误处理 | 2 | 文件不存在、读权限被拒 |
| Windows 路径 | 1 | 含中文 / 空格路径 |

### 集成测试
**`tests/frontend/tech-debt-inventory.spec.js`** (Playwright L3)
- 验证生成的报告文件存在且可解析
- 验证报告中 P0 项都有具体 `file:line` 引用
- 验证报告引用了全部 9 个审计脚本的输出（3 新 + 6 旧）

### 验收检查清单（人工）
报告生成后，逐项跑：
1. `python scripts/audit_undefined_css_vars.py` → 退出码 0/1
2. `python scripts/audit_compound_selectors.py` → 同上
3. `python scripts/audit_frontend_smells.py` → 同上
4. `python scripts/build_tech_debt_inventory.py` → 退出码 0
5. 打开报告 Markdown，肉眼检查 P0 分类是否合理

---

## YAGNI（不做什么）

- **不修复 P0 之外的任何代码**：本 spec 只负责「清点」，修复在后续 plan 中。
- **不引入新依赖**：所有脚本用 Python 3.10+ 标准库（`re` / `json` / `pathlib` / `collections`），避免新增 `requirements.txt` 项。
- **不做 UI/前端改动**：所有交付物在 `scripts/` + `docs/superpowers/notes/`。
- **不重写已有 6 个脚本**：只读取它们的输出（如 stdout / 已落盘的 JSON），不修改源码。
- **不强制 CI 集成**：脚本可在 CI 中调用，但本 spec 不写 `.github/workflows/` 配置。

---

## 风险与缓解（Risks）

| 风险 | 概率 | 影响 | 缓解 |
|------|------|------|------|
| 406 个 undefined vars 中真未定义只占少数，多数是 Tailwind 编译产物导致误报 | 高 | 报告噪音大 | §3.1 的 `categories` 字段按 4 类分桶，统计值暴露给用户 |
| `*, *::before, *::after` 在很多 CSS reset 中是合法且必要的 | 高 | 误报 P0 | 报告中标 `[Expected: CSS reset]`，从 P0 降为 P3 |
| JS 文件过多（30+ 个）扫描慢 | 中 | 总耗时 > 5 min | 只扫 size > 10KB 的文件 / 加 `--quick` 参数 |
| 报告 Markdown 中重复出现同一问题（多文件同源） | 中 | 报告冗长 | Layer 2 做去重：同 root cause 合并条目 |

---

## 验收标准（Acceptance Criteria）

本 spec 完成的标志：
1. 3 个新审计脚本存在且运行成功
2. 1 个报告生成器存在且运行成功
3. 生成的 `frontend-tech-debt-2026-06-XX.md` 存在
4. 报告包含 P0/P1/P2/P3 分级
5. 报告末尾「报告遗留问题解决状态」三项全部 `[x]`
6. 6 个单元测试文件存在且通过
7. git 已提交（中文 commit message）

---

## 后续步骤

spec 批准后 → 调用 `writing-plans` skill → 产出实施计划 → 阶段式实施：
- Phase 1: 3 个新审计脚本
- Phase 2: 报告生成器 + 单元测试
- Phase 3: 集成测试 + 验收
- Phase 4: git 提交 + 文档更新
