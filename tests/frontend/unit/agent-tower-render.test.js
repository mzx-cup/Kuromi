/**
 * agent-tower — 新 renderTowerFlow / loadAgentCatalog / agentBus 订阅
 * 单元测试 (Task 20 / 21 / 22)
 *
 * 测试范围:
 *   1. loadAgentCatalog fetch 成功 -> 缓存到 agentCatalog
 *   2. loadAgentCatalog fetch 失败 -> 回落最小目录
 *   3. renderTowerFlow 把 agents 写到 #tower-flow, 每个节点带 data-agent 属性
 *   4. agentBus.subscribe('agent_step') 触发后, towerAgentStatus 跟着更新并重渲
 *   5. renderTowerLog 写入 #tower-terminal, 自动转义 XSS (Task 21)
 *   6. renderTowerLog 累计超过 TOWER_LOG_MAX 时丢掉最旧行 (Task 21)
 *   7. clearTowerTerminal 清空 #tower-terminal 和 towerLogs 数组 (Task 21)
 *   8. agent_step 事件 -> renderTowerLog 写入 + 状态类切换 (Task 21)
 *   9. computeRadarPoints 从 snapshot 提取 6 维分数并限制到 0-100 (Task 22)
 *  10. computeRadarPoints snapshot 为 null 时回退到零值 + hasData=false (Task 22)
 *  11. computeRadarPoints 越界值被 clamp 到 [0, 100] (Task 22)
 *  12. radarColorWithAlpha 把 #3b82f6 转为 rgba(59,130,246,0.5) (Task 22)
 *  13. profile_updated 事件触发 renderRadarFromSnapshot + towerRadarSnapshot 更新 (Task 22)
 *  (4 卡画像面板 Task 23 已删除, 与 8 tile 语义重复, 由 Task #48 8 tile 实时更新承载)
 *
 * 实现说明:
 *   js/index.js 是一个 10000+ 行的顶层脚本, 不导出符号。
 *   为了在不破坏该脚本的前提下测试新增的塔函数, 本测试在 jsdom 中:
 *     - 加载 agent-bus.js (IIFE 挂在 window.agentBus)
 *     - 从 js/index.js 源码中按标记段截取 "Agent 编排控制塔" 区块
 *     - 在隔离 sandbox (Function 构造器) 中 eval 该区块, 暴露内部函数
 *     - 通过 sandbox 暴露的 init / render / reset 接口做断言
 *
 * 运行: npx vitest run tests/frontend/unit/agent-tower-render.test.js
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import fs from 'fs';
import path from 'path';

const INDEX_JS = fs.readFileSync(
  path.resolve(__dirname, '../../../js/index.js'),
  'utf8',
);

/**
 * 从 index.js 源码里截取 "Agent 编排控制塔" 区块.
 * 区块开始:  "// === Agent 编排控制塔 — 新数据源 (Task 20) ==="
 * 区块结束:  "// 旧 renderFlowNodes() 仍保留并指向隐藏的 #flow-node-container,"
 *            这条注释 *之前* 的最后一个声明 — 简单起见, 我们取到
 *            "initAgentTower();" 调用之后第一个空行, 即整个 init 块也包含进来。
 */
function extractTowerBlock(src) {
  const start = src.indexOf('// === Agent 编排控制塔 — 新数据源');
  if (start === -1) throw new Error('tower block marker not found in index.js');
  // 找区块结束的最后一个函数声明 — 我们用 "function renderSandboxLog" 作为下界 (不含)
  // 但 sandbox 后续还会用到 AGENT_LABELS / escapeHtml, 所以也一起包进来
  const endNeedle = 'function renderSandboxLog';
  const end = src.indexOf(endNeedle, start);
  if (end === -1) throw new Error('renderSandboxLog marker not found');
  return src.slice(start, end);
}

/**
 * 在 sandbox 中执行塔区块, 暴露需要的标识符.
 * sandbox 继承 window, 但所有顶层 const/let/function 都在自身作用域内, 不会污染测试.
 */
function loadTowerSandbox({ fetchImpl, documentHtml } = {}) {
  // 准备 DOM (只在调用方传 documentHtml 时才覆盖, 默认沿用 beforeEach 设置的)
  if (documentHtml !== undefined) {
    document.body.innerHTML = documentHtml;
  }

  // 抓出塔区段 + 必要的依赖 (escapeHtml + AGENT_LABELS)
  const towerBlock = extractTowerBlock(INDEX_JS);
  // 抓出 escapeHtml (从它的定义点到 AGENT_COLORS 之前 — 避免重复声明)
  const escapeStart = INDEX_JS.indexOf('function escapeHtml(text)');
  const escapeEnd = INDEX_JS.indexOf('const AGENT_COLORS', escapeStart);
  const deps = INDEX_JS.slice(escapeStart, escapeEnd);

  const sbFetch = fetchImpl || (() => Promise.resolve({
    ok: true,
    status: 200,
    json: () => Promise.resolve({ agents: [], pipeline: [] }),
  }));

  // 用 Function 构造器隔离沙箱, 注入 window/document/fetch, 末尾 return 我们需要的接口
  const factorySrc = `
    "use strict";
    var fetch = arguments[0].fetchImpl;
    var window = arguments[0].win;
    var document = arguments[0].doc;
    ${deps}
    ${towerBlock}
    return {
      loadAgentCatalog, renderTowerFlow, resetTowerStatus,
      renderTowerLog, clearTowerTerminal,
      initAgentTower, subscribeToAgentBus,
      // Task 22: radar snapshot + pure geometry helpers
      computeRadarPoints, radarColorWithAlpha, renderRadarFromSnapshot,
      RADAR_DIMENSIONS,
      // Task #49: 控制塔 start/pause/stop 交互
      startPipeline, pausePipeline, stopPipeline, finishPipeline,
      wireTowerControlButtons, runMockPipeline, _parseSseEnvelope,
      __state: {
        get agentCatalog() { return agentCatalog; },
        get towerAgentStatus() { return towerAgentStatus; },
        get towerLogs() { return towerLogs; },
        get TOWER_LOG_MAX() { return TOWER_LOG_MAX; },
        get _towerCatalogLoaded() { return towerCatalogLoaded; },
        get _towerBusSubscribed() { return _towerBusSubscribed; },
        get _towerInitialized() { return _towerInitialized; },
        get towerRadarSnapshot() { return towerRadarSnapshot; },
        get towerPipelineRunning() { return towerPipelineRunning; },
        get towerPaused() { return towerPaused; },
        get towerSseAbort() { return towerSseAbort; },
        get TOWER_MOCK_STEPS() { return TOWER_MOCK_STEPS; },
        set agentCatalog(v) { agentCatalog = v; },
        set towerAgentStatus(v) { towerAgentStatus = v; },
        set towerLogs(v) { towerLogs = v; },
        set _towerCatalogLoaded(v) { towerCatalogLoaded = v; },
        set _towerBusSubscribed(v) { _towerBusSubscribed = v; },
        set _towerInitialized(v) { _towerInitialized = v; },
        set towerRadarSnapshot(v) { towerRadarSnapshot = v; },
        set towerPipelineRunning(v) { towerPipelineRunning = v; },
        set towerPaused(v) { towerPaused = v; },
      },
    };
  `;

  // eslint-disable-next-line no-new-func
  const factory = new Function(factorySrc);
  return factory({ fetchImpl: sbFetch, win: window, doc: document });
}

describe('agent-tower — 新数据源渲染', () => {
  beforeEach(async () => {
    document.body.innerHTML = '<div class="tower-flow" id="tower-flow"></div>'
      + '<div class="tower-terminal" id="tower-terminal"></div>';
    // 加载 agent-bus 干净实例
    delete window.agentBus;
    vi.resetModules();
    await import('../../../js/agent-bus.js');
  });

  afterEach(() => {
    vi.restoreAllMocks();
    // 清空 agentBus 上累积的订阅, 避免测试间互相污染
    if (window.agentBus && typeof window.agentBus.clear === 'function') {
      window.agentBus.clear();
    }
  });

  it('loadAgentCatalog fetch 成功 -> 缓存到 agentCatalog', async () => {
    const fakeCatalog = {
      agents: [
        { id: 'profiler', name: '画像分析', stage: 'main' },
        { id: 'planner', name: '路径规划', stage: 'main' },
      ],
      pipeline: [
        { stage: 'main', agents: ['profiler', 'planner'] },
      ],
    };
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true, status: 200, json: () => Promise.resolve(fakeCatalog),
    });
    const sb = loadTowerSandbox({ fetchImpl: fetchMock });
    const result = await sb.loadAgentCatalog();
    expect(result).toEqual(fakeCatalog);
    expect(sb.__state._towerCatalogLoaded).toBe(true);
    expect(fetchMock).toHaveBeenCalledWith('/api/agents/catalog');
  });

  it('loadAgentCatalog fetch 失败 -> 回落最小目录 (不抛错)', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: false, status: 500, json: () => Promise.resolve({}),
    });
    const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});
    const sb = loadTowerSandbox({ fetchImpl: fetchMock });
    const result = await sb.loadAgentCatalog();
    expect(result.agents).toBeTruthy();
    expect(result.agents.length).toBeGreaterThan(0);
    expect(result.pipeline.length).toBeGreaterThan(0);
    expect(sb.__state._towerCatalogLoaded).toBe(true);
    // 关键 fallback 节点必须存在
    const ids = result.agents.map(a => a.id);
    expect(ids).toContain('profiler');
    expect(ids).toContain('document_generator');
    expect(ids).toContain('evaluator');
    warnSpy.mockRestore();
  });

  it('renderTowerFlow 写入 #tower-flow, 节点带 data-agent 属性', async () => {
    const fakeCatalog = {
      agents: [
        { id: 'echo', name: '问候', stage: 'pre' },
        { id: 'profiler', name: '画像分析', stage: 'main' },
        { id: 'planner', name: '路径规划', stage: 'main' },
        { id: 'document_generator', name: '文档生成', stage: 'parallel' },
        { id: 'evaluator', name: '评估', stage: 'post' },
      ],
      pipeline: [
        { stage: 'pre', agents: ['echo'] },
        { stage: 'main', agents: ['profiler', 'planner'] },
        { stage: 'parallel', agents: ['document_generator'] },
        { stage: 'post', agents: ['evaluator'] },
      ],
    };
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true, status: 200, json: () => Promise.resolve(fakeCatalog),
    });
    const sb = loadTowerSandbox({ fetchImpl: fetchMock });
    await sb.loadAgentCatalog();
    sb.renderTowerFlow();

    const container = document.getElementById('tower-flow');
    const nodes = container.querySelectorAll('.flow-node');
    expect(nodes.length).toBe(5);
    const ids = Array.from(nodes).map(n => n.getAttribute('data-agent'));
    expect(ids).toEqual(['echo', 'profiler', 'planner', 'document_generator', 'evaluator']);
    // 全部初始为 idle — 不带 is-* 类
    for (const n of nodes) {
      expect(n.classList.contains('is-busy')).toBe(false);
      expect(n.classList.contains('is-success')).toBe(false);
      expect(n.classList.contains('is-failed')).toBe(false);
    }
  });

  it('agent_step 事件 -> towerAgentStatus 更新 + 重渲 (is-busy / is-success 状态切换)', async () => {
    const fakeCatalog = {
      agents: [
        { id: 'profiler', name: '画像分析', stage: 'main' },
        { id: 'planner', name: '路径规划', stage: 'main' },
      ],
      pipeline: [{ stage: 'main', agents: ['profiler', 'planner'] }],
    };
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true, status: 200, json: () => Promise.resolve(fakeCatalog),
    });
    const sb = loadTowerSandbox({ fetchImpl: fetchMock });
    await sb.loadAgentCatalog();
    sb.renderTowerFlow();
    // 模拟 initAgentTower 后半段: 订阅
    sb.__state._towerBusSubscribed = false;  // 重置幂等旗
    sb.subscribeToAgentBus();
    expect(sb.__state._towerBusSubscribed).toBe(true);

    // emit agent_step with status=success for profiler
    window.agentBus.emit('agent_step', {
      from: 'profiler',
      intent: '画像分析',
      payload: { status: 'success', output_summary: '...', error_message: '' },
      cost_ms: 100,
      timestamp: Date.now(),
      trace_id: 't1',
    });
    expect(sb.__state.towerAgentStatus.profiler).toBe('success');

    // 校验 DOM 重渲
    const container = document.getElementById('tower-flow');
    const profilerNode = container.querySelector('[data-agent="profiler"]');
    expect(profilerNode.classList.contains('is-success')).toBe(true);
    expect(profilerNode.classList.contains('is-busy')).toBe(false);

    // 再 emit 一条 failed
    window.agentBus.emit('agent_step', {
      from: 'planner',
      intent: '路径规划',
      payload: { status: 'failed', error_message: 'boom' },
    });
    expect(sb.__state.towerAgentStatus.planner).toBe('failed');
    const plannerNode = container.querySelector('[data-agent="planner"]');
    expect(plannerNode.classList.contains('is-failed')).toBe(true);

    // emit 一条 unknown status -> busy
    window.agentBus.emit('agent_step', {
      from: 'planner',
      intent: '路径规划',
      payload: { status: 'pending' },
    });
    expect(sb.__state.towerAgentStatus.planner).toBe('busy');
    const plannerNode2 = container.querySelector('[data-agent="planner"]');
    expect(plannerNode2.classList.contains('is-busy')).toBe(true);
  });

  // === Task 21: renderTowerLog / clearTowerTerminal / 双数据源之新管线 ===
  it('renderTowerLog 写入 #tower-terminal, 自动转义 XSS', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true, status: 200, json: () => Promise.resolve({ agents: [], pipeline: [] }),
    });
    const sb = loadTowerSandbox({ fetchImpl: fetchMock });
    // 故意注入一段恶意 payload
    sb.renderTowerLog({
      from: '<script>',
      intent: 'evil<>',
      payload: { status: 'success', output_summary: 'evil<>&"\'' },
      timestamp: Date.now(),
    });

    const container = document.getElementById('tower-terminal');
    const lines = container.querySelectorAll('.tower-log-line');
    expect(lines.length).toBe(1);
    const html = lines[0].innerHTML;
    // agent id / intent / content 都应被转义, 不会有可执行 <script>
    expect(html).toContain('&lt;script&gt;');
    expect(html).toContain('evil&lt;&gt;');
    expect(html).toContain('&amp;');
    // 容器内确实没有 script 节点 (浏览器在 innerHTML 时会丢弃)
    expect(container.querySelector('script')).toBeNull();
    // data-agent 也应是 raw, 方便后续 selector
    expect(lines[0].getAttribute('data-agent')).toBe('<script>');
  });

  it('renderTowerLog 累计超过 TOWER_LOG_MAX 时丢掉最旧行', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true, status: 200, json: () => Promise.resolve({ agents: [], pipeline: [] }),
    });
    const sb = loadTowerSandbox({ fetchImpl: fetchMock });
    const max = sb.__state.TOWER_LOG_MAX;
    expect(max).toBe(200);
    // 推 max+1 条
    const total = max + 1;
    for (let i = 0; i < total; i++) {
      sb.renderTowerLog({
        from: 'profiler',
        intent: 'step-' + i,
        payload: { status: 'success', output_summary: 'msg-' + i },
        timestamp: Date.now() + i,
      });
    }
    const container = document.getElementById('tower-terminal');
    const lines = container.querySelectorAll('.tower-log-line');
    // DOM 中只剩 max 行
    expect(lines.length).toBe(max);
    // 内存中也只剩 max 行
    expect(sb.__state.towerLogs.length).toBe(max);
    // 最旧的 (msg-0) 应被丢掉, 最新的 (msg-max) 仍在
    expect(container.innerHTML).not.toContain('msg-0');
    expect(container.innerHTML).toContain('msg-' + max);
  });

  it('clearTowerTerminal 清空 #tower-terminal 和 towerLogs 数组', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true, status: 200, json: () => Promise.resolve({ agents: [], pipeline: [] }),
    });
    const sb = loadTowerSandbox({ fetchImpl: fetchMock });
    for (let i = 0; i < 3; i++) {
      sb.renderTowerLog({
        from: 'profiler',
        intent: 'step',
        payload: { status: 'success', output_summary: 'line ' + i },
        timestamp: Date.now(),
      });
    }
    expect(sb.__state.towerLogs.length).toBe(3);
    sb.clearTowerTerminal();
    expect(sb.__state.towerLogs.length).toBe(0);
    const container = document.getElementById('tower-terminal');
    expect(container.querySelectorAll('.tower-log-line').length).toBe(0);
    expect(container.innerHTML).toBe('');
  });

  it('agent_step 事件 -> renderTowerLog 写入 + 状态类切换', async () => {
    const fakeCatalog = {
      agents: [{ id: 'profiler', name: '画像分析', stage: 'main' }],
      pipeline: [{ stage: 'main', agents: ['profiler'] }],
    };
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true, status: 200, json: () => Promise.resolve(fakeCatalog),
    });
    const sb = loadTowerSandbox({ fetchImpl: fetchMock });
    await sb.loadAgentCatalog();
    sb.renderTowerFlow();
    sb.__state._towerBusSubscribed = false;
    // 先清空可能从前面测试残留的订阅
    if (window.agentBus && typeof window.agentBus.clear === 'function') {
      window.agentBus.clear();
    }
    sb.subscribeToAgentBus();
    const container = document.getElementById('tower-terminal');
    // 启动前清空 (排除 idle 初始行)
    container.innerHTML = '';
    sb.__state.towerLogs.length = 0;

    // success -> 普通行, 不带 tower-log-err
    window.agentBus.emit('agent_step', {
      from: 'profiler',
      intent: '画像分析',
      payload: { status: 'success', output_summary: '画像完成' },
      timestamp: Date.now(),
      trace_id: 't1',
    });
    let lines = container.querySelectorAll('.tower-log-line');
    expect(lines.length).toBe(1);
    expect(lines[0].classList.contains('tower-log-err')).toBe(false);
    expect(lines[0].dataset.agent).toBe('profiler');
    expect(lines[0].innerHTML).toContain('画像完成');

    // failed -> 带 tower-log-err
    window.agentBus.emit('agent_step', {
      from: 'profiler',
      intent: '画像分析',
      payload: { status: 'failed', error_message: 'boom' },
      timestamp: Date.now(),
      trace_id: 't1',
    });
    lines = container.querySelectorAll('.tower-log-line');
    expect(lines.length).toBe(2);
    expect(lines[1].classList.contains('tower-log-err')).toBe(true);
    expect(lines[1].innerHTML).toContain('boom');

    // fatal error 走 error 事件 -> 合成一条 error 行
    window.agentBus.emit('error', { agent: 'profiler', fatal: true, message: 'pipeline crashed' });
    lines = container.querySelectorAll('.tower-log-line');
    expect(lines.length).toBe(3);
    expect(lines[2].classList.contains('tower-log-err')).toBe(true);
    expect(lines[2].innerHTML).toContain('pipeline crashed');
  });

  // === Task 22: 雷达图 LearningPortrait 6 维 + 新 CSS 渐变 ===
  it('computeRadarPoints 从 snapshot 提取 6 维分数并限制到 0-100', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true, status: 200, json: () => Promise.resolve({ agents: [], pipeline: [] }),
    });
    const sb = loadTowerSandbox({ fetchImpl: fetchMock });
    const snapshot = {
      radar: {
        knowledge_mastery: 75,
        code_skill: 60,
        cognitive_style: 80,
        learning_goal: 50,
        weakness: 30,
        focus_level: 90,
      },
    };
    const geom = sb.computeRadarPoints(snapshot, { cx: 120, cy: 120, R: 60 });
    expect(geom.values).toEqual([75, 60, 80, 50, 30, 90]);
    expect(geom.labels).toEqual([
      '知识掌握', '编程能力', '认知风格', '学习目标', '知识短板', '专注度',
    ]);
    expect(geom.hasData).toBe(true);
    // 6 个数据点 + 4 层 grid (各 6 个顶点)
    expect(geom.points.length).toBe(6);
    expect(geom.levels.length).toBe(4);
    // 第一点 (i=0, angle=-PI/2): cx + 0 = 120, cy - r = (cy - R*75/100)
    expect(geom.points[0].x).toBeCloseTo(120, 5);
    expect(geom.points[0].y).toBeCloseTo(120 - 60 * 0.75, 5);
    expect(geom.points[0].v).toBe(75);
  });

  it('computeRadarPoints snapshot 为 null 时回退到零值 + hasData=false', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true, status: 200, json: () => Promise.resolve({ agents: [], pipeline: [] }),
    });
    const sb = loadTowerSandbox({ fetchImpl: fetchMock });
    const geom = sb.computeRadarPoints(null, { cx: 100, cy: 100, R: 50 });
    expect(geom.values).toEqual([0, 0, 0, 0, 0, 0]);
    expect(geom.labels.length).toBe(6);
    expect(geom.hasData).toBe(false);
    // 所有点都被 clamp 到最小 r=2, 全部聚在圆心附近
    for (const p of geom.points) {
      expect(p.r).toBe(2);
    }
    // 空 snapshot 同样视为 hasData=false
    const geom2 = sb.computeRadarPoints({}, { cx: 100, cy: 100, R: 50 });
    expect(geom2.hasData).toBe(false);
    expect(geom2.values).toEqual([0, 0, 0, 0, 0, 0]);
  });

  it('computeRadarPoints 越界值被 clamp 到 [0, 100]', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true, status: 200, json: () => Promise.resolve({ agents: [], pipeline: [] }),
    });
    const sb = loadTowerSandbox({ fetchImpl: fetchMock });
    const snapshot = {
      radar: {
        knowledge_mastery: 150,    // 超出 100
        code_skill: -25,           // 低于 0
        cognitive_style: 100,
        learning_goal: 0,
        weakness: NaN,             // 非数字 -> 回退 0
        focus_level: 'foo',        // 非数字 -> 回退 0
      },
    };
    const geom = sb.computeRadarPoints(snapshot, { cx: 0, cy: 0, R: 100 });
    expect(geom.values[0]).toBe(100);   // 150 -> 100
    expect(geom.values[1]).toBe(0);     // -25 -> 0
    expect(geom.values[2]).toBe(100);
    expect(geom.values[3]).toBe(0);
    expect(geom.values[4]).toBe(0);     // NaN -> 0
    expect(geom.values[5]).toBe(0);     // 'foo' -> 0
  });

  it('radarColorWithAlpha 把 #3b82f6 转为 rgba(59,130,246,0.5)', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true, status: 200, json: () => Promise.resolve({ agents: [], pipeline: [] }),
    });
    const sb = loadTowerSandbox({ fetchImpl: fetchMock });
    expect(sb.radarColorWithAlpha('#3b82f6', 0.5)).toBe('rgba(59,130,246,0.5)');
    expect(sb.radarColorWithAlpha('#abc', 0.25)).toBe('rgba(170,187,204,0.25)');
    expect(sb.radarColorWithAlpha('rgb(255, 0, 128)', 0.8)).toBe('rgba(255,0,128,0.8)');
    // 解析失败 -> 原样返回
    expect(sb.radarColorWithAlpha('oklch(0.5 0.1 30)', 0.3)).toBe('oklch(0.5 0.1 30)');
    expect(sb.radarColorWithAlpha('rgba(0,0,0,0.5)', 0.3)).toBe('rgba(0,0,0,0.5)');
    // 非字符串 -> 原样返回
    expect(sb.radarColorWithAlpha(null, 0.3)).toBe(null);
  });

  it('profile_updated 事件触发 renderRadarFromSnapshot + towerRadarSnapshot 更新', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true, status: 200, json: () => Promise.resolve({ agents: [], pipeline: [] }),
    });
    const sb = loadTowerSandbox({ fetchImpl: fetchMock });
    // 重置幂等旗, 重新挂订阅 (避免和前面 case 的 agent_step 订阅重叠)
    sb.__state._towerBusSubscribed = false;
    if (window.agentBus && typeof window.agentBus.clear === 'function') {
      window.agentBus.clear();
    }
    sb.subscribeToAgentBus();
    expect(sb.__state._towerBusSubscribed).toBe(true);

    // 起始 snapshot 应为 null
    expect(sb.__state.towerRadarSnapshot).toBe(null);

    // emit profile_updated, 携带 6 维 0-100 分数
    window.agentBus.emit('profile_updated', {
      trace_id: 't-radar-1',
      radar: {
        knowledge_mastery: 50,
        code_skill: 55,
        cognitive_style: 60,
        learning_goal: 45,
        weakness: 70,
        focus_level: 80,
      },
      panel: {
        card1: { label: '学习进度', value: '60%' },
      },
    });

    // towerRadarSnapshot 应被 set, 且只保留 radar + panel
    const snap = sb.__state.towerRadarSnapshot;
    expect(snap).not.toBeNull();
    expect(snap.radar.knowledge_mastery).toBe(50);
    expect(snap.panel.card1.label).toBe('学习进度');

    // 用 computeRadarPoints 验证 snapshot 是 6 维 LearningPortrait 形状
    const geom = sb.computeRadarPoints(snap, { cx: 0, cy: 0, R: 100 });
    expect(geom.values).toEqual([50, 55, 60, 45, 70, 80]);
    expect(geom.hasData).toBe(true);
  });

  // === Task 23: 4 卡画像面板 (#profile-grid) 已删除 ===
  // 4 张小卡 (学习风格 / 认知水平 / 近期目标 / 情绪状态) 与 8 tile (#profile-container) 重复。
  // 学情画像实时更新改由 8 tile 自身承担 — 见 Task #48 (8 tile 实时更新)。

  // === Task #49: 控制塔 start / pause / stop 交互 ===

  it('TOWER_MOCK_STEPS 包含 9 步, 覆盖 echo/profiler/planner/.../evaluator', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true, status: 200, json: () => Promise.resolve({ agents: [], pipeline: [] }),
    });
    const sb = loadTowerSandbox({ fetchImpl: fetchMock });
    const steps = sb.__state.TOWER_MOCK_STEPS;
    expect(Array.isArray(steps)).toBe(true);
    expect(steps.length).toBe(9);
    const ids = steps.map(s => s.id);
    expect(ids).toContain('echo');
    expect(ids).toContain('profiler');
    expect(ids).toContain('planner');
    expect(ids).toContain('document_generator');
    expect(ids).toContain('exercise_generator');
    expect(ids).toContain('mindmap_generator');
    expect(ids).toContain('video_content');
    expect(ids).toContain('resource_push');
    expect(ids).toContain('evaluator');
    // 每条都有 label
    for (const s of steps) {
      expect(typeof s.label).toBe('string');
      expect(s.label.length).toBeGreaterThan(0);
    }
  });

  it('_parseSseEnvelope 解析标准 SSE 格式 (event/data 双行) 返回 {event, data}', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true, status: 200, json: () => Promise.resolve({ agents: [], pipeline: [] }),
    });
    const sb = loadTowerSandbox({ fetchImpl: fetchMock });
    const raw = 'event: agent_step\ndata: {"from":"profiler","status":"success"}';
    const env = sb._parseSseEnvelope(raw);
    expect(env).not.toBeNull();
    expect(env.event).toBe('agent_step');
    expect(env.data.from).toBe('profiler');
    expect(env.data.status).toBe('success');
  });

  it('_parseSseEnvelope 缺 event: 行时默认 event=message, data 多行用 \\n 拼接后 parse 失败返回 null', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true, status: 200, json: () => Promise.resolve({ agents: [], pipeline: [] }),
    });
    const sb = loadTowerSandbox({ fetchImpl: fetchMock });
    // 多行 data 用 \n 拼成 "line1\nline2" — 不是合法 JSON, parse 失败 -> 整个 envelope null
    const raw = 'data: line1\ndata: line2\n';
    expect(sb._parseSseEnvelope(raw)).toBeNull();

    // 单行 data: {合法 json} 但缺 event: 行 -> event 默认 'message'
    const raw2 = 'data: {"a":1}';
    const env2 = sb._parseSseEnvelope(raw2);
    expect(env2.event).toBe('message');
    expect(env2.data.a).toBe(1);
  });

  it('_parseSseEnvelope 解析失败 (data 非 JSON) 返回 null, 不抛错', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true, status: 200, json: () => Promise.resolve({ agents: [], pipeline: [] }),
    });
    const sb = loadTowerSandbox({ fetchImpl: fetchMock });
    expect(sb._parseSseEnvelope('data: {not json}')).toBeNull();
    expect(sb._parseSseEnvelope('')).toBeNull();
    expect(sb._parseSseEnvelope('not an sse message')).toBeNull();
  });

  it('wireTowerControlButtons 幂等: 多次调用只绑一次 (dataset.wired=1)', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true, status: 200, json: () => Promise.resolve({ agents: [], pipeline: [] }),
    });
    const sb = loadTowerSandbox({ fetchImpl: fetchMock, documentHtml: ''
      + '<button id="tower-start"></button>'
      + '<button id="tower-pause"></button>'
      + '<button id="tower-stop"></button>',
    });
    // 第一次: 绑
    sb.wireTowerControlButtons();
    expect(document.getElementById('tower-start').dataset.wired).toBe('1');
    expect(document.getElementById('tower-pause').dataset.wired).toBe('1');
    expect(document.getElementById('tower-stop').dataset.wired).toBe('1');

    // 注入一个会被绑两次就 +1 的标志 — 用 click 计数验证
    let clickCount = 0;
    const origStart = document.getElementById('tower-start');
    origStart.addEventListener('click', () => { clickCount++; });
    // 第二次: 静默返回
    sb.wireTowerControlButtons();
    // 触发一次 click — 只应走我们的 startPipeline 一次
    origStart.click();
    // 由于 wireTowerControlButtons 第二次早 return, startPipeline 不会真的跑 (无 currentUser) —
    // 但额外加的 clickCount handler 仍 +1
    expect(clickCount).toBe(1);
  });

  it('wireTowerControlButtons 缺按钮时静默返回 (sandbox 友好)', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true, status: 200, json: () => Promise.resolve({ agents: [], pipeline: [] }),
    });
    // 不放任何按钮
    const sb = loadTowerSandbox({ fetchImpl: fetchMock, documentHtml: '<div></div>' });
    // 不抛错
    expect(() => sb.wireTowerControlButtons()).not.toThrow();
  });

  it('pausePipeline 切换 towerPaused 状态 + 改按钮文案', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true, status: 200, json: () => Promise.resolve({ agents: [], pipeline: [] }),
    });
    const sb = loadTowerSandbox({ fetchImpl: fetchMock, documentHtml: ''
      + '<button id="tower-start">▶ 启动</button>'
      + '<button id="tower-pause">⏸</button>'
      + '<button id="tower-stop"></button>',
    });
    // 强制标记为运行中
    sb.__state.towerPipelineRunning = true;
    sb.__state.towerPaused = false;

    // 第一次暂停 -> true
    sb.pausePipeline();
    expect(sb.__state.towerPaused).toBe(true);
    expect(document.getElementById('tower-pause').textContent).toBe('▶');

    // 第二次恢复 -> false
    sb.pausePipeline();
    expect(sb.__state.towerPaused).toBe(false);
    expect(document.getElementById('tower-pause').textContent).toBe('⏸');
  });

  it('finishPipeline 重置 UI: start 可点, pause/stop 禁用, 文案还原', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true, status: 200, json: () => Promise.resolve({ agents: [], pipeline: [] }),
    });
    const sb = loadTowerSandbox({ fetchImpl: fetchMock, documentHtml: ''
      + '<button id="tower-start" disabled>⏵ 运行中</button>'
      + '<button id="tower-pause">⏸</button>'
      + '<button id="tower-stop"></button>',
    });
    sb.__state.towerPipelineRunning = true;
    sb.__state.towerPaused = true;
    sb.finishPipeline();
    expect(sb.__state.towerPipelineRunning).toBe(false);
    expect(sb.__state.towerPaused).toBe(false);
    expect(document.getElementById('tower-start').disabled).toBe(false);
    expect(document.getElementById('tower-start').textContent).toBe('▶ 启动协作');
    expect(document.getElementById('tower-pause').disabled).toBe(true);
    expect(document.getElementById('tower-stop').disabled).toBe(true);
  });

  it('startPipeline 5xx 后端走 mock 兜底, emit agent_step + pipeline_complete', async () => {
    // 后端返回 503, sandbox 抓不到 SSE, 走 mock
    const fetchMock = vi.fn().mockResolvedValue({
      ok: false, status: 503, json: () => Promise.resolve({}),
    });
    const sb = loadTowerSandbox({ fetchImpl: fetchMock, documentHtml: ''
      + '<button id="tower-start">▶ 启动</button>'
      + '<button id="tower-pause" disabled>⏸</button>'
      + '<button id="tower-stop" disabled></button>',
    });
    // 收集 agent_step 事件
    const stepEvents = [];
    window.agentBus.subscribe('agent_step', (e) => stepEvents.push(e));
    let completeFired = false;
    window.agentBus.subscribe('pipeline_complete', () => { completeFired = true; });

    // 不等待, 设置超时 (mock 内部 setTimeout, sandbox 里也会跑)
    const startPromise = sb.startPipeline();
    // 等待 mock 跑完 (9 步 * 250~600ms ≈ 最多 ~5s; 给 8s)
    const timeout = new Promise((resolve) => setTimeout(resolve, 8000));
    await Promise.race([startPromise, timeout]);
    // 兜底: 如果 startPromise 还卡在 mock, 不影响断言
    // 此时 pipeline 至少应该已经 reset (startPipeline 走完 finally)
    // 注意: runMockPipeline 用 setTimeout, vitest fake timers 没用, 所以走真实时钟

    // 断言: towerPipelineRunning 已被 finishPipeline 置 false (startPipeline 的 finally)
    expect(sb.__state.towerPipelineRunning).toBe(false);
    // 收集到 agent_step 事件 (busy + success = 18 个)
    expect(stepEvents.length).toBeGreaterThan(0);
    // pipeline_complete 触发了
    expect(completeFired).toBe(true);
  }, 15000);

  it('stopPipeline 取消 SSE (AbortController) + 重置 UI', async () => {
    // 模拟一个永远 hang 的 fetch — Abort 后才返回 aborted
    const ctrlHolder = { ctrl: null };
    const fetchMock = vi.fn().mockImplementation((url, opts) => {
      if (url !== '/api/agents/execute') {
        return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve({ agents: [], pipeline: [] }) });
      }
      return new Promise((resolve, reject) => {
        ctrlHolder.ctrl = opts.signal;
        opts.signal.addEventListener('abort', () => {
          const e = new Error('aborted');
          e.name = 'AbortError';
          reject(e);
        });
      });
    });
    const sb = loadTowerSandbox({ fetchImpl: fetchMock, documentHtml: ''
      + '<button id="tower-start">▶ 启动</button>'
      + '<button id="tower-pause">⏸</button>'
      + '<button id="tower-stop"></button>',
    });
    // 关键: 不能预先设 towerPipelineRunning=true, 否则 startPipeline 内部 if(...) return 早退。
    // startPipeline 内部会把它设成 true。

    // 触发 startPipeline (后台跑) — 但因为 fetch 会 hang, 我们不 await
    sb.startPipeline().catch(() => {});

    // 给 startPipeline 一点时间创建 AbortController
    await new Promise(r => setTimeout(r, 50));
    // 此时 towerPipelineRunning 应被 startPipeline 内部设为 true
    expect(sb.__state.towerPipelineRunning).toBe(true);
    // towerSseAbort 应已被 set
    expect(sb.__state.towerSseAbort).not.toBeNull();

    // 触发 stop — 应当 abort
    sb.stopPipeline();
    // towerPipelineRunning 应被置 false
    expect(sb.__state.towerPipelineRunning).toBe(false);
    // finishPipeline 已经把 start 按钮可点
    expect(document.getElementById('tower-start').disabled).toBe(false);
  }, 10000);

  // === Task #50: 控制塔折叠按钮 (#tower-toggle) ===

  it('#tower-toggle 切换 #track-a-container.collapsed + 改按钮文案', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true, status: 200, json: () => Promise.resolve({ agents: [], pipeline: [] }),
    });
    const sb = loadTowerSandbox({ fetchImpl: fetchMock, documentHtml: ''
      + '<div id="track-a-container">'
      + '  <div class="tower-header">'
      + '    <div class="tower-actions">'
      + '      <button class="tower-btn" id="tower-start">▶ 启动协作</button>'
      + '      <button class="tower-btn" id="tower-pause" disabled>⏸</button>'
      + '      <button class="tower-btn" id="tower-stop" disabled>⏹</button>'
      + '      <button class="tower-btn" id="tower-toggle" aria-label="折叠控制塔">⇆ 折叠</button>'
      + '    </div>'
      + '  </div>'
      + '</div>',
    });
    // wireTowerControlButtons 绑 start/pause/stop + toggle
    sb.wireTowerControlButtons();
    const container = document.getElementById('track-a-container');
    const toggleBtn = document.getElementById('tower-toggle');
    expect(toggleBtn.dataset.wired).toBe('1');

    // 起始: 非 collapsed
    expect(container.classList.contains('collapsed')).toBe(false);

    // 第一次 click -> 折叠
    toggleBtn.click();
    expect(container.classList.contains('collapsed')).toBe(true);
    expect(toggleBtn.textContent).toBe('⇆ 展开');
    expect(toggleBtn.getAttribute('aria-label')).toBe('展开控制塔');

    // 第二次 click -> 展开
    toggleBtn.click();
    expect(container.classList.contains('collapsed')).toBe(false);
    expect(toggleBtn.textContent).toBe('⇆ 折叠');
    expect(toggleBtn.getAttribute('aria-label')).toBe('折叠控制塔');
  });

  it('#tower-toggle 缺 #track-a-container 时静默不绑 (sandbox 友好)', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true, status: 200, json: () => Promise.resolve({ agents: [], pipeline: [] }),
    });
    const sb = loadTowerSandbox({ fetchImpl: fetchMock, documentHtml: ''
      + '<button id="tower-start">▶ 启动协作</button>'
      + '<button id="tower-pause" disabled>⏸</button>'
      + '<button id="tower-stop" disabled>⏹</button>'
      + '<button id="tower-toggle">⇆ 折叠</button>',
    });
    // 不抛错; start/pause/stop 仍绑, toggleBtn 数据 wired 不应被设
    expect(() => sb.wireTowerControlButtons()).not.toThrow();
    expect(document.getElementById('tower-start').dataset.wired).toBe('1');
    expect(document.getElementById('tower-toggle').dataset.wired).toBeUndefined();
  });
});
