"""
UI Action JSON Schema 定义

对应 OpenMAIC lib/orchestration/tool-schemas.ts 的 getActionDescriptions()
这些 Action 通过 System Prompt 中的文本描述绑定，以 JSON 数组格式由 LLM 输出。
"""

UI_ACTION_SCHEMAS: dict[str, dict] = {
    "spotlight": {
        "description": "聚焦高亮某个幻灯片元素，其他区域变暗。每次最多用1-2个。",
        "params": {"elementId": "string - 目标元素ID", "dimOpacity": "number (可选) - 暗区不透明度"},
    },
    "laser": {
        "description": "激光笔指向某个元素。用于引导注意力。",
        "params": {"elementId": "string - 目标元素ID", "color": "string (可选) - 激光颜色"},
    },
    "wb_open": {
        "description": "打开白板画布。绘制前必须先调用。",
        "params": {},
    },
    "wb_draw_svg": {
        "description": (
            "在白板上绘制SVG图形。用于画流程图、坐标图、示意图、几何图形等。"
            "SVG必须规范、简洁，使用stroke而非fill为主，以便前端一笔一划播放绘制过程。"
        ),
        "params": {
            "svg": "string - 完整的SVG字符串（见下方SVG规范）",
            "x": "number - 白板上的X坐标",
            "y": "number - 白板上的Y坐标",
            "width": "number - 显示宽度",
            "height": "number - 显示高度",
            "elementId": "string (可选) - 元素ID",
        },
    },
    "wb_draw_text": {
        "description": "在白板上写文字。用于书写公式、步骤、要点。",
        "params": {
            "content": "string",
            "x": "number",
            "y": "number",
            "fontSize": "number (可选)",
            "color": "string (可选)",
        },
    },
    "wb_draw_shape": {
        "description": "在白板上绘制几何图形(rectangle/circle/triangle)。",
        "params": {
            "shape": "rectangle|circle|triangle",
            "x": "number",
            "y": "number",
            "width": "number",
            "height": "number",
            "fillColor": "string (可选)",
            "strokeColor": "string (可选)",
        },
    },
    "wb_draw_latex": {
        "description": "在白板上渲染LaTeX数学公式。务必使用正确LaTeX语法。",
        "params": {
            "latex": "string - LaTeX源码",
            "x": "number",
            "y": "number",
            "width": "number (可选)",
            "color": "string (可选)",
        },
    },
    "wb_draw_chart": {
        "description": "在白板上绘制图表(bar/line/pie/radar)。",
        "params": {
            "chartType": "bar|line|pie|radar",
            "x": "number",
            "y": "number",
            "width": "number",
            "height": "number",
            "data": "object - {labels: string[], legends: string[], series: number[][]}",
        },
    },
    "wb_draw_table": {
        "description": "在白板上绘制数据表格。第一行为表头。",
        "params": {
            "data": "string[][] - 二维数组，第一行为表头",
            "x": "number",
            "y": "number",
            "width": "number",
            "height": "number",
        },
    },
    "wb_draw_line": {
        "description": "在白板上绘制连接线/箭头。用于连接元素、关系图等。",
        "params": {
            "startX": "number",
            "startY": "number",
            "endX": "number",
            "endY": "number",
            "color": "string (可选)",
            "width": "number (可选, 默认2)",
            "style": "solid|dashed (可选)",
            "points": "['', 'arrow'] (可选, 末端箭头标记)",
        },
    },
    "wb_draw_code": {
        "description": "在白板上添加代码块(带语法高亮)。用于演示编程概念。",
        "params": {
            "language": "string - python|javascript|java|c|cpp|go|rust",
            "code": "string - 源代码(用\\n换行)",
            "x": "number",
            "y": "number",
            "width": "number (可选, 默认500)",
            "height": "number (可选, 默认300)",
            "fileName": "string (可选)",
        },
    },
    "wb_edit_code": {
        "description": "编辑白板上已有的代码块。支持 insert_after/insert_before/delete_lines/replace_lines。",
        "params": {
            "elementId": "string - 目标代码块ID",
            "operation": "insert_after|insert_before|delete_lines|replace_lines",
            "lineId": "string (可选) - 参考行ID",
            "lineIds": "string[] (可选) - 目标行ID列表",
            "content": "string (可选) - 新代码内容",
        },
    },
    "wb_clear": {
        "description": "清空白板所有元素。",
        "params": {},
    },
    "wb_delete": {
        "description": "删除白板上指定ID的元素。",
        "params": {"elementId": "string"},
    },
    "wb_close": {
        "description": "关闭白板，返回幻灯片视图。不要频繁开关白板。",
        "params": {},
    },
    "play_media": {
        "description": "播放视频/动画资源。",
        "params": {"elementId": "string"},
    },
    "speech": {
        "description": "教师旁白语音。这是主要的口头输出方式。每句≤30字。",
        "params": {"content": "string - 要说的内容(中文)"},
    },
    "text": {
        "description": "纯文本输出(无语音)。用于静默把文本显示在聊天区。",
        "params": {"content": "string"},
    },
}


# =============================================================================
# SVG 生成规范（当 wb_draw_svg 在可用动作中时注入 System Prompt）
# =============================================================================

SVG_GUIDELINES = """
# SVG 绘图规范 (CRITICAL — 当使用 wb_draw_svg 时)

## 核心原则
SVG 必须简洁、规范，使用 stroke 为主而非 fill。前端引擎会一笔一划播放绘制过程，
因此每个可视化元素都应是独立的 path/line/circle，而非一个巨大的填充块。

## 坐标空间
SVG viewBox 默认为 "0 0 400 300"。所有坐标应在此空间内。

## 必须遵守的规则
1. **使用 stroke 而非 fill**: <path stroke=\"#333\" fill=\"none\" stroke-width=\"2\"/>
2. **颜色使用**: stroke用深色(#333, #2563eb, #dc2626), fill仅用于浅色背景(rgba)
3. **箭头标记**: 如需箭头，使用 <polygon> 手动绘制，不要依赖 <marker>
4. **文字标注**: 使用 <text> 元素，font-size=\"12\" 到 \"16\"
5. **简洁优先**: 一个SVG最多10-15个图形元素，避免过度复杂
6. **禁止**: 不使用 <foreignObject>、不依赖外部CSS、不使用JS

## 常用元素示例
- 矩形: <rect x=\"10\" y=\"10\" width=\"80\" height=\"40\" stroke=\"#333\" fill=\"none\"/>
- 圆形: <circle cx=\"50\" cy=\"50\" r=\"20\" stroke=\"#2563eb\" fill=\"rgba(37,99,235,0.1)\"/>
- 线条: <line x1=\"10\" y1=\"10\" x2=\"100\" y2=\"100\" stroke=\"#333\" stroke-width=\"2\"/>
- 路径: <path d=\"M10,50 L100,50 L100,100\" stroke=\"#dc2626\" fill=\"none\"/>
- 折线箭头: <polygon points=\"95,47 100,50 95,53\" fill=\"#dc2626\"/>
- 文字: <text x=\"50\" y=\"30\" font-size=\"12\" fill=\"#333\" text-anchor=\"middle\">标签</text>

## 排版布局
- 元素间距 ≥ 20px
- 文字放在图形上方或下方 15px 处
- 线条连接图元中心点
- 所有坐标取整，避免小数

## Good Example — 简单的坐标图
<svg viewBox=\"0 0 400 300\">
  <line x1=\"40\" y1=\"260\" x2=\"380\" y2=\"260\" stroke=\"#333\" stroke-width=\"2\"/>
  <line x1=\"40\" y1=\"260\" x2=\"40\" y2=\"20\" stroke=\"#333\" stroke-width=\"2\"/>
  <polygon points=\"375,257 380,260 375,263\" fill=\"#333\"/>
  <polygon points=\"37,25 40,20 43,25\" fill=\"#333\"/>
  <text x=\"200\" y=\"290\" font-size=\"12\" fill=\"#333\" text-anchor=\"middle\">x轴</text>
  <text x=\"20\" y=\"140\" font-size=\"12\" fill=\"#333\" text-anchor=\"middle\" transform=\"rotate(-90,20,140)\">y轴</text>
  <rect x=\"80\" y=\"180\" width=\"60\" height=\"80\" stroke=\"#2563eb\" fill=\"rgba(37,99,235,0.1)\"/>
  <rect x=\"180\" y=\"120\" width=\"60\" height=\"140\" stroke=\"#dc2626\" fill=\"rgba(220,38,38,0.1)\"/>
  <text x=\"110\" y=\"275\" font-size=\"11\" fill=\"#333\" text-anchor=\"middle\">A</text>
  <text x=\"210\" y=\"275\" font-size=\"11\" fill=\"#333\" text-anchor=\"middle\">B</text>
</svg>

## Bad Example — 禁止这样做
<svg>  ← 缺少 viewBox
  <rect x=\"0\" y=\"0\" width=\"100%\" height=\"100%\" fill=\"#eee\"/>  ← 百分比坐标不行
  <path d=\"M 1.23456 7.89012 ...\" fill=\"#333\"/>  ← 填充而非描边，无法一笔一划
</svg>
"""


def get_ui_action_descriptions(allowed_actions: list[str]) -> str:
    """生成 UI 动作描述文本，嵌入 System Prompt"""
    lines = []
    for name in allowed_actions:
        if name in UI_ACTION_SCHEMAS:
            schema = UI_ACTION_SCHEMAS[name]
            params_str = ", ".join(f"{k}: {v}" for k, v in schema["params"].items())
            lines.append(f"- **{name}**: {schema['description']} 参数: {{{params_str}}}")

    result = "\n".join(lines)

    # 如果 wb_draw_svg 在可用动作中，附加 SVG 规范
    if "wb_draw_svg" in allowed_actions:
        result += "\n" + SVG_GUIDELINES

    return result
