/**
 * 全局命令搜索 — ⌘K 快捷键
 * Phase 4: Command palette with Fuse.js fuzzy search
 * 依赖: Fuse.js (CDN)
 */
(function() {
  'use strict';

  let overlay = null;
  let input = null;
  let resultsEl = null;
  let fuse = null;
  let searchIndex = [];

  // ===== 索引构建 =====
  function buildIndex() {
    searchIndex = [
      // 功能入口
      { type: '功能', label: 'AI 问答', desc: '与AI智能对话、苏格拉底教学、代码工坊', route: '/index.html', keywords: 'chat ai socratic code' },
      { type: '功能', label: '我的课程', desc: '查看已生成课程、学习进度、学习日历', route: '/my-courses.html', keywords: 'courses progress calendar' },
      { type: '功能', label: '学习数据', desc: '学习分析大屏、能力雷达、知识图谱', route: '/data-dashboard.html', keywords: 'data analytics dashboard' },
      { type: '功能', label: '个人中心', desc: '个人资料、成就展示、学习生态、设置', route: '/personal.html', keywords: 'profile settings achievements' },
      { type: '功能', label: '代码工坊', desc: 'Python代码编辑与AI批阅', route: '/code.html', keywords: 'code python editor' },
      { type: '功能', label: '苏格拉底教学', desc: 'AI苏格拉底式提问教学', route: '/socratic-ai.html', keywords: 'socratic teaching' },
      { type: '功能', label: '全息视界', desc: '视频学习播放器', route: '/video-player.html', keywords: 'video player' },

      // 课程（从 localStorage 读取）
      ...loadCourseIndex(),
    ];

    fuse = new Fuse(searchIndex, {
      keys: ['label', 'desc', 'keywords'],
      threshold: 0.4,
      includeScore: true,
    });
  }

  function loadCourseIndex() {
    try {
      const courses = JSON.parse(localStorage.getItem('starlearn_courses') || '[]');
      return courses.map(c => ({
        type: '课程',
        label: c.name || c.title || '未命名课程',
        desc: `进度 ${c.progress || 0}%`,
        route: `/course-detail.html?id=${c.id}`,
        keywords: c.subject || '',
      }));
    } catch (e) {
      return [];
    }
  }

  // ===== UI 创建 =====
  function createOverlay() {
    if (overlay) return;

    overlay = document.createElement('div');
    overlay.className = 'cmd-overlay';
    overlay.innerHTML = `
      <div class="cmd-panel">
        <div class="cmd-header">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
          <input class="cmd-input" id="cmd-input" type="text" placeholder="搜索课程、功能或输入指令..." autocomplete="off" />
          <kbd class="cmd-kbd">ESC</kbd>
        </div>
        <div class="cmd-results" id="cmd-results"></div>
        <div class="cmd-footer">
          <span><kbd>↑↓</kbd> 导航</span>
          <span><kbd>Enter</kbd> 打开</span>
          <span><kbd>Esc</kbd> 关闭</span>
        </div>
      </div>
    `;
    document.body.appendChild(overlay);

    input = document.getElementById('cmd-input');
    resultsEl = document.getElementById('cmd-results');

    // 事件
    overlay.addEventListener('click', (e) => {
      if (e.target === overlay) close();
    });
    input.addEventListener('input', handleInput);
    input.addEventListener('keydown', handleKeydown);
  }

  function open() {
    buildIndex();
    createOverlay();
    overlay.classList.add('visible');
    input.value = '';
    input.focus();
    renderResults(searchIndex.slice(0, 5));  // 默认显示前5个
  }

  function close() {
    if (overlay) overlay.classList.remove('visible');
    if (input) input.value = '';
    if (resultsEl) resultsEl.innerHTML = '';
  }

  // ===== 搜索 =====
  function handleInput() {
    const query = input.value.trim();
    if (!query) {
      renderResults(searchIndex.slice(0, 5));
      return;
    }
    const results = fuse.search(query).slice(0, 8);
    renderResults(results.map(r => r.item));
  }

  function renderResults(items) {
    if (!resultsEl) return;
    if (items.length === 0) {
      resultsEl.innerHTML = '<div class="cmd-empty">没有找到匹配结果</div>';
      return;
    }

    const grouped = {};
    items.forEach(item => {
      if (!grouped[item.type]) grouped[item.type] = [];
      grouped[item.type].push(item);
    });

    let html = '';
    for (const [group, entries] of Object.entries(grouped)) {
      html += `<div class="cmd-group-title">${group}</div>`;
      entries.forEach((item, i) => {
        html += `
          <div class="cmd-result-item" data-route="${item.route}" data-index="${i}">
            <div class="cmd-result-label">${item.label}</div>
            <div class="cmd-result-desc">${item.desc}</div>
            ${item.type === '功能' ? `<div class="cmd-result-arrow">→ ${item.label}</div>` : ''}
          </div>`;
      });
    }
    resultsEl.innerHTML = html;

    // 点击事件
    resultsEl.querySelectorAll('.cmd-result-item').forEach(el => {
      el.addEventListener('click', () => {
        const route = el.dataset.route;
        if (route) {
          window.location.href = route;
          close();
        }
      });
    });
  }

  function handleKeydown(e) {
    if (e.key === 'Escape') {
      close();
    } else if (e.key === 'Enter') {
      const first = resultsEl?.querySelector('.cmd-result-item');
      if (first) {
        window.location.href = first.dataset.route;
        close();
      }
    } else if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
      e.preventDefault();
      const items = resultsEl?.querySelectorAll('.cmd-result-item');
      if (!items || items.length === 0) return;
      const current = resultsEl.querySelector('.cmd-result-item.active');
      let idx = -1;
      if (current) {
        idx = Array.from(items).indexOf(current);
        current.classList.remove('active');
      }
      if (e.key === 'ArrowDown') idx = (idx + 1) % items.length;
      else idx = (idx - 1 + items.length) % items.length;
      items[idx].classList.add('active');
      items[idx].scrollIntoView({ block: 'nearest' });
    }
  }

  // ===== 快捷键 =====
  document.addEventListener('keydown', (e) => {
    if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
      e.preventDefault();
      open();
    }
  });

  // ===== 暴露 API =====
  window.CommandSearch = { open, close, buildIndex };

  console.log('[CommandSearch] ⌘K ready — Fuse.js indexed', searchIndex.length, 'entries');
})();
