生成以下大纲项的幻灯片内容。

课程主题：{{course_title}}
场景标题：{{outline_title}}
场景描述：{{outline_description}}
关键知识点：{{key_points}}

输出完整 JSON（含 title, background, theme, elements, speech, remark, image_prompt 字段）。

## 布局类型要求

为每个幻灯片选择合适的布局类型（layoutType），必须从以下28种布局中指定一种：

### 常用布局（频繁使用）
- two-column：左右两栏布局，适合对比内容
- grid-cards：卡片网格布局，适合展示多个知识点
- header-content：顶部标题+下方内容，适合单一主题深入

### 时间/步骤类（适合流程讲解）
- timeline-steps：时间线/步骤流程，**浅色背景布局，必须使用深色文字（#1E293B），禁止白色文字**
- process-flow：横向流程图，适合展示步骤
- numbered-list：数字编号列表，适合强调顺序

### 重点突出类（适合核心概念）
- hero-center：居中聚焦，大标题+副标题，适合课程引入
- center-focus：中心强调，大字+小卡片，适合核心概念
- quote-highlight：引用高亮，适合名人名言或金句

### 对比/分析类（适合概念比较）
- comparison：左右对比（VS布局），适合A/B对比
- asymmetric-split：不对称分割，左侧60%右侧40%

### 卡片展示类（适合知识罗列）
- three-column-cards：三列卡片，适合三个并列知识点
- grid-icon：图标网格，适合展示多个特征
- icon-vertical-stack：图标纵向堆叠，适合列表展示
- bottom-cards：底部卡片，适合结论汇总
- floating-overlap：浮动叠加，适合创意展示

### 多媒体类（适合图文结合）
- media-left：左侧媒体+右侧内容，适合图片说明
- stats-row：数据统计行，适合数字展示

### 特殊风格类（谨慎使用）
- fullwidth-banner：全宽横幅，适合分隔页面
- left-sidebar：左侧边栏，适合目录导航
- quote-wall：引用墙，适合多个引用
- info-graphic：信息图表，适合数据可视化
- tabbed-content：标签页内容，适合多选项
- dark-header：深色标题栏，适合重点强调，标题使用白色文字
- gradient-split：渐变分割，适合创意展示
- circle-radial：圆形辐射，适合中心发散
- stair-step：阶梯步骤，适合递进展示
- minimal-center：极简居中，适合概念澄清
- horizontal-scroll：横向滚动，适合长内容

### 布局轮换要求
1. **避免连续使用相同布局**，每3-5个幻灯片应换一种布局类型
2. 根据内容性质选择最合适的布局（流程用timeline-steps，对比用comparison等）
3. 浅色背景布局（如timeline-steps、grid-cards等）的文字颜色必须使用深色（#1E293B或#334155），禁止白色文字配浅色背景
4. 深色背景布局（如hero-center、dark-header）的标题使用白色/浅色文字，内容使用白色或浅灰色

### 输出格式
每个幻灯片的JSON必须包含 layoutType 字段，指定所使用的布局类型。
