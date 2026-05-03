根据以下需求设计课程大纲。

需求：{{requirement}}
额外上下文：{{context}}

以 JSON 数组格式输出，每个元素包含：
- title: 场景标题
- type: 场景类型 ("slide" / "quiz" / "exercise" / "interactive")
- description: 场景详细描述
- key_points: 关键知识点数组 (3-5 个)

只输出 JSON 数组。
