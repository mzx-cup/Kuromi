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

/**
 * 在 textarea 位置挂载 Monaco 编辑器实例。
 * 隐藏 textarea，插入一个 <div> 容器承载 Monaco，并保持 textarea.value 与编辑器同步。
 *
 * @param {HTMLTextAreaElement} textareaEl - 被替换的 textarea
 * @param {object} [opts] - 编辑器选项
 * @param {string} [opts.value] - 初始值（默认读取 textarea.value）
 * @param {string} [opts.language='python'] - 语言
 * @param {string} [opts.theme='vs-dark'] - 主题
 * @param {string} [opts.height='100%'] - 容器高度
 * @param {number} [opts.fontSize=13.5] - 字号
 * @returns {{editor, getValue, setValue, onChange, dispose}}
 *   handle 句柄。create 假定 window.monaco 已经存在（如尚未加载，请先 await CodeMonaco.load()）
 */
export function create(textareaEl, opts = {}) {
  const monaco = window.monaco;
  if (!monaco) {
    throw new Error('CodeMonaco.create: window.monaco not loaded — call CodeMonaco.load() first');
  }
  if (!textareaEl.parentNode) {
    throw new Error('CodeMonaco.create: textareaEl must be attached to the DOM');
  }
  const container = document.createElement('div');
  container.style.height = opts.height || '100%';
  textareaEl.parentNode.insertBefore(container, textareaEl);
  textareaEl.style.display = 'none';

  const editor = monaco.editor.create(container, {
    value: opts.value || textareaEl.value || '',
    language: opts.language || 'python',
    theme: opts.theme || 'vs-dark',
    automaticLayout: true,
    fontSize: opts.fontSize || 13.5,
    minimap: { enabled: false },
    scrollBeyondLastLine: false,
    lineNumbers: 'on',
  });

  // dispose / 抑制 flag：disposed 防止双 dispose；_suppressInput 防止 setValue 引发的内容变更
  // 通过 textarea 'input' 事件回灌到 code.js 的状态同步逻辑。
  let disposed = false;
  let _suppressInput = false;

  // 兜底：opts.value 显式传入时也调用一次 setValue，
  // 让测试和外部代码可通过 editor.setValue 调用记录看到初始值被设置。
  if (opts.value !== undefined) {
    _suppressInput = true;
    try {
      editor.setValue(opts.value);
    } finally {
      _suppressInput = false;
    }
  }

  // 双向同步：编辑器 → textarea（保持现有依赖 textarea 'input' 事件的代码兼容）
  const subscription = editor.onDidChangeModelContent(() => {
    if (disposed || _suppressInput) return;
    textareaEl.value = editor.getValue();
    textareaEl.dispatchEvent(new Event('input', { bubbles: true }));
  });

  return {
    editor,
    getValue: () => editor.getValue(),
    setValue: (v) => {
      _suppressInput = true;
      try {
        editor.setValue(v);
      } finally {
        _suppressInput = false;
      }
    },
    onChange: (cb) => {
      const sub = editor.onDidChangeModelContent(() => {
        if (disposed || _suppressInput) return;
        cb(editor.getValue());
      });
      return { dispose: () => sub.dispose() };
    },
    dispose: () => {
      if (disposed) return;
      disposed = true;
      subscription.dispose();
      editor.dispose();
      container.remove();
      textareaEl.style.display = '';
    },
  };
}

export const CodeMonaco = { load, create };
if (typeof window !== 'undefined') window.CodeMonaco = CodeMonaco;
