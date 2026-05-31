# 前端代码规范与AI操作手册

## 项目前端架构（三层模型）

```
┌─────────────────────────────────────────┐
│  Layer 1: 设计令牌  →  css/tokens.css   │  ← 所有页面共享的颜色、间距、阴影、圆角
├─────────────────────────────────────────┤
│  Layer 2: 通用组件  →  css/components.css│  ← 导航、按钮、卡片、弹窗、表单、徽章
├─────────────────────────────────────────┤
│  Layer 3: 页面样式  →  css/xxx.css      │  ← 只写该页面独有的布局和微调
└─────────────────────────────────────────┘
```

**核心原则**：通用组件只改 `components.css`，不要往页面CSS里复制粘贴。

---

## 修改优先级（AI必须遵守）

| 你要改什么 | 第一步去哪里找 | 第二步去哪里改 |
|-----------|--------------|--------------|
| 弹窗样式 | `css/components.css` → `.app-modal-*` | 不需要第二步 |
| 按钮样式 | `css/components.css` → `.app-btn-*` | 不需要第二步 |
| 卡片样式 | `css/components.css` → `.app-card-*` | 不需要第二步 |
| 导航栏样式 | `css/components.css` → `.app-nav-*` | 不需要第二步 |
| 表单输入框 | `css/components.css` → `.app-input` | 不需要第二步 |
| 颜色/圆角/阴影全局调整 | `css/tokens.css` | 不需要第二步 |
| 动效 | `css/animations.css` | 不需要第二步 |
| 某页面特有的布局 | `css/该页面.css` | — |
| 某页面特有的组件 | `css/该页面.css` | 如该组件在2+页面出现，应升级到components.css |

**禁止**：在JS字符串里拼接CSS样式。所有CSS必须在 `.css` 文件中。

---

## 命名规范

### CSS选择器
- **通用组件**：`.app-前缀`（如 `.app-btn`, `.app-card`）
- **页面特有**：用页面缩写（如 `.settings-nav`, `.hub-card`）
- **主题弹窗**：保持 `.tsm-*` 前缀（已有兼容）
- **禁止**：直接用 `.btn`、`.card`、`.modal` 等过于通用的类名（容易冲突）

### CSS变量
- 所有颜色、间距、圆角、阴影 **必须** 使用 `tokens.css` 中的变量
- 禁止硬编码 `#ffffff`、`8px`、`rgba(0,0,0,0.1)` 等值
- 常用变量速查：
  - 背景：`var(--surface-card)`, `var(--surface-hover)`, `var(--surface-glass)`
  - 文字：`var(--text-heading)`, `var(--text-body)`, `var(--text-muted)`
  - 品牌：`var(--brand-500)`（主色）, `var(--brand-600)`（hover）
  - 阴影：`var(--shadow-sm)`, `var(--shadow-md)`, `var(--shadow-lg)`
  - 圆角：`var(--radius-sm)`, `var(--radius-md)`, `var(--radius-lg)`
  - 间距：`var(--space-sm)`, `var(--space-md)`, `var(--space-lg)`

---

## 组件使用速查

### 导航栏
```html
<nav class="app-nav">
  <div class="app-nav-inner">
    <div class="app-nav-left">
      <a href="/hub.html" class="app-nav-back">...</a>
      <h1 class="app-nav-title">页面标题</h1>
    </div>
    <div class="app-nav-right">
      <button class="app-nav-btn">...</button>
    </div>
  </div>
</nav>
```

### 按钮
```html
<button class="app-btn app-btn-primary">主按钮</button>
<button class="app-btn app-btn-secondary">次按钮</button>
<button class="app-btn app-btn-ghost">幽灵按钮</button>
<button class="app-btn app-btn-danger">危险按钮</button>
<!-- 尺寸 -->
<button class="app-btn app-btn-primary app-btn-sm">小号</button>
<button class="app-btn app-btn-primary app-btn-lg">大号</button>
```

### 卡片
```html
<div class="app-card">
  <div class="app-card-header">
    <h3 class="app-card-title">标题</h3>
  </div>
  <!-- 内容 -->
  <div class="app-card-actions">
    <button class="app-btn app-btn-secondary">取消</button>
    <button class="app-btn app-btn-primary">确认</button>
  </div>
</div>
```

### 弹窗
```html
<div class="app-modal-overlay">
  <div class="app-modal">
    <div class="app-modal-header">
      <h3 class="app-modal-title">标题</h3>
      <button class="app-modal-close">&times;</button>
    </div>
    <div class="app-modal-body">内容</div>
    <div class="app-modal-footer">
      <button class="app-btn app-btn-secondary">取消</button>
      <button class="app-btn app-btn-primary">确认</button>
    </div>
  </div>
</div>
```

### 表单
```html
<label class="app-label">邮箱</label>
<input class="app-input" placeholder="请输入邮箱">
<p class="app-hint">提示文字</p>

<textarea class="app-textarea" placeholder="请输入内容"></textarea>

<select class="app-select">
  <option>选项一</option>
</select>
```

### 徽章
```html
<span class="app-badge app-badge-brand">品牌</span>
<span class="app-badge app-badge-success">成功</span>
<span class="app-badge app-badge-warning">警告</span>
<span class="app-badge app-badge-danger">危险</span>
```

---

## 美化原则（让UI更精美）

1. **统一阴影层次**：卡片用 `shadow-sm`，hover时用 `shadow-md`，弹窗用 `shadow-lg`
2. **所有交互元素必须有hover态**：颜色加深、轻微上浮、阴影增强
3. **所有按钮必须有active态**：回到原位，阴影减弱
4. **过渡动画**：所有状态变化使用 `var(--transition-base)`（0.25s ease-out）
5. **圆角一致**：小元素用 `radius-sm`(8px)，按钮用 `radius-md`(14px)，卡片用 `radius-lg`(20px)
6. **间距网格**：以8px为基准（space-sm=8px, space-md=16px, space-lg=24px）

---

## 常见问题

**Q：我想给某个页面加一个特殊按钮，该怎么做？**
A：先检查 `components.css` 里的 `.app-btn-*` 是否够用。如果样式差异很大（比如形状完全不同），在页面CSS里用 `.该页面 .特殊按钮` 命名，不要直接用 `.btn`。

**Q：我想改全局主题色？**
A：改 `css/tokens.css` 里的 `--_brand-h` / `--_brand-c` / `--_brand-l`，所有页面的品牌色会自动更新。

**Q：页面CSS和components.css冲突了？**
A：页面CSS的优先级高于components.css（因为后加载）。优先用components.css的变量，少写覆盖规则。
