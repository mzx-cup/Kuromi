/**
 * 课程中心 (v2 重构)
 * 流程: 拉后端 /api/courses/subjects → 渲染概览 + 学科分组
 * 错误 / 空数据 / 加载 三态分离
 *
 * 模块:
 *   - 数据加载 (subjects)
 *   - 概览统计 (学科数 / 课程数 / 课时 / 平均进度)
 *   - 学科分组 + 课程卡片
 *   - 全局空状态 / 错误态 / 加载态
 *   - 编辑弹窗 (开关 / 移除 / 添加科目)
 *   - B 站导入弹窗 (链接 / 搜索 / 合集)
 */

(function () {
  'use strict';

  /* ===================== 状态 ===================== */
  var state = {
    subjects:  [],     // 后端返回的科目列表, [{id, name, slug, icon, visible, courses:[...]}]
    loading:   false,
    error:     null,
    editOpen:  false,
    importOpen: false,
    pendingImportSubjectId: null
  };

  /* ===================== 主题配色 (按 slug 映射) ===================== */
  var SUBJECT_ICON_SVG = {
    cs: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="3" width="20" height="14" rx="2"/><path d="M8 21h8M12 17v4" stroke-linecap="round"/></svg>',
    math: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="4" y1="9"  x2="20" y2="9"  stroke-linecap="round"/><line x1="4" y1="15" x2="20" y2="15" stroke-linecap="round"/><line x1="9"  y1="4" x2="9"  y2="20" stroke-linecap="round"/><line x1="15" y1="4" x2="15" y2="20" stroke-linecap="round"/></svg>',
    physics: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><ellipse cx="12" cy="12" rx="10" ry="4"/><line x1="12" y1="2" x2="12" y2="22"/></svg>',
    language: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M5 8h14M9 4v4M12 20l-3-8M15 12l-3 8" stroke-linecap="round" stroke-linejoin="round"/><circle cx="17" cy="14" r="3"/></svg>',
    default: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/></svg>'
  };

  function subjectIcon(slug) {
    return SUBJECT_ICON_SVG[slug] || SUBJECT_ICON_SVG.default;
  }

  function subjectSlug(slug) {
    return (slug && SUBJECT_ICON_SVG[slug]) ? slug : 'default';
  }

  function formatDuration(seconds) {
    if (!seconds || seconds < 0) return '--';
    var h = Math.floor(seconds / 3600);
    var m = Math.floor((seconds % 3600) / 60);
    if (h > 0) return h + 'h' + (m > 0 ? m + 'm' : '');
    if (m > 0) return m + ' 分钟';
    return Math.round(seconds) + ' 秒';
  }

  function formatLessons(n) {
    n = n || 0;
    return n + ' 课时';
  }

  function formatPercent(p) {
    p = Math.max(0, Math.min(100, Math.round(p || 0)));
    return p + '%';
  }

  function escapeHtml(s) {
    if (s == null) return '';
    return String(s).replace(/[&<>"']/g, function (c) {
      return ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c];
    });
  }

  /* ===================== 数据加载 ===================== */
  function loadSubjects() {
    state.loading = true;
    state.error = null;
    renderBody();

    fetch('/api/courses/subjects', { headers: { 'Accept': 'application/json' } })
      .then(function (r) {
        if (!r.ok) throw new Error('HTTP ' + r.status);
        return r.json();
      })
      .then(function (res) {
        if (!res || res.code !== 200) throw new Error(res && res.message || '加载失败');
        var list = (res.data || []).filter(function (s) { return s.visible !== false; });
        state.subjects = list.map(function (s) {
          return {
            id: s.id,
            name: s.name,
            slug: subjectSlug(s.slug),
            icon: s.icon,
            visible: s.visible !== false,
            courses: (s.courses || []).map(function (c) {
              return {
                id: c.id,
                title: c.title,
                description: c.description || '',
                bvid: c.bvid || '',
                playlistUrl: c.playlist_url || '',
                coverUrl: c.cover_url || '',
                totalLessons: c.total_lessons || 0,
                totalDuration: c.total_duration || 0,
                progress: c.progress || 0,
                visible: c.visible !== false
              };
            })
          };
        });
        state.loading = false;
        state.error = null;
        render();
      })
      .catch(function (err) {
        state.loading = false;
        state.error = err && err.message ? err.message : '网络错误';
        state.subjects = [];
        render();
      });
  }

  /* ===================== 概览统计 ===================== */
  function renderStats() {
    var subjects = state.subjects;
    var subjectCount = subjects.length;
    var courseCount = 0;
    var lessonCount = 0;
    var progressSum = 0;
    var courseWithProgress = 0;

    subjects.forEach(function (s) {
      s.courses.forEach(function (c) {
        if (c.visible === false) return;
        courseCount++;
        lessonCount += (c.totalLessons || 0);
        if (c.progress && c.progress > 0) {
          progressSum += c.progress;
          courseWithProgress++;
        }
      });
    });

    var avg = courseWithProgress > 0 ? Math.round(progressSum / courseWithProgress) : 0;

    var el;
    el = document.getElementById('cc-stat-subjects'); if (el) el.textContent = subjectCount;
    el = document.getElementById('cc-stat-courses');  if (el) el.textContent = courseCount;
    el = document.getElementById('cc-stat-lessons');  if (el) el.textContent = lessonCount;
    el = document.getElementById('cc-stat-progress'); if (el) el.textContent = formatPercent(avg);
  }

  /* ===================== 主体渲染 ===================== */
  function render() {
    renderStats();
    renderBody();
  }

  function renderBody() {
    var body = document.getElementById('cc-body');
    if (!body) return;

    if (state.loading) {
      body.innerHTML = '<div class="cc-loading"><div class="cc-spinner"></div><span>正在加载课程...</span></div>';
      return;
    }
    if (state.error) {
      body.innerHTML =
        '<div class="cc-error">' +
          '<div class="cc-error-icon"><svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16" stroke-linecap="round"/></svg></div>' +
          '<div class="cc-error-title">课程加载失败</div>' +
          '<p class="cc-error-desc">' + escapeHtml(state.error) + '</p>' +
          '<button class="cc-error-retry" type="button" data-retry>重试</button>' +
        '</div>';
      var retry = body.querySelector('[data-retry]');
      if (retry) retry.addEventListener('click', loadSubjects);
      return;
    }
    if (state.subjects.length === 0) {
      body.innerHTML = renderGlobalEmpty();
      var importBtn = body.querySelector('[data-open-import]');
      if (importBtn) importBtn.addEventListener('click', function () { openImportModal(null); });
      return;
    }

    var html = '';
    state.subjects.forEach(function (s) {
      html += renderSubject(s);
    });
    body.innerHTML = html;

    // 绑定: 课程卡片
    body.querySelectorAll('.cc-course').forEach(function (el) {
      el.addEventListener('click', function () {
        var courseId = el.getAttribute('data-course-id');
        var course = findCourse(courseId);
        if (course && course.bvid) {
          window.location.href = '/course-learn.html?courseId=' + encodeURIComponent(courseId);
        } else {
          showToast('该课程暂未关联视频', 'warning');
        }
      });
    });

    // 绑定: 学科级导入按钮
    body.querySelectorAll('[data-subject-import]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        openImportModal(btn.getAttribute('data-subject-import'));
      });
    });

    // 绑定: 学科内空状态导入按钮
    body.querySelectorAll('[data-subject-empty-import]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        openImportModal(btn.getAttribute('data-subject-empty-import'));
      });
    });
  }

  function renderGlobalEmpty() {
    return (
      '<div class="cc-empty">' +
        '<div class="cc-empty-illu">' +
          '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="5 3 19 12 5 21 5 3"/></svg>' +
        '</div>' +
        '<h3 class="cc-empty-title">还没有添加任何课程</h3>' +
        '<p class="cc-empty-desc">从 B 站导入视频或合集,系统会自动解析章节和进度,跟随式学习立刻开始。</p>' +
        '<button class="cc-empty-cta" type="button" data-open-import>' +
          '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">' +
            '<line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>' +
          '</svg>' +
          '导入 B 站课程' +
        '</button>' +
      '</div>'
    );
  }

  function renderSubject(subject) {
    var visibleCourses = subject.courses.filter(function (c) { return c.visible !== false; });
    var coursesHtml = '';

    if (visibleCourses.length === 0) {
      coursesHtml =
        '<div class="cc-subject-empty">' +
          '<div class="cc-subject-empty-icon">' +
            '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 5v14M5 12h14" stroke-linecap="round"/></svg>' +
          '</div>' +
          '<div class="cc-subject-empty-text">' +
            '<div class="cc-subject-empty-title">此科目下还没有课程</div>' +
            '<div class="cc-subject-empty-desc">从 B 站导入视频后会自动归类到本学科</div>' +
          '</div>' +
          '<button class="cc-subject-empty-btn" type="button" data-subject-empty-import="' + escapeHtml(subject.id) + '">' +
            '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>' +
            '导入课程' +
          '</button>' +
        '</div>';
    } else {
      coursesHtml = '<div class="cc-courses-grid">' +
        visibleCourses.map(function (c) { return renderCourse(c, subject.slug); }).join('') +
        '</div>';
    }

    return (
      '<section class="cc-subject">' +
        '<header class="cc-subject-head">' +
          '<div class="cc-subject-icon ' + escapeHtml(subject.slug) + '">' + subjectIcon(subject.slug) + '</div>' +
          '<div class="cc-subject-meta">' +
            '<h3 class="cc-subject-name">' + escapeHtml(subject.name) + '</h3>' +
            '<div class="cc-subject-desc">' + visibleCourses.length + ' 门课程 · ' +
              visibleCourses.reduce(function (s, c) { return s + (c.totalLessons || 0); }, 0) + ' 课时</div>' +
          '</div>' +
          '<span class="cc-subject-count">' + visibleCourses.length + '</span>' +
          '<button class="cc-subject-import" type="button" data-subject-import="' + escapeHtml(subject.id) + '" title="为此学科导入课程">' +
            '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>' +
            '导入' +
          '</button>' +
        '</header>' +
        coursesHtml +
      '</section>'
    );
  }

  function renderCourse(course, parentSlug) {
    var pct = Math.max(0, Math.min(100, Math.round(course.progress || 0)));
    var status;
    if (pct >= 100) status = 'complete';
    else if (pct > 0) status = 'continue';
    else status = 'start';

    var ctaText = status === 'complete' ? '再次学习' : status === 'continue' ? '继续学习' : '开始学习';
    var pillHtml = '';
    if (pct > 0) {
      var pillClass = pct >= 100 ? 'cc-course-progress-pill complete' : 'cc-course-progress-pill';
      pillHtml = '<span class="' + pillClass + '">' + pct + '%</span>';
    }

    var bvidShort = course.bvid ? course.bvid.replace(/^BV/, '') : '';
    var bvidHtml = bvidShort ? '<span class="cc-course-bvid">BV' + escapeHtml(bvidShort.slice(0, 6)) + '</span>' : '';

    var coverClass = 'cc-course-cover ' + escapeHtml(parentSlug);

    var descHtml = course.description
      ? '<p class="cc-course-desc">' + escapeHtml(course.description) + '</p>'
      : '';

    var ctaIcon = status === 'start'
      ? '<svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><polygon points="6 4 20 12 6 20 6 4"/></svg>'
      : '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><polyline points="9 18 15 12 9 6"/></svg>';

    return (
      '<div class="cc-course" data-course-id="' + escapeHtml(course.id) + '">' +
        '<div class="' + coverClass + '">' +
          bvidHtml +
          pillHtml +
          '<div class="cc-course-cover-icon">' + subjectIcon(parentSlug) + '</div>' +
        '</div>' +
        '<div class="cc-course-body">' +
          '<h4 class="cc-course-title">' + escapeHtml(course.title) + '</h4>' +
          descHtml +
          '<div class="cc-course-meta">' +
            '<span class="cc-course-meta-item">' +
              '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="5 3 19 12 5 21 5 3" fill="currentColor" stroke="none"/></svg>' +
              formatLessons(course.totalLessons) +
            '</span>' +
            (course.totalDuration ? '<span class="cc-course-meta-item">' +
              '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14" stroke-linecap="round"/></svg>' +
              formatDuration(course.totalDuration) +
            '</span>' : '') +
          '</div>' +
          (pct > 0 ? '<div class="cc-course-bar"><div class="cc-course-bar-fill" style="width:' + pct + '%"></div></div>' : '') +
          '<div class="cc-course-foot">' +
            '<span class="cc-course-cta ' + status + '">' + ctaText + ctaIcon + '</span>' +
          '</div>' +
        '</div>' +
      '</div>'
    );
  }

  function findCourse(courseId) {
    for (var i = 0; i < state.subjects.length; i++) {
      var list = state.subjects[i].courses;
      for (var j = 0; j < list.length; j++) {
        if (list[j].id === courseId) return list[j];
      }
    }
    return null;
  }

  /* ===================== 编辑弹窗 ===================== */
  function openEditModal() {
    var modal = document.getElementById('cc-edit-modal');
    if (!modal) return;
    renderEditBody();
    modal.hidden = false;
    state.editOpen = true;
  }

  function closeEditModal() {
    var modal = document.getElementById('cc-edit-modal');
    if (modal) modal.hidden = true;
    state.editOpen = false;
  }

  function renderEditBody() {
    var body = document.getElementById('cc-edit-body');
    if (!body) return;
    if (state.subjects.length === 0) {
      body.innerHTML = '<div class="cc-edit-empty">还没有科目,请先通过 B 站导入</div>';
      return;
    }
    var html = '';
    state.subjects.forEach(function (s) {
      var courseRows = '';
      if (s.courses.length > 0) {
        courseRows = '<div class="cc-edit-course-list">' +
          s.courses.map(function (c) {
            return (
              '<div class="cc-edit-course">' +
                '<button class="cc-toggle' + (c.visible !== false ? ' on' : '') + '" type="button" data-action="toggle-course" data-course-id="' + escapeHtml(c.id) + '" aria-label="切换显示"></button>' +
                '<span class="cc-edit-course-name" title="' + escapeHtml(c.title) + '">' + escapeHtml(c.title) + '</span>' +
                '<button class="cc-edit-course-remove" type="button" data-action="remove-course" data-course-id="' + escapeHtml(c.id) + '">移除</button>' +
              '</div>'
            );
          }).join('') +
          '</div>';
      }
      html += (
        '<div class="cc-edit-subject">' +
          '<div class="cc-edit-subject-head">' +
            '<button class="cc-toggle' + (s.visible !== false ? ' on' : '') + '" type="button" data-action="toggle-subject" data-subject-id="' + escapeHtml(s.id) + '" aria-label="切换显示"></button>' +
            '<span class="cc-edit-subject-name">' + escapeHtml(s.name) + '</span>' +
            '<div class="cc-edit-subject-actions">' +
              '<button class="cc-btn ghost" type="button" data-action="import-subject" data-subject-id="' + escapeHtml(s.id) + '">B 站导入</button>' +
            '</div>' +
          '</div>' +
          (courseRows || '<div class="cc-edit-empty">无课程</div>') +
        '</div>'
      );
    });
    body.innerHTML = html;
    bindEditEvents();
  }

  function bindEditEvents() {
    var body = document.getElementById('cc-edit-body');
    if (!body) return;
    body.querySelectorAll('[data-action="toggle-subject"]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var id = btn.getAttribute('data-subject-id');
        var s = findSubject(id);
        if (!s) return;
        s.visible = s.visible === false ? true : false;
        btn.classList.toggle('on', s.visible !== false);
        persistVisibility(s.id, s.visible);
      });
    });
    body.querySelectorAll('[data-action="toggle-course"]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var id = btn.getAttribute('data-course-id');
        var c = findCourse(id);
        if (!c) return;
        c.visible = c.visible === false ? true : false;
        btn.classList.toggle('on', c.visible !== false);
        persistVisibility(null, null, c.id, c.visible);
      });
    });
    body.querySelectorAll('[data-action="remove-course"]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var id = btn.getAttribute('data-course-id');
        if (!confirm('确定要移除该课程吗?')) return;
        removeCourse(id).then(function () {
          renderEditBody();
          render();
        });
      });
    });
    body.querySelectorAll('[data-action="import-subject"]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var id = btn.getAttribute('data-subject-id');
        closeEditModal();
        openImportModal(id);
      });
    });
  }

  function findSubject(id) {
    for (var i = 0; i < state.subjects.length; i++) {
      if (state.subjects[i].id === id) return state.subjects[i];
    }
    return null;
  }

  function removeCourse(courseId) {
    return fetch('/api/courses/courses/' + encodeURIComponent(courseId), { method: 'DELETE' })
      .then(function (r) { return r.json(); })
      .then(function (res) {
        if (res && res.code === 200) {
          state.subjects.forEach(function (s) {
            s.courses = s.courses.filter(function (c) { return c.id !== courseId; });
          });
          showToast('已移除课程', 'success');
        } else {
          showToast((res && res.message) || '移除失败', 'error');
        }
      })
      .catch(function () {
        showToast('网络错误', 'error');
      });
  }

  function persistVisibility(subjectId, subjectVisible, courseId, courseVisible) {
    if (subjectId) {
      fetch('/api/courses/subjects/' + encodeURIComponent(subjectId), {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ visible: subjectVisible })
      })
        .then(function (r) { return r.json(); })
        .then(function (res) {
          if (!res || res.code !== 200) showToast('状态保存失败', 'warning');
        })
        .catch(function () { showToast('网络错误', 'error'); });
    }
    if (courseId) {
      fetch('/api/courses/courses/' + encodeURIComponent(courseId), {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ visible: courseVisible })
      })
        .then(function (r) { return r.json(); })
        .then(function (res) {
          if (!res || res.code !== 200) showToast('状态保存失败', 'warning');
        })
        .catch(function () { showToast('网络错误', 'error'); });
    }
  }

  function addSubject() {
    var name = prompt('请输入新科目名称:');
    if (!name || !name.trim()) return;
    var slug = 'subject-' + Date.now();
    fetch('/api/courses/subjects', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: name.trim(), slug: slug, visible: true })
    })
      .then(function (r) { return r.json(); })
      .then(function (res) {
        if (res && res.code === 200 && res.data) {
          showToast('科目已添加', 'success');
          loadSubjects();
        } else {
          showToast((res && res.message) || '添加失败', 'error');
        }
      })
      .catch(function () { showToast('网络错误', 'error'); });
  }

  /* ===================== B 站导入弹窗 ===================== */
  function openImportModal(subjectId) {
    state.pendingImportSubjectId = subjectId || null;
    var modal = document.getElementById('cc-import-modal');
    if (!modal) return;
    modal.hidden = false;
    state.importOpen = true;
    switchImportTab('link');
  }

  function closeImportModal() {
    var modal = document.getElementById('cc-import-modal');
    if (modal) modal.hidden = true;
    state.importOpen = false;
  }

  function switchImportTab(name) {
    var modal = document.getElementById('cc-import-modal');
    if (!modal) return;
    modal.querySelectorAll('.cc-tab').forEach(function (t) {
      t.classList.toggle('active', t.getAttribute('data-tab') === name);
    });
    modal.querySelectorAll('.cc-tab-panel').forEach(function (p) {
      var match = p.getAttribute('data-tab-panel') === name;
      p.classList.toggle('active', match);
      p.hidden = !match;
    });
  }

  function bindImportEvents() {
    var modal = document.getElementById('cc-import-modal');
    if (!modal) return;

    // Tabs
    modal.querySelectorAll('.cc-tab').forEach(function (t) {
      t.addEventListener('click', function () { switchImportTab(t.getAttribute('data-tab')); });
    });

    // 链接解析
    var linkBtn = document.getElementById('cc-link-parse');
    if (linkBtn) {
      linkBtn.addEventListener('click', function () {
        var ta = document.getElementById('cc-link-text');
        var urls = (ta && ta.value || '').split(/\n+/).map(function (s) { return s.trim(); }).filter(Boolean);
        if (urls.length === 0) { showToast('请粘贴至少一个链接', 'warning'); return; }
        importVideos(urls, 'cc-link-results');
      });
    }

    // 搜索
    var searchBtn = document.getElementById('cc-search-btn');
    if (searchBtn) {
      searchBtn.addEventListener('click', function () {
        var input = document.getElementById('cc-search-input');
        var kw = input && input.value.trim();
        if (!kw) { showToast('请输入关键词', 'warning'); return; }
        searchVideos(kw, 'cc-search-results');
      });
    }

    // 合集解析
    var plBtn = document.getElementById('cc-playlist-parse');
    if (plBtn) {
      plBtn.addEventListener('click', function () {
        var input = document.getElementById('cc-playlist-url');
        var url = input && input.value.trim();
        if (!url) { showToast('请粘贴合集链接', 'warning'); return; }
        importPlaylist(url, 'cc-playlist-results');
      });
    }
  }

  function importVideos(urls, resultElId) {
    var resultEl = document.getElementById(resultElId);
    if (!resultEl) return;
    resultEl.hidden = false;
    resultEl.innerHTML = '<div class="cc-loading"><div class="cc-spinner"></div><span>正在解析...</span></div>';

    fetch('/api/bilibili/import', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ bvids: urls.map(extractBvid).filter(Boolean), autoGenerate: true })
    })
      .then(function (r) { return r.json(); })
      .then(function (res) {
        if (res && res.code === 200 && res.data && res.data.results) {
          renderImportResults(res.data.results, resultEl);
        } else {
          resultEl.innerHTML = '<div class="cc-error"><div class="cc-error-desc">解析失败: ' + escapeHtml((res && res.message) || '未知错误') + '</div></div>';
        }
      })
      .catch(function () {
        resultEl.innerHTML = '<div class="cc-error"><div class="cc-error-desc">网络错误</div></div>';
      });
  }

  function searchVideos(keyword, resultElId) {
    var resultEl = document.getElementById(resultElId);
    if (!resultEl) return;
    resultEl.hidden = false;
    resultEl.innerHTML = '<div class="cc-loading"><div class="cc-spinner"></div><span>正在搜索...</span></div>';

    fetch('/api/bilibili/search', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ keyword: keyword, page: 1, pageSize: 10 })
    })
      .then(function (r) { return r.json(); })
      .then(function (res) {
        if (res && res.code === 200) {
          var items = (res.data && (res.data.items || res.data.results || res.data)) || [];
          renderImportResults(items, resultEl);
        } else {
          resultEl.innerHTML = '<div class="cc-error"><div class="cc-error-desc">搜索失败</div></div>';
        }
      })
      .catch(function () {
        resultEl.innerHTML = '<div class="cc-error"><div class="cc-error-desc">网络错误</div></div>';
      });
  }

  function importPlaylist(url, resultElId) {
    var resultEl = document.getElementById(resultElId);
    if (!resultEl) return;
    resultEl.hidden = false;
    resultEl.innerHTML = '<div class="cc-loading"><div class="cc-spinner"></div><span>正在解析合集...</span></div>';

    fetch('/api/bilibili/playlist', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url: url })
    })
      .then(function (r) { return r.json(); })
      .then(function (res) {
        if (res && res.code === 200) {
          var items = (res.data && (res.data.items || res.data)) || [];
          renderImportResults(items, resultEl);
        } else {
          resultEl.innerHTML = '<div class="cc-error"><div class="cc-error-desc">合集解析失败</div></div>';
        }
      })
      .catch(function () {
        resultEl.innerHTML = '<div class="cc-error"><div class="cc-error-desc">网络错误</div></div>';
      });
  }

  function renderImportResults(items, container) {
    if (!items || items.length === 0) {
      container.innerHTML = '<div class="cc-edit-empty">未找到匹配的视频</div>';
      return;
    }
    var html = '';
    items.forEach(function (v) {
      var title = v.title || v.partTitle || '(无标题)';
      var bvid = v.bvid || v.bvId || v.BVId || '';
      var cover = v.coverUrl || v.cover || v.pic || '';
      var meta = [];
      if (v.authorName) meta.push(v.authorName);
      if (v.duration) meta.push(formatDuration(v.duration));
      if (v.success === false) meta.push('解析失败');

      html +=
        '<div class="cc-video">' +
          '<input type="checkbox" class="cc-video-check" ' + (v.success === false ? 'disabled' : '') + ' data-bvid="' + escapeHtml(bvid) + '">' +
          '<div class="cc-video-cover">' +
            (cover
              ? '<img src="' + escapeHtml(cover) + '" alt="" loading="lazy" onerror="this.style.display=\'none\'">'
              : '<div class="cc-video-cover-placeholder"></div>') +
          '</div>' +
          '<div class="cc-video-info">' +
            '<div class="cc-video-title">' + escapeHtml(title) + '</div>' +
            '<div class="cc-video-meta">' + escapeHtml(meta.filter(Boolean).join(' · ')) + '</div>' +
          '</div>' +
        '</div>';
    });
    html +=
      '<button class="cc-btn primary" type="button" data-confirm-import style="margin-top:8px">' +
        '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 6L9 17l-5-5" stroke-linecap="round" stroke-linejoin="round"/></svg>' +
        '导入选中的视频' +
      '</button>';
    container.innerHTML = html;

    var confirmBtn = container.querySelector('[data-confirm-import]');
    if (confirmBtn) {
      confirmBtn.addEventListener('click', function () {
        var checked = container.querySelectorAll('.cc-video-check:checked');
        var bvids = [];
        checked.forEach(function (c) { if (c.getAttribute('data-bvid')) bvids.push(c.getAttribute('data-bvid')); });
        if (bvids.length === 0) { showToast('请勾选要导入的视频', 'warning'); return; }
        confirmImport(bvids);
      });
    }
  }

  function confirmImport(bvids) {
    var subjectId = state.pendingImportSubjectId;
    var body = {
      bvids: bvids,
      autoGenerate: !subjectId  // 未指定学科时由后端归类
    };
    if (subjectId) body.subjectId = subjectId;

    fetch('/api/bilibili/import-playlist', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    })
      .then(function (r) { return r.json(); })
      .then(function (res) {
        if (res && res.code === 200) {
          showToast('已导入 ' + bvids.length + ' 个视频', 'success');
          closeImportModal();
          loadSubjects();
        } else {
          showToast((res && res.message) || '导入失败', 'error');
        }
      })
      .catch(function () { showToast('网络错误', 'error'); });
  }

  function extractBvid(url) {
    if (!url) return '';
    var m = String(url).match(/BV[a-zA-Z0-9]{10}/);
    return m ? m[0] : '';
  }

  /* ===================== 事件绑定 ===================== */
  function bindGlobalEvents() {
    var editBtn = document.getElementById('cc-edit-btn');
    if (editBtn) editBtn.addEventListener('click', openEditModal);

    var quickImport = document.getElementById('cc-quick-import');
    if (quickImport) quickImport.addEventListener('click', function () { openImportModal(null); });

    var addBtn = document.getElementById('cc-add-subject');
    if (addBtn) addBtn.addEventListener('click', addSubject);

    var doneBtn = document.getElementById('cc-edit-done');
    if (doneBtn) doneBtn.addEventListener('click', function () {
      closeEditModal();
      render();
    });

    // Modal 关闭
    document.querySelectorAll('.cc-modal').forEach(function (m) {
      m.querySelectorAll('[data-close]').forEach(function (el) {
        el.addEventListener('click', function () {
          if (m.id === 'cc-edit-modal')   closeEditModal();
          if (m.id === 'cc-import-modal') closeImportModal();
        });
      });
    });

    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') {
        if (state.editOpen)   closeEditModal();
        if (state.importOpen) closeImportModal();
      }
    });

    bindImportEvents();
  }

  /* ===================== Toast ===================== */
  function showToast(message, type) {
    var container = document.getElementById('toast-container');
    if (!container) return;
    type = type || 'info';
    var toast = document.createElement('div');
    toast.className = 'toast ' + type;
    toast.textContent = message;
    container.appendChild(toast);
    setTimeout(function () {
      toast.style.opacity = '0';
      toast.style.transform = 'translateX(40px)';
      setTimeout(function () { toast.remove(); }, 300);
    }, 3000);
  }

  /* ===================== 启动 ===================== */
  function init() {
    bindGlobalEvents();
    loadSubjects();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  /* ===================== 暴露 ===================== */
  window.CoursesCenter = {
    reload: loadSubjects,
    getData: function () { return state.subjects; },
    openEdit: openEditModal,
    openImport: openImportModal
  };
})();
