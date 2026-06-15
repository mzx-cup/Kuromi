/**
 * CodeMonaco — Monaco Editor 封装
 * 通过 AMD loader (CDN) 延迟加载，避免首屏阻塞。
 *
 * AMD 加载链：
 *   1. append <script src=".../loader.js"> — jsdelivr CDN 上的官方 AMD loader
 *   2. loader 注入 window.require
 *   3. require(['vs/editor/editor.main']) → 触发 Monaco 主入口 → 挂载 window.monaco
 *
 * 后续任务：
 *   - Task 6: 新增 create() 在指定 textarea 位置挂载编辑器实例
 *   - Task 7: 新增 typeCodeToEditor() 打字机适配
 */
const MONACO_VERSION = '0.45.0';
const MONACO_LOADER_URL = `https://cdn.jsdelivr.net/npm/monaco-editor@${MONACO_VERSION}/min/vs/loader.js`;
const LOADER_ATTR = 'data-monaco-loader';

let loadPromise = null;

export async function load() {
  if (loadPromise) return loadPromise;
  if (window.monaco) {
    loadPromise = Promise.resolve(window.monaco);
    return loadPromise;
  }
  // 记录 load 之前 window.require 的状态，失败时还原，
  // 避免覆盖页面已有的 require.js / 其他 AMD loader 配置。
  const prevRequire = Object.prototype.hasOwnProperty.call(window, 'require')
    ? window.require
    : undefined;
  loadPromise = new Promise((resolve, reject) => {
    // ensure require config is set BEFORE loader runs
    window.require = window.require || {
      paths: { vs: `https://cdn.jsdelivr.net/npm/monaco-editor@${MONACO_VERSION}/min/vs` },
    };
    const script = document.createElement('script');
    script.src = MONACO_LOADER_URL;
    script.setAttribute(LOADER_ATTR, 'true');
    script.onload = () => {
      window.require(['vs/editor/editor.main'], () => {
        resolve(window.monaco);
      });
    };
    script.onerror = () => {
      // 还原 pre-existing window.require（如果 load 之前页面已经设置了它）
      if (prevRequire === undefined) {
        delete window.require;
      } else {
        window.require = prevRequire;
      }
      loadPromise = null;  // 失败时清空缓存，允许重试
      reject(new Error('Monaco loader failed'));
    };
    document.head.appendChild(script);
  });
  return loadPromise;
}

export const CodeMonaco = { load };
if (typeof window !== 'undefined') window.CodeMonaco = CodeMonaco;
