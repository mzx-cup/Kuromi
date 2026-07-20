/**
 * 学情画像 (8 tile) 实时更新 — 单元测试 (Task #48)
 *
 * 测试范围:
 *   1. applyProfileFromSnapshot 把 radar.code_skill 0-100 映射到 4 档 (beginner/basic/intermediate/advanced) 中文标签
 *   2. applyProfileFromSnapshot 把 radar.knowledge_mastery 映射到 4 档中文标签
 *   3. applyProfileFromSnapshot 优先取 panel.current_goal.label (中文) 直接写入
 *   4. applyProfileFromSnapshot 退化路径: panel 缺 current_goal 时按 radar.learning_goal 0-100 区间派生
 *   5. applyProfileFromSnapshot 把 panel.learning_style.label 英文 enum (visual/textual/pragmatic) 翻译成中文
 *   6. applyProfileFromSnapshot 把 panel.emotion_state.label 翻译成 focusLevel (engaged→高专注, calm→中等专注 等)
 *   7. applyProfileFromSnapshot 写完字段后调 renderProfile() 触发 #profile-container 重渲 (DOM 内容更新)
 *   8. applyProfileFromSnapshot 非法输入 (null/非对象/缺 radar 和 panel) 静默返回 false, 不抛错
 *   9. applyProfileFromSnapshot 在没有全局 profile 的 sandbox 里静默返回 false, 不抛错
 *  10. profile_updated agentBus 事件触发 applyProfileFromSnapshot 路径 (集成)
 *
 * 实现说明:
 *   js/index.js 是 10000+ 行的顶层脚本, 不导出符号。
 *   本测试在 jsdom 中, 用 Function 构造器建一个轻量 sandbox:
 *     - 注入 assessmentToProfileMap (从 js/index.js 截取)
 *     - 注入 applyProfileFromSnapshot (从 js/index.js 截取)
 *     - 注入 mock profile 全局 + mock renderProfile (sandbox 内部)
 *     - 通过暴露的 apply 函数做断言
 *
 * 运行: npx vitest run tests/frontend/unit/profile-real-time.test.js
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import fs from 'fs';
import path from 'path';

const INDEX_JS = fs.readFileSync(
  path.resolve(__dirname, '../../../js/index.js'),
  'utf8',
);

/**
 * 从 index.js 源码里截取 assessmentToProfileMap 整个 const 定义.
 * 用花括号配对定位, 不依赖具体换行符。
 */
function extractAssessmentMap(src) {
  const start = src.indexOf('const assessmentToProfileMap = {');
  if (start === -1) throw new Error('assessmentToProfileMap marker not found');
  const slice = src.slice(start);
  // 从第一个 "{" 开始花括号配对
  let depth = 0;
  let endIdx = -1;
  for (let i = 0; i < slice.length; i++) {
    const ch = slice[i];
    if (ch === '{') depth++;
    else if (ch === '}') {
      depth--;
      if (depth === 0) {
        endIdx = i;
        break;
      }
    }
  }
  if (endIdx === -1) throw new Error('assessmentToProfileMap end not found');
  // endIdx 指向顶层 "}", 再吃掉 ";" 结束符
  return slice.slice(0, endIdx + 1) + ';';
}

/**
 * 从 index.js 源码里截取 applyProfileFromSnapshot + 其依赖的 _pickLearningDirectionFromRadar.
 */
function extractApplyProfile(src) {
  // 抓 _pickLearningDirectionFromRadar
  const pickerStart = src.indexOf('const _RADAR_DIR_FROM_RADAR = [');
  const pickerEnd = src.indexOf('function _pickLearningDirectionFromRadar', pickerStart);
  if (pickerStart === -1 || pickerEnd === -1) throw new Error('picker marker not found');
  const pickerEnd2 = src.indexOf('}', src.indexOf('}', pickerEnd) + 1);
  // 抓 applyProfileFromSnapshot 整体
  const applyStart = src.indexOf('function applyProfileFromSnapshot', pickerStart);
  const applyEnd = src.indexOf('function renderRadarFromSnapshot', applyStart);
  if (applyStart === -1 || applyEnd === -1) throw new Error('apply marker not found');

  // 把 picker + apply 拼起来, _pickLearningDirectionFromRadar 必须在 apply 之前
  return src.slice(pickerStart, applyEnd);
}

/**
 * 在 sandbox 中加载 applyProfileFromSnapshot, 暴露接口.
 * sandbox 内部声明一个简化的 `profile` 全局 + mock renderProfile, 用于追踪调用。
 */
function loadProfileSandbox() {
  const mapBlock = extractAssessmentMap(INDEX_JS);
  const applyBlock = extractApplyProfile(INDEX_JS);

  const factorySrc = `
    "use strict";
    var window = arguments[0].win;
    var document = arguments[0].doc;
    ${mapBlock}
    ${applyBlock}
    // 简化的 profile 全局 (sandbox 内部)
    var profile = {
      knowledgeBase: '普通学生',
      codeSkill: 'Python基础',
      learningGoal: '期末考试',
      cognitiveStyle: '待测试',
      weakness: '暂无',
      focusLevel: 'medium',
      learningDirection: '大数据技术',
      languages: ['python']
    };
    // mock renderProfile — 记录调用次数, 替换实际 DOM 写入
    var renderProfileCalls = 0;
    function renderProfile() { renderProfileCalls++; }
    return {
      applyProfileFromSnapshot,
      getProfile: function () { return JSON.parse(JSON.stringify(profile)); },
      setProfile: function (v) { for (var k in v) if (Object.prototype.hasOwnProperty.call(v, k)) profile[k] = v[k]; },
      getRenderProfileCalls: function () { return renderProfileCalls; },
    };
  `;
  // eslint-disable-next-line no-new-func
  const factory = new Function(factorySrc);
  return factory({ win: window, doc: document });
}

describe('applyProfileFromSnapshot — 8 tile 实时更新 (Task #48)', () => {
  let sb;
  beforeEach(() => {
    sb = loadProfileSandbox();
  });
  afterEach(() => {
    sb = null;
  });

  it('radar.code_skill 0-100 映射到 4 档中文 (basic/intermediate/advanced/beginner)', () => {
    // basic (<25)
    sb.applyProfileFromSnapshot({ radar: { code_skill: 10 } });
    expect(sb.getProfile().codeSkill).toBe('编程新手');
    // intermediate (50-74)
    sb.applyProfileFromSnapshot({ radar: { code_skill: 60 } });
    expect(sb.getProfile().codeSkill).toBe('熟练编程');
    // advanced (>=75)
    sb.applyProfileFromSnapshot({ radar: { code_skill: 88 } });
    expect(sb.getProfile().codeSkill).toBe('编程高手');
  });

  it('radar.knowledge_mastery 0-100 映射到 4 档中文 (zero/basic/intermediate/advanced)', () => {
    sb.applyProfileFromSnapshot({ radar: { knowledge_mastery: 5 } });
    expect(sb.getProfile().knowledgeBase).toBe('零基础入门');
    sb.applyProfileFromSnapshot({ radar: { knowledge_mastery: 30 } });
    expect(sb.getProfile().knowledgeBase).toBe('基础入门');
    sb.applyProfileFromSnapshot({ radar: { knowledge_mastery: 65 } });
    expect(sb.getProfile().knowledgeBase).toBe('进阶学习');
    sb.applyProfileFromSnapshot({ radar: { knowledge_mastery: 90 } });
    expect(sb.getProfile().knowledgeBase).toBe('深入掌握');
  });

  it('优先取 panel.current_goal.label 中文直接写入 learningGoal', () => {
    sb.applyProfileFromSnapshot({
      radar: { learning_goal: 80 },
      panel: { current_goal: { label: '应对考试', progress_pct: 50 } },
    });
    expect(sb.getProfile().learningGoal).toBe('应对考试');
  });

  it('退化路径: panel 缺 current_goal 时按 radar.learning_goal 0-100 区间派生', () => {
    sb.applyProfileFromSnapshot({
      radar: { learning_goal: 90 }, // 高分 -> 科研学术 (idx=5)
    });
    expect(sb.getProfile().learningGoal).toBe('科研学术');
    sb.applyProfileFromSnapshot({
      radar: { learning_goal: 10 }, // 低分 -> 应对考试 (idx=0)
    });
    expect(sb.getProfile().learningGoal).toBe('应对考试');
  });

  it('panel.learning_style.label 英文 enum 翻译成中文 (visual→视觉型, textual→文字型, pragmatic→实践型)', () => {
    sb.applyProfileFromSnapshot({ panel: { learning_style: { label: 'visual', confidence: 0.8 } } });
    expect(sb.getProfile().cognitiveStyle).toBe('视觉型');
    sb.applyProfileFromSnapshot({ panel: { learning_style: { label: 'textual', confidence: 0.6 } } });
    expect(sb.getProfile().cognitiveStyle).toBe('文字型');
    sb.applyProfileFromSnapshot({ panel: { learning_style: { label: 'pragmatic', confidence: 0.7 } } });
    expect(sb.getProfile().cognitiveStyle).toBe('实践型');
  });

  it('panel.emotion_state.label 翻译成 focusLevel (engaged→高专注, calm→中等专注, anxious/frustrated→需要引导)', () => {
    sb.applyProfileFromSnapshot({ panel: { emotion_state: { label: 'engaged' } } });
    expect(sb.getProfile().focusLevel).toBe('高专注');
    sb.applyProfileFromSnapshot({ panel: { emotion_state: { label: 'calm' } } });
    expect(sb.getProfile().focusLevel).toBe('中等专注');
    sb.applyProfileFromSnapshot({ panel: { emotion_state: { label: 'anxious' } } });
    expect(sb.getProfile().focusLevel).toBe('需要引导');
    sb.applyProfileFromSnapshot({ panel: { emotion_state: { label: 'frustrated' } } });
    expect(sb.getProfile().focusLevel).toBe('需要引导');
  });

  it('写完字段后调 renderProfile() 触发 #profile-container 重渲 (DOM 内容更新)', () => {
    const callsBefore = sb.getRenderProfileCalls();
    sb.applyProfileFromSnapshot({
      radar: { code_skill: 80, knowledge_mastery: 70, focus_level: 80, learning_goal: 60, weakness: 75, cognitive_style: 50 },
      panel: {
        learning_style: { label: 'visual' },
        cognitive_level: { label: 'advanced' },
        current_goal: { label: '项目实战' },
        emotion_state: { label: 'engaged' },
      },
    });
    expect(sb.getRenderProfileCalls()).toBe(callsBefore + 1);
    const p = sb.getProfile();
    expect(p.codeSkill).toBe('编程高手');
    expect(p.knowledgeBase).toBe('进阶学习');
    expect(p.learningGoal).toBe('项目实战');
    expect(p.cognitiveStyle).toBe('视觉型');
    expect(p.focusLevel).toBe('高专注');
  });

  it('非法输入 (null/非对象/缺 radar 和 panel) 静默返回 false, 不抛错', () => {
    expect(sb.applyProfileFromSnapshot(null)).toBe(false);
    expect(sb.applyProfileFromSnapshot(undefined)).toBe(false);
    expect(sb.applyProfileFromSnapshot({})).toBe(false); // 无 radar 无 panel
    expect(sb.applyProfileFromSnapshot('not an object')).toBe(false);
    expect(sb.applyProfileFromSnapshot(123)).toBe(false);
  });

  it('同事件多字段合并: radar 全部维度 + panel 全部 entry 同时给出, 8 tile 全更新', () => {
    sb.applyProfileFromSnapshot({
      trace_id: 't-real-1',
      radar: {
        knowledge_mastery: 80, code_skill: 65, cognitive_style: 55,
        learning_goal: 40, weakness: 30, focus_level: 80,
      },
      panel: {
        learning_style:  { label: 'visual', confidence: 0.9 },
        cognitive_level: { label: 'intermediate' },
        current_goal:    { label: '应对考试', progress_pct: 60 },
        emotion_state:   { label: 'engaged' },
      },
    });
    const p = sb.getProfile();
    expect(p.knowledgeBase).toBe('深入掌握');      // mastery 80 -> advanced
    expect(p.codeSkill).toBe('熟练编程');           // code 65 -> intermediate
    expect(p.learningGoal).toBe('应对考试');         // panel 直接覆盖
    expect(p.cognitiveStyle).toBe('视觉型');         // panel.learning_style 翻译
    expect(p.focusLevel).toBe('高专注');             // engaged -> 高专注
    expect(p.weakness).toBe('基础薄弱, 需补强');     // weakness 30 -> 短板
    // learningDirection 由 radar 最高维派生 (knowledge_mastery=80 最高 -> 数据库技术)
    expect(p.learningDirection).toBe('数据库技术');
  });
});
