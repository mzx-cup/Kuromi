## 可用 Action 类型

### 视觉指示
- `spotlight` — 高亮幻灯片元素，params: {elementId: string}
- `laser` — 激光指示坐标，params: {x: number, y: number}

### 白板操作
- `wb_open` — 打开白板
- `wb_close` — 关闭白板
- `wb_draw_text` — 在白板写字，params: {text: string, x: number, y: number, style?: object}
- `wb_draw_shape` — 画形状，params: {shape: string, x: number, y: number, w: number, h: number, style?: object}
- `wb_draw_chart` — 画图表，params: {chartType: string, data: object, x: number, y: number}
- `wb_draw_latex` — 写 LaTeX 公式，params: {latex: string, x: number, y: number}
- `wb_draw_table` — 画表格，params: {headers: string[], rows: string[][], x: number, y: number}
- `wb_draw_code` — 写代码，params: {code: string, lang: string, x: number, y: number}
- `wb_draw_line` — 画线，params: {x1: number, y1: number, x2: number, y2: number, style?: object}
- `wb_clear` — 清空白板
- `wb_delete` — 删除白板元素，params: {elementId: string}

### 课堂交互
- `discussion` — 发起圆桌讨论，params: {topic: string, participants: string[]}
- `quiz_show` — 显示测验，params: {quizData: object}
- `quiz_grade` — 批改测验，params: {answers: object}
- `code_run` — 运行代码，params: {code: string, lang: string}

### 媒体控制
- `play_video` — 播放视频，params: {url: string}
- `speech` — 触发 TTS 朗读，params: {text?: string}

### 幻灯片导航
- `slide_next` — 下一页幻灯片
- `slide_prev` — 上一页幻灯片
- `scene_jump` — 跳转到指定场景，params: {sceneIndex: number}

### 输出格式
每个 Action 对象格式：`{"type": "action", "name": "<action_name>", "params": {...}}`
文本对象格式：`{"type": "text", "content": "<自然语言内容>"}`
