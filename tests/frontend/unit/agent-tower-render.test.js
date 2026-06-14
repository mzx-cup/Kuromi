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
 *  14. formatPanelLabel learning_style 显示 label + 置信度 (Task 23)
 *  15. formatPanelLabel emotion_state 翻译为中文 (Task 23)
 *  16. renderProfilePanel 写入 4 卡 data-key + 进度条宽度 + 情绪 class (Task 23)
 *  17. profile_updated 事件触发 renderProfilePanel (Task 23)
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
      // Task 23: 4 卡画像面板渲染
      formatPanelLabel, renderProfilePanel,
      PANEL_KEYS, EMOTION_LABEL_MAP, EMOTION_CLASS_PREFIX,
      PANEL_EMOTION_CLASSES,
      __state: {
        get agentCatalog() { return agentCatalog; },
        get towerAgentStatus() { return towerAgentStatus; },
        get towerLogs() { return towerLogs; },
        get TOWER_LOG_MAX() { return TOWER_LOG_MAX; },
        get _towerCatalogLoaded() { return towerCatalogLoaded; },
        get _towerBusSubscribed() { return _towerBusSubscribed; },
        get _towerInitialized() { return _towerInitialized; },
        get towerRadarSnapshot() { return towerRadarSnapshot; },
        set agentCatalog(v) { agentCatalog = v; },
        set towerAgentStatus(v) { towerAgentStatus = v; },
        set towerLogs(v) { towerLogs = v; },
        set _towerCatalogLoaded(v) { towerCatalogLoaded = v; },
        set _towerBusSubscribed(v) { _towerBusSubscribed = v; },
        set _towerInitialized(v) { _towerInitialized = v; },
        set towerRadarSnapshot(v) { towerRadarSnapshot = v; },
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

  // === Task 23: 4 卡画像面板 (#profile-grid) — 单元 + 集成 ===

  /**
   * 构造一个最小可用的 #profile-grid DOM 片段, 供渲染测试复用。
   * 形状要和 html/index.html 的 4 卡 + 进度条 + last-synced 一致。
   */
  function buildProfileGridHtml() {
    return '<div class="profile-grid" id="profile-grid">'
      + '<div class="profile-card">'
      +   '<div class="profile-card-title">学习风格</div>'
      +   '<div class="profile-card-value" data-key="learning_style">—</div>'
      + '</div>'
      + '<div class="profile-card">'
      +   '<div class="profile-card-title">认知水平</div>'
      +   '<div class="profile-card-value" data-key="cognitive_level">—</div>'
      + '</div>'
      + '<div class="profile-card">'
      +   '<div class="profile-card-title">近期目标</div>'
      +   '<div class="profile-card-value" data-key="current_goal">—</div>'
      +   '<div class="profile-progress-bar"><div data-key="current_goal_bar"></div></div>'
      + '</div>'
      + '<div class="profile-card">'
      +   '<div class="profile-card-title">情绪状态</div>'
      +   '<div class="profile-card-value" data-key="emotion_state">—</div>'
      + '</div>'
      + '</div>'
      + '<div class="profile-last-synced" id="profile-last-synced">Last synced: —</div>';
  }

  it('formatPanelLabel learning_style 显示 label + 置信度百分比', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true, status: 200, json: () => Promise.resolve({ agents: [], pipeline: [] }),
    });
    const sb = loadTowerSandbox({ fetchImpl: fetchMock });
    expect(sb.formatPanelLabel('learning_style', { label: 'visual', confidence: 0.7 })).toBe('visual · 70%');
    // confidence=0.34 -> 34% (round), label/textual
    expect(sb.formatPanelLabel('learning_style', { label: 'textual', confidence: 0.34 })).toBe('textual · 34%');
    // 缺 confidence -> 只显示 label
    expect(sb.formatPanelLabel('learning_style', { label: 'pragmatic' })).toBe('pragmatic');
    // 缺 label -> 显示 "—"
    expect(sb.formatPanelLabel('learning_style', { confidence: 0.5 })).toBe('—');
    expect(sb.formatPanelLabel('learning_style', null)).toBe('—');
  });

  it('formatPanelLabel emotion_state 翻译为中文 (calm→平静 / anxious→焦虑 / frustrated→受挫 / engaged→专注)', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true, status: 200, json: () => Promise.resolve({ agents: [], pipeline: [] }),
    });
    const sb = loadTowerSandbox({ fetchImpl: fetchMock });
    expect(sb.formatPanelLabel('emotion_state', { label: 'frustrated' })).toBe('受挫');
    expect(sb.formatPanelLabel('emotion_state', { label: 'calm' })).toBe('平静');
    expect(sb.formatPanelLabel('emotion_state', { label: 'anxious' })).toBe('焦虑');
    expect(sb.formatPanelLabel('emotion_state', { label: 'engaged' })).toBe('专注');
    // 未知 label -> 原样
    expect(sb.formatPanelLabel('emotion_state', { label: 'happy' })).toBe('happy');
    // 缺 entry -> "—"
    expect(sb.formatPanelLabel('emotion_state', null)).toBe('—');
  });

  it('renderProfilePanel 写入 4 卡 data-key + 进度条宽度 + 情绪 class', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true, status: 200, json: () => Promise.resolve({ agents: [], pipeline: [] }),
    });
    // 装载带 #profile-grid 的 DOM
    const sb = loadTowerSandbox({ fetchImpl: fetchMock, documentHtml: buildProfileGridHtml() });

    const panel = {
      learning_style:  { label: 'visual', confidence: 0.5 },
      cognitive_level: { label: 'intermediate' },
      current_goal:    { label: '应对考试', progress_pct: 75 },
      emotion_state:   { label: 'anxious' },
    };
    sb.renderProfilePanel(panel);

    const grid = document.getElementById('profile-grid');
    // 4 卡 data-key 都被写入
    expect(grid.querySelector('[data-key="learning_style"]').textContent).toBe('visual · 50%');
    expect(grid.querySelector('[data-key="cognitive_level"]').textContent).toBe('intermediate');
    expect(grid.querySelector('[data-key="current_goal"]').textContent).toBe('应对考试');
    expect(grid.querySelector('[data-key="emotion_state"]').textContent).toBe('焦虑');
    // 进度条宽度
    expect(grid.querySelector('[data-key="current_goal_bar"]').style.width).toBe('75%');
    // 情绪 class
    const emotionEl = grid.querySelector('[data-key="emotion_state"]');
    expect(emotionEl.classList.contains('is-anxious')).toBe(true);
    expect(emotionEl.classList.contains('is-calm')).toBe(false);
    expect(emotionEl.classList.contains('is-frustrated')).toBe(false);
    expect(emotionEl.classList.contains('is-engaged')).toBe(false);

    // 二次调用换成 calm -> is-anxious 移除, is-calm 添加
    sb.renderProfilePanel({
      learning_style:  { label: 'visual' },
      cognitive_level: { label: 'beginner' },
      current_goal:    { label: '补基础', progress_pct: 30 },
      emotion_state:   { label: 'calm' },
    });
    expect(grid.querySelector('[data-key="emotion_state"]').textContent).toBe('平静');
    expect(grid.querySelector('[data-key="emotion_state"]').classList.contains('is-calm')).toBe(true);
    expect(grid.querySelector('[data-key="emotion_state"]').classList.contains('is-anxious')).toBe(false);
    expect(grid.querySelector('[data-key="current_goal_bar"]').style.width).toBe('30%');

    // 传 null -> 占位 "—", 进度条归零
    sb.renderProfilePanel(null);
    for (const key of sb.PANEL_KEYS) {
      expect(grid.querySelector('[data-key="' + key + '"]').textContent).toBe('—');
    }
    expect(grid.querySelector('[data-key="current_goal_bar"]').style.width).toBe('0%');
    // 情绪 class 全部清掉
    const emotionEl2 = grid.querySelector('[data-key="emotion_state"]');
    for (const cls of sb.PANEL_EMOTION_CLASSES) {
      expect(emotionEl2.classList.contains(cls)).toBe(false);
    }
  });

  it('profile_updated 事件触发 renderProfilePanel 写入 4 卡', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true, status: 200, json: () => Promise.resolve({ agents: [], pipeline: [] }),
    });
    const sb = loadTowerSandbox({ fetchImpl: fetchMock, documentHtml: buildProfileGridHtml() });
    sb.__state._towerBusSubscribed = false;
    if (window.agentBus && typeof window.agentBus.clear === 'function') {
      window.agentBus.clear();
    }
    sb.subscribeToAgentBus();

    // 起始: 4 卡全是 "—"
    const grid = document.getElementById('profile-grid');
    for (const key of sb.PANEL_KEYS) {
      expect(grid.querySelector('[data-key="' + key + '"]').textContent).toBe('—');
    }

    // emit profile_updated 带 panel
    window.agentBus.emit('profile_updated', {
      trace_id: 't-panel-1',
      radar: {
        knowledge_mastery: 60, code_skill: 60, cognitive_style: 60,
        learning_goal: 60, weakness: 60, focus_level: 60,
      },
      panel: {
        learning_style:  { label: 'textual', confidence: 0.8 },
        cognitive_level: { label: 'advanced' },
        current_goal:    { label: '考研冲刺', progress_pct: 42 },
        emotion_state:   { label: 'engaged' },
      },
    });

    // 4 卡都被更新
    expect(grid.querySelector('[data-key="learning_style"]').textContent).toBe('textual · 80%');
    expect(grid.querySelector('[data-key="cognitive_level"]').textContent).toBe('advanced');
    expect(grid.querySelector('[data-key="current_goal"]').textContent).toBe('考研冲刺');
    expect(grid.querySelector('[data-key="emotion_state"]').textContent).toBe('专注');
    expect(grid.querySelector('[data-key="current_goal_bar"]').style.width).toBe('42%');
    expect(grid.querySelector('[data-key="emotion_state"]').classList.contains('is-engaged')).toBe(true);

    // towerRadarSnapshot.panel 也被设上 (Task 22 已经覆盖, 这里再次确认)
    expect(sb.__state.towerRadarSnapshot.panel.learning_style.label).toBe('textual');
  });
});
