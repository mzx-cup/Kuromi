生成以下大纲项的幻灯片内容。

课程主题：{{course_title}}
场景标题：{{outline_title}}
场景描述：{{outline_description}}
关键知识点：{{key_points}}

输出完整 JSON（含 title, background, theme, elements, speech, remark, image_prompt 字段）。

## 布局类型要求

为每个幻灯片选择合适的布局类型（layoutType），必须从以下19种教育布局中指定一种：

### 基础教学布局
- title-only：仅标题页面，用于章节分隔
- two-column：左右两栏布局，适合对比内容
- grid-cards：卡片网格布局，适合展示多个知识点
- header-content：顶部标题+下方内容，适合单一主题深入

### 流程/顺序类（适合步骤讲解）
- timeline-steps：时间线/步骤流程，浅色背景布局，必须使用深色文字（#1E293B），禁止白色文字
- numbered-list：数字编号列表，适合强调顺序

### 重点突出类（适合核心概念）
- hero-center：居中聚焦，大标题+副标题，适合课程引入
- fullwidth-banner：全宽横幅，适合重点强调

### 对比/分析类（适合概念比较）
- comparison：左右对比（VS布局），适合A/B对比
- asymmetric-split：不对称分割，左侧60%右侧40%

### 卡片展示类（适合知识罗列）
- three-column-cards：三列卡片，适合三个并列知识点
- chapter-divider：章节分隔页，适合大章节切换

### 教育专用布局（核心教学场景）
- edu-definition：概念定义页，左侧定义框+右侧属性标签，适合新概念首次出现时的定义讲解
- edu-keypoints：规范要点页，三栏等分卡片，每栏含彩色顶部条+要点列表，适合罗列规范、规则、注意事项
- edu-example：示例演示页，左侧概念说明+右侧示例区（代码/图解），适合展示代码示例、数学例题、案例分析
- edu-summary：章节总结页，三彩色区块横向排列，适合章节小结、知识回顾
- edu-welcome：课程欢迎导学页，"是什么-能做什么-如何学习"三段式结构，适合课程开篇
- edu-programming-concept：编程概念教学页，标题+左右分栏（定义/规范）+下方类型分类，适合编程概念教学

### 媒体展示类
- media-showcase：媒体展示页，深色背景突出图片/视频内容，适合展示生成的媒体资源

### 布局轮换要求
1. **避免连续使用相同布局**，每3-5个幻灯片应换一种布局类型
2. 根据内容性质选择最合适的布局（流程用timeline-steps，对比用comparison等）
3. 浅色背景布局（如timeline-steps、grid-cards等）的文字颜色必须使用深色（#1E293B或#334155），禁止白色文字配浅色背景
4. 深色背景布局（如media-showcase）的标题使用白色/浅色文字，内容使用白色或浅灰色
5. 当生成图片或视频时，优先使用 media-showcase 布局展示媒体内容

### 输出格式
每个幻灯片的JSON必须包含 layoutType 字段，指定所使用的布局类型。
