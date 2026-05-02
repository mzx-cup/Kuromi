## 课堂上下文

课程主题：{{course_title}}
当前场景：{{scene_title}}
已完成的 Agent 轮次：{{turn_history}}

## 历史对话
{{chat_history}}

## 任务
决定下一步应该由哪个 Agent 发言，输出 JSON 决策：

```json
{"next_agent": "<agent_id_or_USER_or_END>", "reason": "<简短理由>"}
```
