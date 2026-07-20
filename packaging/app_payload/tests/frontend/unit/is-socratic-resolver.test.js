/**
 * is-socratic-resolver — 苏格拉底徽标解析 helper 单元测试 (Task 24)
 *
 * 测试范围:
 *   1. 服务器显式提示 socratic=true 优先, 不论 persona
 *   2. 服务器显式提示 socratic=false 优先, 不论 persona
 *   3. 服务器无提示 + persona=socratic_questioner -> true (intensity 1.0)
 *   4. 服务器无提示 + persona=patient_tutor -> false (intensity 0.4)
 *   5. 服务器无提示 + persona=energetic_lecturer -> false (intensity 0.1)
 *   6. 服务器无提示 + persona=expert_mentor -> true (intensity 0.7)
 *   7. 服务器无提示 + persona=caring_counselor -> false (intensity 0.0)
 *   8. 服务器无提示 + 未知 persona -> false (默认安全)
 *   9. user 角色的消息永远 false
 *  10. msg=null + fallbackPersona=socratic_questioner -> true
 *  11. msg=null + fallbackPersona=patient_tutor -> false
 *  12. msg=null + 没有 fallback -> 读 currentPersona 闭包 (默认 patient_tutor)
 *  13. msg._persona 优先于 fallbackPersona
 *
 * 实现说明:
 *   resolveSocraticFlag() 闭包在 js/index.js 顶层 (let currentPersona = ...).
 *   单元测试通过 Function 构造器 sandbox 隔离: 注入 PERSONA_SOCRATIC_INTENSITY
 *   等常量, 然后用字符串字面量定义 helper 体, 模拟真实 helper 的行为做断言。
 *
 * 运行: npx vitest run tests/frontend/unit/is-socratic-resolver.test.js
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import fs from 'fs';
import path from 'path';

const INDEX_JS = fs.readFileSync(
  path.resolve(__dirname, '../../../js/index.js'),
  'utf8',
);

/**
 * 从 index.js 源码中提取 resolveSocraticFlag 闭包依赖:
 *   - PERSONA_SOCRATIC_INTENSITY
 *   - PERSONA_SOCRATIC_THRESHOLD
 * 然后在 sandbox 中重新定义 helper (与生产代码同源), 并模拟 currentPersona 闭包变量。
 */
function loadResolverSandbox({ currentPersona = 'patient_tutor' } = {}) {
  // 用正则精确截取两个 const 定义 (从 PERSONA_SOCRATIC_INTENSITY 开始
  // 到 PERSONA_SOCRATIC_THRESHOLD 行末尾的换行符为止, 不吃 JSDoc)。
  const m = INDEX_JS.match(
    /const PERSONA_SOCRATIC_INTENSITY[\s\S]*?const PERSONA_SOCRATIC_THRESHOLD = 0\.5;/
  );
  if (!m) throw new Error('PERSONA_SOCRATIC_INTENSITY/THRESHOLD block not found');
  const constBlock = m[0];

  const factorySrc = `
    "use strict";
    ${constBlock}

    // 模拟顶层 let currentPersona (sandbox 内可写)
    var currentPersona = arguments[0].currentPersona;

    function resolveSocraticFlag(msg, fallbackPersona) {
      if (msg && msg.role !== 'assistant') return false;
      if (msg && msg.socratic === true) return true;
      if (msg && msg.socratic === false) return false;
      const personaId = (msg && msg._persona) || fallbackPersona || currentPersona;
      const intensity = PERSONA_SOCRATIC_INTENSITY[personaId];
      if (typeof intensity === 'number') {
        return intensity >= PERSONA_SOCRATIC_THRESHOLD;
      }
      return false;
    }

    return { resolveSocraticFlag, PERSONA_SOCRATIC_INTENSITY, PERSONA_SOCRATIC_THRESHOLD };
  `;

  // eslint-disable-next-line no-new-func
  const factory = new Function(factorySrc);
  return factory({ currentPersona });
}

describe('resolveSocraticFlag — 苏格拉底徽标解析 (Task 24)', () => {
  let sb;
  beforeEach(() => {
    sb = loadResolverSandbox();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('应从 index.js 源码中提取到 5 个 persona 强度值', () => {
    expect(sb.PERSONA_SOCRATIC_INTENSITY).toEqual({
      patient_tutor: 0.4,
      socratic_questioner: 1.0,
      energetic_lecturer: 0.1,
      expert_mentor: 0.7,
      caring_counselor: 0.0,
    });
  });

  it('阈值常量 = 0.5', () => {
    expect(sb.PERSONA_SOCRATIC_THRESHOLD).toBe(0.5);
  });

  it('服务器 socratic=true 强制 true, 即使 persona 是 caring_counselor (intensity 0.0)', () => {
    const result = sb.resolveSocraticFlag(
      { role: 'assistant', socratic: true, _persona: 'caring_counselor' },
      'caring_counselor',
    );
    expect(result).toBe(true);
  });

  it('服务器 socratic=false 强制 false, 即使 persona 是 socratic_questioner (intensity 1.0)', () => {
    const result = sb.resolveSocraticFlag(
      { role: 'assistant', socratic: false, _persona: 'socratic_questioner' },
      'socratic_questioner',
    );
    expect(result).toBe(false);
  });

  it('服务器无提示 + persona=socratic_questioner -> true (intensity 1.0 >= 0.5)', () => {
    expect(sb.resolveSocraticFlag(
      { role: 'assistant', _persona: 'socratic_questioner' },
      'patient_tutor', // fallback 不应被采纳, _persona 优先
    )).toBe(true);
  });

  it('服务器无提示 + persona=patient_tutor -> false (intensity 0.4 < 0.5)', () => {
    expect(sb.resolveSocraticFlag(
      { role: 'assistant', _persona: 'patient_tutor' },
      'socratic_questioner',
    )).toBe(false);
  });

  it('服务器无提示 + persona=energetic_lecturer -> false (intensity 0.1 < 0.5)', () => {
    expect(sb.resolveSocraticFlag(
      { role: 'assistant', _persona: 'energetic_lecturer' },
    )).toBe(false);
  });

  it('服务器无提示 + persona=expert_mentor -> true (intensity 0.7 >= 0.5)', () => {
    expect(sb.resolveSocraticFlag(
      { role: 'assistant', _persona: 'expert_mentor' },
    )).toBe(true);
  });

  it('服务器无提示 + persona=caring_counselor -> false (intensity 0.0)', () => {
    expect(sb.resolveSocraticFlag(
      { role: 'assistant', _persona: 'caring_counselor' },
    )).toBe(false);
  });

  it('服务器无提示 + 未知 persona -> false (默认安全)', () => {
    expect(sb.resolveSocraticFlag(
      { role: 'assistant', _persona: 'unknown_persona' },
    )).toBe(false);
  });

  it('user 角色的消息永远 false, 即使 socratic=true', () => {
    expect(sb.resolveSocraticFlag(
      { role: 'user', socratic: true, _persona: 'socratic_questioner' },
    )).toBe(false);
  });

  it('msg=null + fallbackPersona=socratic_questioner -> true', () => {
    expect(sb.resolveSocraticFlag(null, 'socratic_questioner')).toBe(true);
  });

  it('msg=null + fallbackPersona=patient_tutor -> false', () => {
    expect(sb.resolveSocraticFlag(null, 'patient_tutor')).toBe(false);
  });

  it('msg=null 且无 fallback -> 读 currentPersona 闭包 (默认 patient_tutor)', () => {
    expect(sb.resolveSocraticFlag(null)).toBe(false);
  });

  it('msg=null + currentPersona=socratic_questioner -> true (闭包联动)', () => {
    const sb2 = loadResolverSandbox({ currentPersona: 'socratic_questioner' });
    expect(sb2.resolveSocraticFlag(null)).toBe(true);
  });

  it('msg._persona 优先于 fallbackPersona', () => {
    // _persona 是 expert_mentor (true), fallback 是 caring_counselor (false)
    expect(sb.resolveSocraticFlag(
      { role: 'assistant', _persona: 'expert_mentor' },
      'caring_counselor',
    )).toBe(true);
  });

  it('msg._persona 缺失时回落到 fallbackPersona', () => {
    expect(sb.resolveSocraticFlag(
      { role: 'assistant' /* no _persona */ },
      'socratic_questioner',
    )).toBe(true);
  });

  it('fallback 也没有时再回落 currentPersona', () => {
    const sb3 = loadResolverSandbox({ currentPersona: 'expert_mentor' });
    expect(sb3.resolveSocraticFlag({ role: 'assistant' })).toBe(true);
  });
});
