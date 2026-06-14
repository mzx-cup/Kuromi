/**
 * agent-tower — 新 renderTowerFlow / loadAgentCatalog / agentBus 订阅
 * 单元测试 (Task 20)
 *
 * 测试范围:
 *   1. loadAgentCatalog fetch 成功 -> 缓存到 agentCatalog
 *   2. loadAgentCatalog fetch 失败 -> 回落最小目录
 *   3. renderTowerFlow 把 agents 写到 #tower-flow, 每个节点带 data-agent 属性
 *   4. agentBus.subscribe('agent_step') 触发后, towerAgentStatus 跟着更新并重渲
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
      initAgentTower, subscribeToAgentBus,
      __state: {
        get agentCatalog() { return agentCatalog; },
        get towerAgentStatus() { return towerAgentStatus; },
        get _towerCatalogLoaded() { return towerCatalogLoaded; },
        get _towerBusSubscribed() { return _towerBusSubscribed; },
        get _towerInitialized() { return _towerInitialized; },
        set agentCatalog(v) { agentCatalog = v; },
        set towerAgentStatus(v) { towerAgentStatus = v; },
        set _towerCatalogLoaded(v) { towerCatalogLoaded = v; },
        set _towerBusSubscribed(v) { _towerBusSubscribed = v; },
        set _towerInitialized(v) { _towerInitialized = v; },
      },
    };
  `;

  // eslint-disable-next-line no-new-func
  const factory = new Function(factorySrc);
  return factory({ fetchImpl: sbFetch, win: window, doc: document });
}

describe('agent-tower — 新数据源渲染', () => {
  beforeEach(async () => {
    document.body.innerHTML = '<div class="tower-flow" id="tower-flow"></div>';
    // 加载 agent-bus 干净实例
    delete window.agentBus;
    vi.resetModules();
    await import('../../../js/agent-bus.js');
  });

  afterEach(() => {
    vi.restoreAllMocks();
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
});
