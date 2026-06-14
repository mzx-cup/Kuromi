// js/agent-mock-fallback.js
// 后端不可用时, 注入 mock 流水线(演示不卡)
// 通过 agentBus 发出与真实后端相同格式的事件, 前端无需分支判断
(function (global) {
  const STEPS = [
    { agent: 'profiler', role: '画像分析', content: '抽取 6 维画像', delay: 300 },
    { agent: 'planner', role: '路径规划', content: '选定 4 个生成器', delay: 250 },
    { agent: 'document_generator', role: '文档生成', content: '输出 Markdown 草稿', delay: 600 },
    { agent: 'exercise_generator', role: '题库生成', content: '生成 5 道练习', delay: 500 },
    { agent: 'mindmap_generator', role: '导图生成', content: '输出 SVG 导图', delay: 400 },
    { agent: 'video_content', role: '视频内容', content: '检索 B 站片段', delay: 700 },
    { agent: 'resource_push', role: '资源推送', content: '匹配推送时机', delay: 200 },
    { agent: 'evaluator', role: '评估', content: '更新掌握度', delay: 200 },
  ];

  function runMockPipeline(orchestrator) {
    if (!global.agentBus) {
      console.error('[mock-fallback] agentBus not available, aborting mock pipeline');
      return;
    }
    orchestrator.setState('running');
    const traceId = orchestrator.traceId || ('mock-' + Date.now());
    let i = 0;

    function tick() {
      if (i >= STEPS.length) {
        global.agentBus.emit('pipeline_complete', {
          trace_id: traceId,
          status: 'mock_complete',
          assets: [],
        });
        orchestrator.setState('complete');
        return;
      }
      const s = STEPS[i++];
      // 模拟真实后端 AgentStepLog 经 agent_log_adapter 转换后的 envelope 格式
      global.agentBus.emit('agent_step', {
        type: 'response',
        from: s.agent,
        intent: s.role,
        payload: {
          status: 'success',
          output_summary: s.content,
          error_message: '',
        },
        cost_ms: s.delay,
        timestamp: Date.now(),
        trace_id: traceId,
      });
      setTimeout(tick, s.delay);
    }
    setTimeout(tick, 200);
  }

  const api = { runMockPipeline, STEPS };

  if (typeof window !== 'undefined') {
    global.agentMockFallback = api;
  }
  if (typeof module !== 'undefined' && module.exports) {
    module.exports = api;
  }
})(typeof window !== 'undefined' ? window : globalThis);
