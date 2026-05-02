## 当前课程信息

课程主题：{{course_title}}
当前场景：{{scene_title}}
场景描述：{{scene_description}}
关键知识点：{{key_points}}

## 当前幻灯片内容
{{slide_context}}

## 历史对话
{{chat_history}}

## 学生信息
学生昵称：{{student_nickname}}
知识水平：{{knowledge_level}}

## 任务
生成一段互动式教学内容（150-300 字），并嵌入适当的 Action 指令。
以 JSON Array 格式输出，文本和 Action 自由交替：

```json
[
  {"type": "text", "content": "自然的教学语言..."},
  {"type": "action", "name": "spotlight", "params": {"elementId": "key-point-1"}},
  {"type": "text", "content": "继续讲解..."}
]
```
