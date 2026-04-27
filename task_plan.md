# 全息知识生态 UI 重设计 + 智能过滤计划

## Context

用户反馈全息知识生态存在以下问题：
1. **节点是硬编码的** - 不管学生是否在学这门课都会显示
2. **没有根据学习数据过滤** - 不是学生要学的课或还没学的课都显示"遗忘"
3. 需要调用数据库中学生的学习记录来分析，只显示**真正需要复习**的知识点

设计目标：
- 根据用户学习记录动态生成知识节点
- 只显示学生正在学/学过的课程
- 基于 SM2 复习数据计算遗忘度

---

## Phase 1: 数据层改造

### 1.1 新增字段到 knowledge_nodes

```sql
ALTER TABLE knowledge_nodes ADD COLUMN subject VARCHAR(100) DEFAULT '';
ALTER TABLE knowledge_nodes ADD COLUMN is_active BOOLEAN DEFAULT FALSE;
ALTER TABLE knowledge_nodes ADD COLUMN first_studied_at TIMESTAMP NULL;
ALTER TABLE knowledge_nodes ADD COLUMN last_studied_at TIMESTAMP NULL;
```

### 1.2 知识节点来源 - 评估驱动

用户完成能力评估后，系统根据评估结果中的：
- 强项/弱项领域
- 推荐的课程
- difficulty_level

自动激活对应的知识节点

```python
def activate_nodes_from_assessment(user_id, assessment_result):
    """根据评估结果激活知识节点"""
    strong_areas = assessment_result.get('strong_areas', [])
    weak_areas = assessment_result.get('weak_areas', [])
    recommended_courses = assessment_result.get('recommended_courses', [])

    # 激活相关领域的所有节点
    areas = set(strong_areas + weak_areas + recommended_courses)
    for area in areas:
        activate_nodes_by_subject(area)
```

### 1.3 预设知识领域模板

```python
KNOWLEDGE_TEMPLATES = {
    "计算机科学": {
        "python-core": {"name": "Python核心", "icon": "🐍", "children": ["math", "web-dev", "database", "english"]},
        "math": {"name": "数学基础", "icon": "📐"},
        "web-dev": {"name": "Web开发", "icon": "🌐"},
        "database": {"name": "数据库", "icon": "🗄️"},
        "english": {"name": "专业英语", "icon": "📚"}
    },
    "大数据": {...},
    "人工智能": {...}
}
```

### 1.4 获取激活节点 API

```python
# GET /api/knowledge/nodes/{user_id}?active=true
def get_active_knowledge_nodes(user_id):
    """只返回学生正在学习的知识节点"""
    # 1. 获取用户学习记录
    learning_record = get_learning_record(user_id)
    # 2. 获取评估结果中的课程信息
    profile = json.loads(learning_record.get('profile_json', '{}'))
    studied_subjects = profile.get('subjects', [])

    # 3. 获取用户的知识节点
    all_nodes = get_knowledge_nodes(user_id)

    # 4. 过滤：只保留激活的且属于已学课程的节点
    active_nodes = [n for n in all_nodes if n.get('is_active') and n.get('subject') in studied_subjects]

    return active_nodes
```

---

## Phase 2: 节点状态计算逻辑

### 2.1 状态判定规则

| 状态 | 条件 | 颜色 | 显示 |
|------|------|------|------|
| `not-started` | `first_studied_at == NULL` | 灰色 | "未开始" |
| `in-progress` | `repetitions == 0 && first_studied_at != NULL` | 蓝色 | "学习中" |
| `healthy` | `综合评分 >= 70` | 绿色 | "掌握良好" |
| `warning` | `40 <= 综合评分 < 70` | 橙色 | "需复习" |
| `danger` | `综合评分 < 40 或 已过复习时间` | 红色 | "濒临遗忘" |

### 2.2 状态计算流程图

```
获取节点数据
    ↓
first_studied_at == NULL? → 是 → "未开始" (灰色，不提醒)
    ↓ 否
repetitions == 0? → 是 → "学习中" (蓝色，呼吸动画)
    ↓ 否
检查 next_review 是否过期 → 过期 → "濒临遗忘" (红色，抖动)
    ↓ 否
计算综合评分 → >=70 → "掌握良好"
    ↓ <70
    → >=40 → "需复习"
    ↓ <40
    → "濒临遗忘"
```

### 2.3 JavaScript 状态计算实现

```javascript
function getNodeDynamicStatus(nodeData) {
    const sm2 = nodeData.sm2_data || {};
    const stats = nodeData.stats || {};

    // 未开始学习
    if (!nodeData.first_studied_at && !sm2.repetitions) {
        return 'not-started';
    }

    // 开始学习但无复习记录
    if (sm2.repetitions === 0) {
        return 'in-progress';
    }

    // 检查是否过期
    const nextReview = new Date(sm2.next_review);
    if (nextReview < new Date()) {
        return 'danger';
    }

    // 计算综合评分
    const score = calculateComprehensiveScore(nodeData);
    if (score >= 70) return 'healthy';
    if (score >= 40) return 'warning';
    return 'danger';
}
```

---

## Phase 3: UI 改造

### 3.1 节点状态样式扩展

```css
/* 未开始 - 灰色，无动画 */
.holo-node.not-started .node-sphere {
    background: radial-gradient(circle at 30% 30%, #f3f4f6, #d1d5db);
    border: 2px solid #9CA3AF;
    box-shadow: none;
}
.holo-node.not-started .node-icon { opacity: 0.5; }

/* 学习中 - 蓝色，呼吸动画 */
.holo-node.in-progress .node-sphere {
    background: radial-gradient(circle at 30% 30%, #dbeafe, #93c5fd);
    border: 2px solid #3B82F6;
    box-shadow: 0 0 15px rgba(59, 130, 246, 0.3);
    animation: breathe 2s ease-in-out infinite;
}

@keyframes breathe {
    0%, 100% { box-shadow: 0 0 15px rgba(59, 130, 246, 0.3); }
    50% { box-shadow: 0 0 25px rgba(59, 130, 246, 0.5); }
}
```

### 3.2 节点悬停信息 (Tooltip)

Hover 时显示浮动信息卡：
```
┌─────────────────────────┐
│ 📐 数学基础              │
│ ─────────────────────── │
│ 状态: 需复习             │
│ 正确率: 75%             │
│ 下次复习: 明天            │
│ 复习次数: 5             │
└─────────────────────────┘
```

### 3.3 节点点击行为

| 状态 | 点击行为 |
|------|----------|
| `not-started` | 模态框"开始学习？" + 跳转到对应课程 |
| `in-progress` | 引导完成首次复习 |
| `healthy/warning/danger` | 复习面板 |

### 3.4 空状态 - 混合模式

**情况A: 无学习记录**
```
┌────────────────────────────────────────────┐
│                                            │
│    🌟 欢迎来到全息知识生态                  │
│                                            │
│    还没有你的学习记录                       │
│                                            │
│    [完成能力评估]  →  系统为你生成知识图谱   │
│    [选择学习领域]  →  自主选择要学的领域      │
│                                            │
└────────────────────────────────────────────┘
```

**情况B: 有学习记录但无激活节点**
```
┌────────────────────────────────────────────┐
│                                            │
│    📚 知识图谱待生成                        │
│                                            │
│    根据你的评估结果，系统将为你规划学习路径   │
│                                            │
│    [查看评估结果]    [重新评估]             │
│                                            │
└────────────────────────────────────────────┘
```

### 3.5 连接线样式

根据子节点状态动态变化：
- 子节点全 healthy → 连接线绿色
- 任一子节点 warning → 连接线橙色
- 任一子节点 danger → 连接线红色

---

## Phase 4: 每日路线整合

### 4.1 复习任务生成逻辑

```python
def generate_review_tasks(user_id):
    # 1. 获取用户学习记录，确定学生正在学习的课程
    learning_record = get_learning_record(user_id)
    profile = json.loads(learning_record.get('profile_json', '{}'))
    active_subjects = profile.get('subjects', [])

    # 2. 获取所有到期的知识节点
    pending = get_pending_reviews(user_id)

    # 3. 过滤：只包含学生正在学习的课程
    active_pending = [
        p for p in pending
        if get_node_subject(p['node_id']) in active_subjects
    ]

    # 4. 按紧急程度排序（已过期 > 24小时内 > 3天内）
    active_pending.sort(key=lambda x: x['next_review'])

    # 5. 转换为每日路线任务格式
    return [create_review_task(p) for p in active_pending]
```

### 4.2 复习任务格式

```javascript
{
    id: 'review-math-001',
    title: '复习: 数学基础',
    description: '距离上次复习已过去5天',
    type: 'review',
    subject: '数学基础',
    node_id: 'math',
    priority: 'high', // high/medium/low
    duration: 15,     // 分钟
    taskUrl: `/review/${node_id}`
}
```

### 4.3 复习提醒整合

当生成每日路线时：
- 优先插入到期的复习任务
- 在路线卡片中显示为"复习任务"类型
- 完成复习后自动更新节点状态

---

## Critical Files

| 文件 | 修改内容 |
|------|----------|
| `db.py` | 新增 `activate_nodes_from_assessment()`, `get_active_knowledge_nodes()`, 新增字段 |
| `main.py` | `GET /api/knowledge/nodes/{user_id}?active=true` 只返回激活节点 |
| `js/hub.js` | 动态加载、状态计算、空状态处理、tooltip |
| `css/hub.css` | 新增 `.not-started`, `.in-progress` 样式，tooltip 样式 |
| `html/hub.html` | 空状态模板，tooltip 结构 |
| `setup_database.py` | 新增字段 SQL |

---

## Implementation Order

1. **db.py** - 新增字段和过滤函数
2. **setup_database.py** - 更新建表SQL
3. **main.py** - 新增 `active` 参数的API
4. **js/hub.js** - 状态计算逻辑 + 空状态
5. **css/hub.css** - 新状态样式
6. **html/hub.html** - 空状态模板

---

## Verification

1. **空状态测试**: 新用户（无学习记录）→ 显示引导界面
2. **节点过滤测试**: 有学习记录但未评估 → 只显示部分节点
3. **状态显示测试**: 不同状态的节点颜色/动画正确
4. **复习流程测试**: 点击节点 → 复习面板 → 提交 → 状态更新
5. **每日路线测试**: 复习任务正确插入路线
6. **主题测试**: 浅色/深色主题下样式正确
