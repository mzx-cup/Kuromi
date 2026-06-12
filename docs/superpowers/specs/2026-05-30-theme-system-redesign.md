# 主题系统配色优化 — 设计文档

## 目标

重构主题系统的配色架构，解决暗色对比度不足、色阶过渡不自然、跨页面不一致等问题，同时还原霓虹主题并支持用户自定义配色。

## 概览

- **架构**：三层 Token 体系（原始层 → 自动色阶层 → 语义层）
- **预设主题**：5 个（3 个现有重新校色 + 1 个新增森林绿 + 1 个还原霓虹）
- **切换机制**：模式（亮/暗）+ 配色选择 两层结构
- **用户自定义**：弹窗快速选择器 + 设置页完整 Token 编辑器
- **持久化**：localStorage 为主 + 服务端 JSON 同步
- **自定义主题**：无限制，用户可创建/命名/编辑

---

## 一、三层 Token 架构

### 第一层：原始 Token（Primitive）—— 每个主题定义 ~10 个值

```css
[data-theme="warm-morning"] {
  --brand-500:        #f97316;
  --neutral-500:      #78716c;
  --neutral-hue:      30;
  --accent-amber:     #f59e0b;
  --accent-teal:      #14b8a6;
  --accent-rose:      #f43f5e;
  --accent-violet:    #8b5cf6;
  --surface-page-l:   0.97;
  --surface-card-l:   1.0;
  --mode:             "light";
}
```

亮色主题 `surface-page-l` 和 `surface-card-l` 取高值（0.90–1.0），暗色主题取低值（0.08–0.20）。

### 第二层：自动生成色阶（Generated Scale）—— 全局定义一次

使用 `color-mix()` + `oklch` 从原始值推导完整色阶，每个主题无需手写：

```css
:root {
  /* 品牌色阶 */
  --brand-50:  color-mix(in oklch, var(--brand-500) 8%, white);
  --brand-100: color-mix(in oklch, var(--brand-500) 20%, white);
  --brand-200: color-mix(in oklch, var(--brand-500) 38%, white);
  --brand-300: color-mix(in oklch, var(--brand-500) 55%, white);
  --brand-400: color-mix(in oklch, var(--brand-500) 78%, white);
  --brand-600: color-mix(in oklch, var(--brand-500) 80%, black);
  --brand-700: color-mix(in oklch, var(--brand-500) 58%, black);
  --brand-800: color-mix(in oklch, var(--brand-500) 35%, black);
  --brand-900: color-mix(in oklch, var(--brand-500) 12%, black);

  /* 中性色阶 — 亮暗通用，从 neutral-500 + hue 推导 */
  --neutral-50:  color-mix(in oklch, var(--neutral-500) 8%, white);
  --neutral-100: color-mix(in oklch, var(--neutral-500) 20%, white);
  --neutral-200: color-mix(in oklch, var(--neutral-500) 38%, white);
  --neutral-300: color-mix(in oklch, var(--neutral-500) 58%, white);
  --neutral-400: color-mix(in oklch, var(--neutral-500) 80%, white);
  --neutral-600: color-mix(in oklch, var(--neutral-500) 78%, black);
  --neutral-700: color-mix(in oklch, var(--neutral-500) 56%, black);
  --neutral-800: color-mix(in oklch, var(--neutral-500) 34%, black);
  --neutral-900: color-mix(in oklch, var(--neutral-500) 12%, black);
}
```

`oklch` 保证色阶过渡在视觉上均匀平滑。

### 第三层：语义 Token（Semantic）—— 全局定义一次，所有主题共享

```css
:root {
  --surface-page:      oklch(var(--surface-page-l) 0.02 var(--neutral-hue));
  --surface-card:      oklch(var(--surface-card-l) 0.02 var(--neutral-hue));
  --surface-hover:     color-mix(in oklch, var(--surface-card), var(--brand-500) 5%);
  --surface-pressed:   color-mix(in oklch, var(--surface-card), var(--brand-500) 10%);
  --surface-overlay:   oklch(0.15 0.02 var(--neutral-hue) / 0.6);
  --surface-nav:       oklch(var(--surface-card-l) 0.03 var(--neutral-hue) / 0.85);

  --text-heading:      var(--neutral-900);
  --text-body:         var(--neutral-700);
  --text-muted:        var(--neutral-500);
  --text-placeholder:  var(--neutral-400);
  --text-link:         var(--brand-600);
  --text-on-brand:     white;

  --shadow-xs: 0 1px 2px color-mix(in oklch, var(--neutral-900) 6%, transparent);
  --shadow-sm: 0 1px 3px color-mix(in oklch, var(--neutral-900) 8%, transparent);
  --shadow-md: 0 4px 12px color-mix(in oklch, var(--neutral-900) 10%, transparent);
  --shadow-lg: 0 8px 24px color-mix(in oklch, var(--neutral-900) 14%, transparent);

  --radius-sm: 8px;
  --radius-md: 14px;
  --radius-lg: 20px;
  --radius-full: 9999px;

  --space-xs: 4px;  --space-sm: 8px;  --space-md: 16px;
  --space-lg: 24px; --space-xl: 40px;
}
```

### 对比度保证

亮色主题下：
- `--text-body`（neutral-700）vs `--surface-card` → L 差值 ≥ 40% → WCAG AA（~4.5:1）
- `--text-muted`（neutral-500）vs `--surface-card` → L 差值 ≥ 25% → WCAA AA 大号文字（~3:1）

暗色主题下：
- 原始层将 neutral 色阶调暗，语义层的 `--text-body: var(--neutral-700)` 自动映射到浅色
- 因为暗色主题的 `neutral-700` 是浅色（color-mix with white 多），`neutral-100` 是深色
- 这避免了"暗底浅字时复用亮色主题映射导致对比度缩水"的问题

Token 编辑器中提供实时对比度数值展示。

### 清理旧代码

- 删除 `--primary`、`--accent` 等旧映射变量
- 删除 `theme.js` 中的 `renderSakuraParticles()` 死代码（~60 行）
- 删除 `hub.css` 中被隐藏的 `.theme-toggle-btn` 相关样式
- 删除 `settings.html` 中断开连接的旧 5 色选择器
- 删除 index.css 中残留的 `[data-theme="light"]`、`[data-theme="ocean"]` 等从未被设置的伪选择器

---

## 二、预设主题矩阵

| 主题 ID | 名称 | 模式 | 品牌色 | 底色基调 | 状态 |
|---------|------|------|--------|----------|------|
| `warm-morning` | 日出晨光 | 亮色 | 暖橙 `#f97316` | 暖白 L=0.97 | 重新校色 |
| `forest-light` | 林间晨光 | 亮色 | 森林绿 `#16a34a` | 冷白 L=0.97 | 新增 |
| `study-night` | 深夜书房 | 暗色 | 暖橙 `#fb923c` | 暖深灰 L=0.12 | 重新校色 |
| `starry-night` | 星夜 | 暗色 | 金色 `#fbbf24` | 冷紫灰 L=0.10 | 重新校色 |
| `neon-cyber` | 霓虹电光 | 暗色 | 电光青 `#00e5ff` | 纯黑 L=0.06 | 还原新增 |

### 霓虹主题特殊处理

霓虹的原始层使用高饱和荧光色。语义层中少数 token 通过 `[data-theme="neon-cyber"]` 覆盖：

```css
[data-theme="neon-cyber"] {
  /* 阴影替换为辉光 */
  --shadow-sm: 0 0 6px color-mix(in oklch, var(--brand-500) 40%, transparent);
  --shadow-md: 0 0 14px color-mix(in oklch, var(--brand-500) 50%, transparent);
  --shadow-lg: 0 0 28px color-mix(in oklch, var(--brand-500) 60%, transparent);
  /* 保持荧光饱和度的色阶混合参数不同 */
  --brand-50:  color-mix(in oklch, var(--brand-500) 12%, black);
  --brand-100: color-mix(in oklch, var(--brand-500) 25%, black);
  /* ... 暗底上的荧光色阶，少混白多混黑 */
}
```

其余 90% 语义 token 走通用层，不破坏架构。

---

## 三、亮/暗切换机制

**旧机制**：循环切换 warm-morning → study-night → starry-night → warm-morning

**新机制**：两层结构

```
mode:  "light" | "dark"
theme: 当前模式下选中的配色 ID
```

- 亮色模式配 light 线主题（warm-morning, forest-light）
- 暗色模式配 dark 线主题（study-night, starry-night, neon-cyber）
- 切换模式时自动使用该模式下上次选中的主题
- localStorage 存储结构变为 `{ mode, theme, wallpaper, customThemes }`

---

## 四、用户自定义

### 弹窗（快速切换）

现有主题设置 Modal 中：
- 亮色/暗色模式开关（顶部）
- 当前模式下预设配色卡片列表（横向滚动）
- 品牌色快速选择：`input[type=color]` + 预设推荐色块
- "高级编辑 →" 跳转链接

### 设置页（完整 Token 编辑器）

在 `settings.html` 中新增区域：
- **品牌色**：色盘 + 推荐预设色（暖橙/森林绿/电光青/金色/紫罗兰/玫红/自定义）
- **中性色基调**：暖灰 / 冷灰 / 纯灰 三选一 + 明度滑块
- **装饰色**：4 个 accent 各一个色盘
- **实时预览区**：卡片 + 文字 + 按钮迷你预览，即时反映修改
- **对比度指示器**：每个文本 token 旁显示与底色的对比度，绿/黄/红三色标记
- **保存/重置**：命名为自定义主题并保存 / 恢复默认
- 编辑的是原始层 ~10 个值，色阶和语义层自动重新计算
- 界面用中文标签（"品牌色"、"页面底色"、"卡片底色"），不暴露 CSS 变量名

### 自定义主题存储格式

```json
{
  "id": "custom-1",
  "name": "我的配色",
  "mode": "dark",
  "primitives": {
    "brand-500": "#f97316",
    "neutral-500": "#78716c",
    "neutral-hue": 30,
    "accent-amber": "#f59e0b",
    "accent-teal": "#14b8a6",
    "accent-rose": "#f43f5e",
    "accent-violet": "#8b5cf6",
    "surface-page-l": 0.10,
    "surface-card-l": 0.14
  }
}
```

localStorage key: `starlearn_custom_themes`

---

## 五、服务端持久化

### API

```
POST /api/user/theme/sync
  请求体: { mode, theme, wallpaper, customThemes }
  响应:   { ok: true }

GET /api/user/theme/sync
  响应:   { mode, theme, wallpaper, customThemes }
```

### 同步策略

- 登录后从服务端拉取，合并到 localStorage（服务端优先作为初始值）
- 本地修改后 debounce 2 秒静默同步
- 同步失败不影响本地使用
- 未登录用户仅使用 localStorage

### 数据库

`users` 表新增 `theme_prefs` JSON 列（TEXT/JSON 类型），直接存主题偏好 JSON。

---

## 六、文件变更清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `css/index.css` | 重写 | 三层 token 架构重构，删除旧映射/死选择器，新增主题块 |
| `css/hub.css` | 修改 | 删除隐藏的 `.theme-toggle-btn` 样式，适配新 token |
| `js/theme.js` | 重写 | 两层切换逻辑、自定义主题管理、同步引擎、删除死代码 |
| `html/settings.html` | 修改 | 新增 token 编辑器区域 |
| `js/settings.js` | 修改/新增 | token 编辑器交互逻辑 |
| `main.py` | 修改 | 新增 `/api/user/theme/sync` 端点 |
| `db.py` | 修改 | `users` 表加 `theme_prefs` 列 |
| 所有 `html/*.html` | 审查 | 确认使用语义 token，无硬编码颜色 |
| 所有 `css/*.css` | 审查 | 同上，适配新 token 体系 |
| `css/loading.css` | 审查 | 适配新 token |

---

## 七、测试验证清单

- [ ] 5 个预设主题色阶视觉均匀、无跳跃
- [ ] 亮色主题 WCAG AA 对比度（正文 ≥ 4.5:1，辅助文字 ≥ 3:1）
- [ ] 暗色主题 WCAG AA 对比度
- [ ] 霓虹主题发光效果正常，文字可读
- [ ] 模式切换后配色跟随正确
- [ ] 品牌色选择器实时预览反应正确
- [ ] Token 编辑器保存/加载/重置
- [ ] 自定义主题跨页面一致
- [ ] 服务端同步正常（登录/未登录/网络异常）
- [ ] 所有现有页面无颜色异常
- [ ] 壁纸系统与新 token 体系兼容
- [ ] `data-glass` 毛玻璃效果正常
