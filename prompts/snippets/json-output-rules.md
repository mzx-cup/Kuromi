## JSON 输出规范

1. **只输出 JSON，不要添加任何其他文字**（不要有 markdown 代码块标记，不要有解释说明）
2. 输出格式为 JSON Array：`[{...}, {...}, ...]`
3. 每个数组元素是以下两种类型之一：
   - Text 对象：`{"type": "text", "content": "自然语言教学文本"}`
   - Action 对象：`{"type": "action", "name": "action_name", "params": {...}}`
4. Text 和 Action 对象可以自由交替排列
5. 所有 JSON 必须是合法的、可被 JSON.parse 解析的格式
6. 字符串中的双引号必须转义为 `\"`
7. 数组末尾不要有多余逗号
