生成以下大纲项的幻灯片内容。

课程主题：{{course_title}}
场景标题：{{outline_title}}
场景描述：{{outline_description}}
关键知识点：{{key_points}}

## 后端强制指定 (硬约束)

- 目标 layout: `{{_hint_layout}}` — **必须**在 layoutType 字段使用此值
- 目标 color theme: `{{_hint_color}}` — **必须**作为 content[].colorTheme
- 目标 design style: `{{_hint_style}}` — 写作时按此风格的视觉气质 (font 字号/语气) 调整文本密度

LLM 自由发挥的部分仅限: 文字内容 (title, bullets, narration, codeSnippet, image_prompt)。
布局、配色、结构 **严格按后端指定**。

输出完整 JSON（含 title, background, theme, elements, speech, remark, image_prompt 字段）。

## 文字内容要求

- 文本元素 content 字段必须是完整的句子或段落，不能只是关键词
- 每个文本元素 content 至少包含 50-200 个中文字符
- 使用完整的句子描述知识点，包含主谓宾结构
- 避免使用"概念：xxx"这种简短格式，改用"xxx 是一种 yyy，它的特点是..."
- 每个关键知识点需要 3-5 句话的详细解释
- 文字密度需匹配风格: dark-tech/professional 偏密, sunset-warm/ocean-glass 偏疏

## 风格气质速查 (写作时参考)

- dark-tech: 严谨、术语多、代码多
- modern: 中性、信息密度均衡
- minimal: 短句、留白多
- professional: 商务、强调数据
- ocean-glass: 轻盈、比喻多
- sunset-warm: 友好、举例多
- forest-green: 自然、叙述化
- midnight-violet: 思辨、引用多

## 布局坐标参考 (按 layout 调整)

- title-only: 全屏大标题
- two-column: 左右 50/50
- grid-cards: 2x2 或 3x2 网格
- header-content: 顶部标题 + 下方内容
- edu-welcome: "是什么-能做什么-如何学习" 三段式
- edu-definition: 左侧定义框 + 右侧属性标签
- edu-example: 左侧概念 + 右侧示例
- edu-summary: 三色块横向排列
- edu-programming-concept: 标题 + 左右分栏 (定义/规范) + 下方分类

## 文字颜色规范

- 深色风格 (dark-tech, midnight-violet): 标题白, 正文浅灰
- 浅色风格 (modern, minimal, professional, ocean-glass, sunset-warm, forest-green): 标题深色 (#1E293B), 正文 #334155
- 强调色: 使用后端指定 colorTheme 对应色 (blue=#3B82F6, yellow=#F59E0B 等)

## 布局轮换要求

1. **避免连续使用相同布局**，每3-5个幻灯片应换一种布局类型
2. 根据内容性质选择最合适的布局 (流程用 timeline-steps/stair-step, 对比用 comparison/gradient-split)
3. 当生成图片或视频时，优先使用 media-showcase 布局展示媒体内容

## 输出格式

每个幻灯片的 JSON 必须包含 layoutType 字段, **取值为 `{{_hint_layout}}`**。
