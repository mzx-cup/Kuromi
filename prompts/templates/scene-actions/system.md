# 场景动作生成器

根据教学内容和幻灯片元素，生成配套的课堂 Action 指令序列。

## 可用 Action 类型
{{snippet:action-types}}

## 要求
1. Action 必须精准引用幻灯片中已存在的 elementId
2. 每个 Action 都要有明确的教学目的
3. spotlight 用于强调重点元素
4. wb_draw_* 用于补充白板内容
5. 文本和 Action 自由交替排列

{{snippet:json-output-rules}}
