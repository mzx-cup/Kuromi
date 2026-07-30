/**
 * Course Learn Page (v2 重构)
 * 跟随式 5+1 步学习流程: 观看 → 字幕 → 笔记 → 概念 → 导图 → 练习
 *
 * 模块:
 *   - 章节树渲染与切换
 *   - B 站视频播放 (iframe embed)
 *   - 字幕加载 / 渲染 / 点击跳转 (B 站 API, 无则空状态)
 *   - AI 讲义 / 关键概念 / 思维导图 / 课后练习 — 由后端返回, 无则空状态
 *   - 笔记自动保存 (localStorage)
 *   - 思维导图 SVG 渲染 (递归布局, 支持缩放拖动)
 *   - 课后练习 (选择/判断/填空, 自动判分)
 *   - 步骤引导 (stepper) 进度同步
 *   - 上一节 / 下一节 / 章节完成状态
 */
(function () {
  'use strict';

  /* ===================== 常量 ===================== */
  var STORAGE_KEY     = 'starlearn_courses_data';
  var NOTES_KEY       = 'starlearn_course_notes';
  var PROGRESS_KEY    = 'starlearn_course_progress';
  var STEP_PROGRESS_KEY = 'starlearn_course_step_progress';
  var EXERCISE_KEY    = 'starlearn_course_exercise_state';

  var STEP_ORDER = ['watch', 'subtitles', 'notes', 'concepts', 'mindmap', 'exercises'];
  var STEP_NAMES = {
    watch:     '观看视频',
    subtitles: '阅读字幕',
    notes:     '记录笔记',
    concepts:  '理解概念',
    mindmap:   '梳理导图',
    exercises: '完成练习'
  };

  /* ===================== 状态 ===================== */
  var courseId          = null;
  var course            = null;
  var chapters          = [];
  var currentChapterIdx = -1;
  var currentSubIdx     = -1;
  var subtitleData      = [];
  var sidebarCollapsed  = false;
  var currentStep       = 'watch';
  var mindmapZoom       = 1;
  var mindmapOffsetX    = 0;
  var mindmapOffsetY    = 0;
  var isDraggingMM      = false;
  var dragStartX        = 0;
  var dragStartY        = 0;
  var currentMindMap    = null;  // 当前 mindmap 数据, 用于切换步骤时重渲染
  var currentExercises  = [];    // 当前练习, 用于重置答卷时重渲染

  /* ===================== AI 视频生成状态 ===================== */
  var aiVideoState = { taskId: null, status: null, pollTimer: null };

  /* ===================== 入口 ===================== */
  function init() {
    var params = new URLSearchParams(window.location.search);
    courseId = params.get('courseId');

    if (!courseId) {
      showToast('未指定课程', 'error');
      return;
    }

    loadCourse();
    if (!course) {
      course = {
        id: courseId,
        title: '加载中...',
        bvid: extractBvidFromCourseId(courseId),
        totalLessons: 1,
        totalDuration: 0,
        progress: 0
      };
    }

    document.getElementById('cl-course-title').textContent = course.title;
    document.getElementById('cl-welcome-title-text').textContent = course.title;
    buildChapterTree();
    loadNotes();
    loadExerciseState();
    bindEvents();

    // Try backend for richer data
    loadCourseFromBackend();
  }

  function extractBvidFromCourseId(id) {
    var m = (id || '').match(/BV[a-zA-Z0-9]{10}/);
    return m ? m[0] : '';
  }

  /* ===================== 课程与章节 ===================== */
  function loadCourse() {
    try {
      var data = JSON.parse(localStorage.getItem(STORAGE_KEY));
      if (!data || !data.subjects) return;
      for (var i = 0; i < data.subjects.length; i++) {
        var list = data.subjects[i].courses || [];
        for (var j = 0; j < list.length; j++) {
          if (list[j].id === courseId) {
            course = list[j];
            return;
          }
        }
      }
    } catch (e) { /* ignore */ }
  }

  function loadCourseFromBackend() {
    fetch('/api/courses/courses/' + courseId)
      .then(function (r) { return r.json(); })
      .then(function (res) {
        if (res && res.code === 200 && res.data) {
          var d = res.data;
          course = {
            id: d.id,
            title: d.title,
            bvid: d.bvid,
            totalLessons: d.total_lessons,
            totalDuration: d.total_duration,
            progress: d.progress,
            coverUrl: d.cover_url
          };
          chapters = (d.chapters || []).map(function (ch) {
            return {
              id: ch.id,
              title: ch.title,
              expanded: true,
              children: (ch.subchapters || []).map(function (sc) {
                return {
                  id: sc.id,
                  title: sc.title,
                  duration: sc.duration,
                  cid: sc.cid,
                  page: sc.page,
                  bvid: sc.bvid,
                  completed: !!sc.completed
                };
              })
            };
          });
          document.getElementById('cl-course-title').textContent = course.title;
          document.getElementById('cl-welcome-title-text').textContent = course.title;

          // 如果课程有 bvid 但子章节 cid 为空（seeder 导入的课程），
          // 从 B站 API 补全章节结构
          if (course.bvid) {
            var hasEmptyCids = chapters.every(function (ch) {
              return ch.children.every(function (sc) { return !sc.cid; });
            });
            if (hasEmptyCids) {
              loadBilibiliChapters(course.bvid);
              return; // loadBilibiliChapters 内部会调用 renderChapterTree + selectChapter
            }
          }

          renderChapterTree();
          var start = findStartIndex();
          if (chapters.length > 0) selectChapter(start, 0);
        }
      })
      .catch(function () { /* silent fail */ });
  }

  function buildChapterTree() {
    chapters = [];
    if (!course) return;

    if (course.bvid) {
      loadBilibiliChapters(course.bvid);
    } else {
      // 占位: 等待后端
      chapters = [{
        id: 'ch-1',
        title: course.title || '课程内容',
        expanded: true,
        children: [{
          id: 'sub-1',
          title: '加载中...',
          duration: 0, cid: 0, page: 1, bvid: '', completed: false
        }]
      }];
      renderChapterTree();
    }
  }

  function loadBilibiliChapters(bvid) {
    var tree = document.getElementById('cl-chapter-tree');
    tree.innerHTML = '<div class="cl-tree-loading"><div class="cl-spinner"></div><span>正在加载课程目录...</span></div>';

    fetch('/api/bilibili/parse', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url: 'https://www.bilibili.com/video/' + bvid })
    })
      .then(function (r) { return r.json(); })
      .then(function (res) {
        if (res && res.code === 200 && res.data) {
          var videoData = res.data;
          var pages = videoData.pages || [];

          if (pages.length > 0) {
            chapters = [{
              id: 'ch-1',
              title: videoData.title || '课程内容',
              expanded: true,
              children: pages.map(function (p) {
                return {
                  id: 'sub-' + p.page,
                  title: p.partTitle || ('第' + p.page + '讲'),
                  duration: p.duration || 0,
                  cid: p.cid,
                  page: p.page,
                  bvid: bvid,
                  completed: false
                };
              })
            }];
            if (chapters[0].children.length > 0) {
              course.totalLessons = chapters[0].children.length;
              course.totalDuration = chapters[0].children.reduce(function (s, c) { return s + (c.duration || 0); }, 0);
            }
          } else {
            chapters = [{
              id: 'ch-1',
              title: videoData.title || '课程内容',
              expanded: true,
              children: [{
                id: 'sub-1',
                title: videoData.title || '视频',
                duration: videoData.duration || 0,
                cid: videoData.cid, page: 1, bvid: bvid, completed: false
              }]
            }];
            course.totalLessons = 1;
            course.totalDuration = videoData.duration || 0;
          }
          saveCourseData();
        } else {
          throw new Error('parse failed');
        }

        renderChapterTree();
        if (chapters.length > 0 && chapters[0].children.length > 0) {
          selectChapter(0, 0);
        }
      })
      .catch(function () {
        // 兜底章节
        chapters = [{
          id: 'ch-1',
          title: course.title || '课程内容',
          expanded: true,
          children: [{
            id: 'sub-1',
            title: course.title || '视频',
            duration: course.totalDuration || 0,
            cid: 0, page: 1, bvid: bvid, completed: false
          }]
        }];
        course.totalLessons = 1;
        renderChapterTree();
        if (chapters[0].children.length > 0) selectChapter(0, 0);
      });
  }

  function renderChapterTree() {
    var container = document.getElementById('cl-chapter-tree');
    if (chapters.length === 0) {
      container.innerHTML = '<div class="cl-tree-loading">暂无课程内容</div>';
      return;
    }

    var html = '';
    for (var i = 0; i < chapters.length; i++) {
      var ch = chapters[i];
      var expanded = ch.expanded !== false;
      html += '<div class="cl-chapter-node">';
      html += '<div class="cl-chapter-header' + (currentChapterIdx === i ? ' active' : '') + '" data-chapter="' + i + '">';
      html += '<svg class="cl-chapter-arrow' + (expanded ? ' expanded' : '') + '" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="9 18 15 12 9 6"/></svg>';
      html += '<div class="cl-chapter-icon"><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="5 3 19 12 5 21 5 3"/></svg></div>';
      html += '<div class="cl-chapter-info">';
      html += '<div class="cl-chapter-name">' + escapeHtml(ch.title) + '</div>';
      html += '<div class="cl-chapter-meta">' + (ch.children ? ch.children.length : 0) + ' 个视频</div>';
      html += '</div></div>';

      if (ch.children && ch.children.length > 0) {
        html += '<div class="cl-chapter-children' + (expanded ? '' : ' collapsed') + '" data-chapter-children="' + i + '">';
        for (var j = 0; j < ch.children.length; j++) {
          var sub = ch.children[j];
          var isActive = currentChapterIdx === i && currentSubIdx === j;
          html += '<div class="cl-subchapter' + (isActive ? ' active' : '') + (sub.completed ? ' completed' : '') + '" data-chapter="' + i + '" data-sub="' + j + '">';
          html += '<span class="cl-subchapter-dot"></span>';
          html += '<span class="cl-subchapter-name">' + escapeHtml(sub.title) + '</span>';
          html += '<span class="cl-subchapter-check">✓</span>';
          html += '<span class="cl-subchapter-dur">' + formatDuration(sub.duration) + '</span>';
          html += '</div>';
        }
        html += '</div>';
      }
      html += '</div>';
    }
    container.innerHTML = html;

    // 绑定事件
    container.querySelectorAll('.cl-chapter-header').forEach(function (h) {
      h.addEventListener('click', function () {
        toggleChapter(parseInt(h.getAttribute('data-chapter')));
      });
    });
    container.querySelectorAll('.cl-subchapter').forEach(function (s) {
      s.addEventListener('click', function (e) {
        e.stopPropagation();
        var ci = parseInt(s.getAttribute('data-chapter'));
        var si = parseInt(s.getAttribute('data-sub'));
        selectChapter(ci, si);
      });
    });

    // 自适应高度
    container.querySelectorAll('.cl-chapter-children').forEach(function (el) {
      if (!el.classList.contains('collapsed')) {
        el.style.maxHeight = el.scrollHeight + 'px';
      } else {
        el.style.maxHeight = '0px';
      }
    });
  }

  function toggleChapter(idx) {
    chapters[idx].expanded = !chapters[idx].expanded;
    var c = document.querySelector('[data-chapter-children="' + idx + '"]');
    if (c) {
      if (chapters[idx].expanded) {
        c.classList.remove('collapsed');
        c.style.maxHeight = c.scrollHeight + 'px';
      } else {
        c.style.maxHeight = c.scrollHeight + 'px';
        requestAnimationFrame(function () {
          c.classList.add('collapsed');
          c.style.maxHeight = '0px';
        });
      }
    }
    var h = document.querySelector('[data-chapter="' + idx + '"].cl-chapter-header');
    if (h) {
      var arrow = h.querySelector('.cl-chapter-arrow');
      if (arrow) arrow.classList.toggle('expanded', chapters[idx].expanded);
    }
  }

  /* ===================== 章节切换 ===================== */
  function selectChapter(chIdx, subIdx) {
    if (chIdx >= chapters.length) return;
    var ch = chapters[chIdx];
    if (!ch.children || subIdx >= ch.children.length) return;

    currentChapterIdx = chIdx;
    currentSubIdx = subIdx;
    var sub = ch.children[subIdx];

    loadVideo(sub.bvid, sub.page);
    loadSubtitles(sub.bvid);
    loadLearningContent(sub);

    // 重置 stepper 到第一步
    setStep('watch', false);
    renderChapterTree();
    updateNavigation();
  }

  function loadVideo(bvid, page) {
    var player = document.getElementById('cl-bilibili-player');
    var placeholder = document.getElementById('cl-player-placeholder');
    if (!bvid) {
      player.style.display = 'none';
      placeholder.style.display = 'flex';
      return;
    }
    var url = 'https://player.bilibili.com/player.html?bvid=' + bvid + '&page=' + (page || 1) + '&high_quality=1&autoplay=1';
    player.src = url;
    player.style.display = 'block';
    placeholder.style.display = 'none';
  }

  /* ===================== 字幕 ===================== */
  function loadSubtitles(bvid) {
    var container = document.getElementById('cl-subtitle-container');
    container.innerHTML = '<div class="cl-subtitle-empty">加载字幕中...</div>';

    if (!bvid) {
      renderSubtitles([]);
      return;
    }

    // 优先复用 B 站字幕 (成功则保留; 失败/为空依然请求 AI 内容以保证"非空")
    fetch('/api/bilibili/subtitles', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ bvid: bvid })
    })
      .then(function (r) { return r.json(); })
      .then(function (res) {
        if (res && res.code === 200 && res.data && res.data.length > 0) {
          subtitleData = res.data[0].content || [];
        } else {
          subtitleData = [];
        }
        renderSubtitles(subtitleData);
        // 触发 AI 讲义侧栏同步: 后端会发现无字幕, 用课程标题也能凑一份讲义
        syncTranscriptFallback(bvid);
      })
      .catch(function () {
        subtitleData = [];
        renderSubtitles(subtitleData);
        syncTranscriptFallback(bvid);
      });
  }

  /**
   * 当 B 站字幕为空时, 主动重抓一次内容端点, 让后端用课程标题 + 章节标题生成
   * "占位讲义", 避免讲解 tab 完全空白. 拿到的内容写入 transcript 面板, 但不会
   * 覆盖已有真实内容.
   */
  function syncTranscriptFallback(bvid) {
    var transcriptEl = document.getElementById('cl-transcript-content');
    if (!transcriptEl) return;
    // 已经有讲义了 (transcript 节点不含 -empty) 就不再请求
    if (transcriptEl.querySelector('h4, p, ol, ul') &&
        !transcriptEl.querySelector('.cl-transcript-empty')) {
      return;
    }
    // 用 bvid 找到当前选中的 sub.id, 直接重抓
    if (!currentSubId()) return;
    fetch('/api/courses/courses/' + encodeURIComponent(courseId) +
          '/subchapters/' + encodeURIComponent(currentSubId()) + '/content')
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (res) {
        if (!res || !res.data) return;
        var d = res.data;
        if (d.transcript) {
          var note = d.note
            ? '<div class="cl-transcript-empty" style="margin-bottom:10px">' + escapeHtml(d.note) + '</div>'
            : '';
          transcriptEl.innerHTML = note + d.transcript;
        }
        // 概念 / 练习 / 导图也顺手补齐
        if ((d.concepts || []).length) renderConcepts(d.concepts);
        if ((d.exercises || []).length) {
          currentExercises = d.exercises;
          renderExercises(currentExercises);
        }
        if (d.mindMap) {
          currentMindMap = d.mindMap;
          var mmPanel = document.querySelector('.cl-step-panel[data-panel="mindmap"]');
          if (mmPanel && mmPanel.classList.contains('active')) {
            requestAnimationFrame(function () { renderMindMap(currentMindMap); });
          }
        }
      })
      .catch(function () { /* ignore */ });
  }

  function renderSubtitles(list) {
    subtitleData = list || [];
    var container = document.getElementById('cl-subtitle-container');
    if (subtitleData.length === 0) {
      container.innerHTML = '<div class="cl-subtitle-empty">该视频暂无字幕</div>';
      return;
    }
    var html = '';
    for (var i = 0; i < subtitleData.length; i++) {
      var s = subtitleData[i];
      html += '<div class="cl-subtitle-line" data-time="' + s.from + '" data-index="' + i + '">';
      html += '<span class="cl-subtitle-time">' + formatTime(s.from) + '</span>';
      html += '<span class="cl-subtitle-text">' + escapeHtml(s.content) + '</span>';
      html += '</div>';
    }
    container.innerHTML = html;

    container.querySelectorAll('.cl-subtitle-line').forEach(function (line) {
      line.addEventListener('click', function () {
        var t = parseFloat(line.getAttribute('data-time'));
        seekTo(t);
        container.querySelectorAll('.cl-subtitle-line').forEach(function (l) { l.classList.remove('active'); });
        line.classList.add('active');
        markStepCompleted('subtitles');
      });
    });
  }

  function seekTo(seconds) {
    var player = document.getElementById('cl-bilibili-player');
    if (player && player.contentWindow) {
      player.contentWindow.postMessage({ type: 'seek', time: seconds }, '*');
    }
  }

  /* ===================== 学习内容加载 (核心) ===================== */
  function loadLearningContent(sub) {
    var ch = chapters[currentChapterIdx];
    var currentSub = ch && ch.children[currentSubIdx];

    // 1. 欢迎标题
    document.getElementById('cl-welcome-title-text').textContent =
      (course ? course.title + ' · ' : '') + (currentSub ? currentSub.title : '');

    // 2. 讲义 / 概念 / 导图 / 练习 — 全部走后端, 无数据则空状态
    fetch('/api/courses/courses/' + encodeURIComponent(courseId) + '/subchapters/' + encodeURIComponent(sub.id) + '/content')
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (res) {
        var data = (res && res.data) || {};

        currentMindMap   = data.mindMap || null;
        currentExercises = data.exercises || [];

        // 1. 写讲义 (并显示缓存命中/失败提示)
        var transcriptEl = document.getElementById('cl-transcript-content');
        if (data.transcript) {
          var note = data.note
            ? '<div class="cl-transcript-empty" style="margin-bottom:10px">' + escapeHtml(data.note) + '</div>'
            : '';
          transcriptEl.innerHTML = note + data.transcript;
        } else {
          transcriptEl.innerHTML =
            '<div class="cl-transcript-empty">该小节暂无 AI 讲义' +
            (data.note ? ' — ' + escapeHtml(data.note) : ' (稍后再试或确认字幕是否可用)') +
            '</div>';
        }

        // 2. 概念 / 练习 立即渲染
        renderConcepts(data.concepts || []);
        renderExercises(currentExercises);

        // 3. 思维导图: 等用户真的切到思维导步骤再渲染 (尺寸才准)
        //    但若当前已经在该步骤, 立即重渲染一次
        var mmPanel = document.querySelector('.cl-step-panel[data-panel="mindmap"]');
        if (mmPanel && mmPanel.classList.contains('active') && currentMindMap) {
          requestAnimationFrame(function () {
            requestAnimationFrame(function () { renderMindMap(currentMindMap); });
          });
        }
      })
      .catch(function () {
        document.getElementById('cl-transcript-content').innerHTML =
          '<div class="cl-transcript-empty">课程内容加载失败, 请稍后重试</div>';
        currentMindMap   = null;
        currentExercises = [];
        renderConcepts([]);
        renderMindMap(null);
        renderExercises([]);
      });
  }

  function currentSubId() {
    if (currentChapterIdx < 0 || !chapters[currentChapterIdx]) return null;
    var sub = chapters[currentChapterIdx].children[currentSubIdx];
    return sub ? sub.id : null;
  }

  /* ===================== 笔记 ===================== */
  function loadNotes() {
    var editor = document.getElementById('cl-notes-editor');
    if (!editor) return;
    try {
      var notes = JSON.parse(localStorage.getItem(NOTES_KEY)) || {};
      editor.value = notes[courseId] || '';
    } catch (e) {
      editor.value = '';
    }
  }

  function saveNotes() {
    var editor = document.getElementById('cl-notes-editor');
    if (!editor) return;
    try {
      var notes = JSON.parse(localStorage.getItem(NOTES_KEY)) || {};
      notes[courseId] = editor.value;
      localStorage.setItem(NOTES_KEY, JSON.stringify(notes));
      flashSaveStatus('已自动保存');
      markStepCompleted('notes');
    } catch (e) { /* ignore */ }
  }

  function flashSaveStatus(text) {
    var el = document.getElementById('cl-notes-save-status');
    if (!el) return;
    el.textContent = text;
  }

  function insertTimestamp() {
    var editor = document.getElementById('cl-notes-editor');
    if (!editor) return;
    var pos = editor.selectionStart || 0;
    var timeStr = '\n[时间戳 ' + formatTime(Date.now() / 1000 % 3600) + '] ';
    editor.value = editor.value.slice(0, pos) + timeStr + editor.value.slice(editor.selectionEnd || pos);
    editor.focus();
    editor.selectionStart = editor.selectionEnd = pos + timeStr.length;
    saveNotes();
  }

  /* ===================== 步骤引导 (Stepper) ===================== */
  function setStep(stepName, scrollIntoView) {
    if (STEP_ORDER.indexOf(stepName) < 0) return;
    currentStep = stepName;

    // 更新 stepper UI
    var currentIdx = STEP_ORDER.indexOf(stepName);
    document.querySelectorAll('.cl-step').forEach(function (el) {
      var step = el.getAttribute('data-step');
      var idx = STEP_ORDER.indexOf(step);
      el.classList.toggle('active', step === stepName);
      el.classList.toggle('completed', idx < currentIdx);
    });

    // 进度条
    var pct = currentIdx === 0 ? 0 : (currentIdx / (STEP_ORDER.length - 1)) * 100;
    document.getElementById('cl-stepper-progress').style.width = pct + '%';

    // 切换面板
    document.querySelectorAll('.cl-step-panel').forEach(function (p) {
      p.classList.toggle('active', p.getAttribute('data-panel') === stepName);
    });

    // 思维导图需要按当前可见视口尺寸重渲染
    // 视口尺寸在父面板切换瞬间才稳定, 等两帧再读
    if (stepName === 'mindmap' && currentMindMap) {
      requestAnimationFrame(function () {
        requestAnimationFrame(function () {
          var viewport = document.getElementById('cl-mindmap-viewport');
          if (viewport && viewport.clientHeight < 40) {
            viewport.style.minHeight = '320px';
          }
          renderMindMap(currentMindMap);
        });
      });
    }

    // 滚动到内容区
    if (scrollIntoView) {
      var main = document.querySelector('.cl-main');
      if (main) {
        var panels = document.querySelector('.cl-step-panels');
        if (panels) panels.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    }

    // 持久化当前步骤
    saveStepProgress();
  }

  function markStepCompleted(stepName) {
    if (STEP_ORDER.indexOf(stepName) < 0) return;
    var el = document.querySelector('.cl-step[data-step="' + stepName + '"]');
    if (el) el.classList.add('completed');
  }

  function loadStepProgress() {
    try {
      var data = JSON.parse(localStorage.getItem(STEP_PROGRESS_KEY)) || {};
      var subId = currentSubId();
      if (subId && data[subId]) {
        // 恢复已完成的步骤
        data[subId].forEach(function (s) { markStepCompleted(s); });
      }
    } catch (e) { /* ignore */ }
  }

  function saveStepProgress() {
    try {
      var data = JSON.parse(localStorage.getItem(STEP_PROGRESS_KEY)) || {};
      var subId = currentSubId();
      if (!subId) return;
      var completed = [];
      document.querySelectorAll('.cl-step.completed').forEach(function (el) {
        completed.push(el.getAttribute('data-step'));
      });
      data[subId] = completed;
      localStorage.setItem(STEP_PROGRESS_KEY, JSON.stringify(data));
    } catch (e) { /* ignore */ }
  }

  /* ===================== 关键概念 ===================== */
  var conceptFilter = 'all';

  function renderConcepts(concepts) {
    var grid = document.getElementById('cl-concepts-grid');
    document.getElementById('cl-concepts-count').textContent = concepts.length;

    if (concepts.length === 0) {
      grid.innerHTML = '<div class="cl-empty-card"><p>暂无概念</p></div>';
      return;
    }

    var levelColors = {
      core:     'var(--cl-danger)',
      basic:    'var(--cl-info)',
      advanced: 'var(--cl-warning)'
    };
    var levelLabels = { core: '核心', basic: '基础', advanced: '进阶' };

    var html = '';
    concepts.forEach(function (c, idx) {
      var lvl = c.level || 'basic';
      var color = levelColors[lvl] || 'var(--cl-accent)';
      html += '<div class="cl-concept-card" data-level="' + lvl + '" style="--concept-color: ' + color + '">';
      html += '  <div class="cl-concept-head">';
      html += '    <div class="cl-concept-term">' + escapeHtml(c.term) + '</div>';
      html += '    <span class="cl-concept-level ' + lvl + '">' + (levelLabels[lvl] || lvl) + '</span>';
      html += '  </div>';
      html += '  <p class="cl-concept-def">' + escapeHtml(c.definition) + '</p>';
      if (c.example) {
        html += '  <div class="cl-concept-example">💡 ' + escapeHtml(c.example) + '</div>';
      }
      html += '</div>';
    });
    grid.innerHTML = html;

    applyConceptFilter();
  }

  function applyConceptFilter() {
    var cards = document.querySelectorAll('.cl-concept-card');
    cards.forEach(function (c) {
      if (conceptFilter === 'all' || c.getAttribute('data-level') === conceptFilter) {
        c.style.display = '';
      } else {
        c.style.display = 'none';
      }
    });
  }

  /* ===================== 思维导图 ===================== */
  function renderMindMap(data) {
    currentMindMap = data;  // 保存供后续重渲染
    var stage = document.getElementById('cl-mindmap-stage');
    var viewport = document.getElementById('cl-mindmap-viewport');
    mindmapZoom = 1; mindmapOffsetX = 0; mindmapOffsetY = 0;

    if (!data || !data.name) {
      stage.innerHTML =
        '<div class="cl-empty-card">' +
        '<p>该小节暂未生成思维导图</p>' +
        '<p style="font-size:12px;color:var(--cl-text-faint);margin-top:6px">' +
        'AI 将基于字幕/讲义自动梳理, 请确认本节是否有可用的字幕或文字稿' +
        '</p></div>';
      return;
    }

    // 递归布局: 根节点居中, 子节点左右展开
    // 用视口实际尺寸作为画布, 这样节点就一定落在可见区域
    // 视口在 display:none 时尺寸为 0, 必须先用 CSS min 兜底再读尺寸
    if (viewport) {
      // 强制让视口"可测量": 临时给它一个最小高度, 即使父面板还没激活
      if (viewport.clientHeight === 0) {
        viewport.style.minHeight = '320px';
      }
    }
    var vw = (viewport ? viewport.clientWidth : 800) || 800;
    var vh = (viewport ? viewport.clientHeight : 320) || 320;
    var W = Math.max(640, vw);
    var H = Math.max(320, vh);
    var root = data;
    var nodes = [];
    var lines = [];

    // 先把根的子节点分成左右两侧
    var sideMap = {};
    if (root.children && root.children.length > 0) {
      var half = Math.ceil(root.children.length / 2);
      root.children.forEach(function (c, i) {
        sideMap[i] = i < half ? 1 : -1;
      });
    }

    // 单次递归: 走遍整棵树, 用 sideMap 决定一级节点的左右
    function walk(node, depth, side, parentX, parentY) {
      var x, y;
      if (depth === 0) {
        x = W / 2; y = H / 2;
      } else {
        var siblings = node._siblings || 1;
        var idx = node._idxInSiblings || 0;
        var range = Math.min(H - 80, siblings * 56);
        var offset = siblings > 1 ? (idx / (siblings - 1) - 0.5) * range : 0;
        y = parentY + offset;
        if (depth === 1) {
          x = parentX + side * 160;
        } else {
          x = parentX + side * 130;
        }
        // 夹紧到画布内
        x = Math.max(60, Math.min(W - 60, x));
        y = Math.max(20, Math.min(H - 20, y));
      }
      node._x = x; node._y = y;
      node._depth = depth;
      nodes.push({ x: x, y: y, name: node.name, depth: depth });

      if (node.children) {
        for (var i = 0; i < node.children.length; i++) {
          var child = node.children[i];
          child._parent = node;
          child._siblings = node.children.length;
          child._idxInSiblings = i;
          // 二级以下沿用父节点的方向
          walk(child, depth + 1, side, x, y);
        }
      }
    }
    root._parent = null;
    walk(root, 0, 0, W / 2, H / 2);
    // 一级节点按 sideMap 走第二遍覆盖位置
    if (root.children) {
      root.children.forEach(function (c, i) {
        // 注意: 不要再设 c._parent = root, 否则会丢失
        walk(c, 1, sideMap[i], W / 2, H / 2);
      });
    }

    // 生成 SVG + 节点
    var svgHtml = '<svg width="' + W + '" height="' + H + '" style="position:absolute;left:0;top:0;pointer-events:none;overflow:visible;">';
    function drawLines(node) {
      if (node._parent) {
        // 简单贝塞尔曲线
        var x1 = node._parent._x, y1 = node._parent._y;
        var x2 = node._x, y2 = node._y;
        var midX = (x1 + x2) / 2;
        svgHtml += '<path class="cl-mindmap-line' + (node._parent._parent ? ' l2' : '') + '" d="M' + x1 + ' ' + y1 + ' C' + midX + ' ' + y1 + ' ' + midX + ' ' + y2 + ' ' + x2 + ' ' + y2 + '"/>';
      }
      if (node.children) node.children.forEach(drawLines);
    }
    drawLines(root);
    svgHtml += '</svg>';

    var nodeHtml = '';
    function buildNode(n) {
      var x = n._x, y = n._y, name = n.name, depth = n._depth;
      var cls = depth === 0 ? 'root' : (depth === 1 ? 'l1' : 'l2');
      nodeHtml += '<div class="cl-mindmap-node ' + cls + '" style="left:' + x + 'px;top:' + y + 'px">' + escapeHtml(name) + '</div>';
      if (n.children) n.children.forEach(buildNode);
    }
    buildNode(root);

    stage.innerHTML = svgHtml + nodeHtml +
      '<div class="cl-mindmap-legend">' +
      '<span><i style="background:var(--cl-accent)"></i>核心</span>' +
      '<span><i style="background:var(--cl-accent-2)"></i>分支</span>' +
      '<span><i style="background:#666"></i>细节</span>' +
      '</div>';

    applyMindMapTransform();
    markStepCompleted('mindmap');
  }

  function applyMindMapTransform() {
    var stage = document.getElementById('cl-mindmap-stage');
    if (!stage) return;
    stage.style.transform = 'translate(' + mindmapOffsetX + 'px,' + mindmapOffsetY + 'px) scale(' + mindmapZoom + ')';
  }

  function zoomMindMap(delta) {
    mindmapZoom = Math.max(0.4, Math.min(2.4, mindmapZoom + delta));
    applyMindMapTransform();
  }

  function resetMindMap() {
    mindmapZoom = 1; mindmapOffsetX = 0; mindmapOffsetY = 0;
    applyMindMapTransform();
  }

  /* ===================== 课后练习 ===================== */
  var exerciseState = {};  // { idx: userAnswer }

  function loadExerciseState() {
    try {
      var data = JSON.parse(localStorage.getItem(EXERCISE_KEY)) || {};
      exerciseState = data[courseId] || {};
    } catch (e) {
      exerciseState = {};
    }
  }

  function saveExerciseState() {
    try {
      var data = JSON.parse(localStorage.getItem(EXERCISE_KEY)) || {};
      data[courseId] = exerciseState;
      localStorage.setItem(EXERCISE_KEY, JSON.stringify(data));
    } catch (e) { /* ignore */ }
  }

  function renderExercises(exercises) {
    var list = document.getElementById('cl-exercise-list');
    document.getElementById('cl-exercises-count').textContent = exercises.length;

    if (exercises.length === 0) {
      list.innerHTML = '<div class="cl-empty-card"><p>暂无练习</p></div>';
      updateExerciseScore();
      return;
    }

    var typeMap = {
      choice: '选择题',
      bool:   '判断题',
      fill:   '填空题'
    };

    var html = '';
    exercises.forEach(function (ex, idx) {
      var answered = exerciseState.hasOwnProperty(idx);
      var isCorrect = answered && checkAnswer(ex, exerciseState[idx]);
      var cls = 'cl-exercise-item' + (answered ? ' answered' : '') + (isCorrect ? ' correct' : (answered ? ' wrong' : ''));

      html += '<div class="' + cls + '" data-idx="' + idx + '" data-type="' + ex.type + '">';
      html += '  <div class="cl-exercise-head">';
      html += '    <span class="cl-exercise-num">' + (idx + 1) + '</span>';
      html += '    <span class="cl-exercise-type">' + (typeMap[ex.type] || ex.type) + '</span>';
      html += '  </div>';
      html += '  <p class="cl-exercise-q">' + ex.question + '</p>';

      if (ex.type === 'choice') {
        html += '<div class="cl-exercise-options">';
        ex.options.forEach(function (opt, oi) {
          var sel = exerciseState[idx] === oi;
          var optCls = 'cl-exercise-option';
          if (answered) {
            optCls += ' disabled';
            if (oi === ex.answer) optCls += ' correct';
            else if (sel) optCls += ' wrong';
          } else if (sel) {
            optCls += ' selected';
          }
          html += '<div class="' + optCls + '" data-opt="' + oi + '">';
          html += '  <span class="cl-exercise-marker">' + String.fromCharCode(65 + oi) + '</span>';
          html += '  <span>' + escapeHtml(opt) + '</span>';
          html += '</div>';
        });
        html += '</div>';
      } else if (ex.type === 'bool') {
        var u = exerciseState[idx];
        html += '<div class="cl-exercise-truefalse">';
        [true, false].forEach(function (val) {
          var sel = u === val;
          var optCls = 'cl-exercise-option';
          if (answered) {
            optCls += ' disabled';
            if (val === ex.answer) optCls += ' correct';
            else if (sel) optCls += ' wrong';
          } else if (sel) {
            optCls += ' selected';
          }
          html += '<div class="' + optCls + '" data-bool="' + (val ? 'true' : 'false') + '">';
          html += '  <span class="cl-exercise-marker">' + (val ? '✓' : '✗') + '</span>';
          html += '  <span>' + (val ? '正确' : '错误') + '</span>';
          html += '</div>';
        });
        html += '</div>';
      } else if (ex.type === 'fill') {
        var inputCls = '';
        if (answered) {
          inputCls = isCorrect ? 'correct' : 'wrong';
        }
        html += '<div class="cl-exercise-fill">';
        html += '  <input type="text" class="' + inputCls + '" placeholder="请输入答案" value="' + escapeHtml(answered ? String(exerciseState[idx] || '') : '') + '" ' + (answered ? 'disabled' : '') + '>';
        html += '  <button class="cl-exercise-reset" type="button" data-fill-submit="' + idx + '" ' + (answered ? 'style="display:none"' : '') + '>提交</button>';
        if (answered && !isCorrect) {
          html += '  <div style="font-size:12px;color:var(--cl-danger);margin-left:8px">正确答案: ' + escapeHtml(ex.answer) + '</div>';
        }
        html += '</div>';
      }

      html += '  <div class="cl-exercise-explain">💡 ' + escapeHtml(ex.explanation || '') + '</div>';
      html += '</div>';
    });
    list.innerHTML = html;

    bindExerciseEvents(exercises);
    updateExerciseScore();
  }

  function checkAnswer(ex, user) {
    if (user === undefined || user === null) return false;
    if (ex.type === 'choice') return user === ex.answer;
    if (ex.type === 'bool')   return user === ex.answer;
    if (ex.type === 'fill')   return String(user).trim() === String(ex.answer).trim();
    return false;
  }

  function bindExerciseEvents(exercises) {
    // 选择题 / 判断题
    document.querySelectorAll('.cl-exercise-option').forEach(function (opt) {
      opt.addEventListener('click', function () {
        if (opt.classList.contains('disabled')) return;
        var item = opt.closest('.cl-exercise-item');
        var idx = parseInt(item.getAttribute('data-idx'));
        var ex = exercises[idx];

        if (ex.type === 'bool') {
          exerciseState[idx] = opt.getAttribute('data-bool') === 'true';
        } else {
          exerciseState[idx] = parseInt(opt.getAttribute('data-opt'));
        }
        saveExerciseState();
        renderExercises(exercises);
        showFeedback(item, ex);
      });
    });
    // 填空题提交
    document.querySelectorAll('[data-fill-submit]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var idx = parseInt(btn.getAttribute('data-fill-submit'));
        var item = btn.closest('.cl-exercise-item');
        var input = item.querySelector('input');
        var ex = exercises[idx];
        exerciseState[idx] = input.value;
        saveExerciseState();
        renderExercises(exercises);
      });
    });
  }

  function showFeedback(item, ex) {
    // 答完自动滚动到下一题
    var next = item.nextElementSibling;
    if (next && next.classList.contains('cl-exercise-item')) {
      // 只在视口外时滚动
      var r = next.getBoundingClientRect();
      if (r.bottom > window.innerHeight) {
        next.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
    } else {
      // 最后一题, 触发完成检测
      var allAnswered = checkAllAnswered();
      if (allAnswered) {
        markStepCompleted('exercises');
        showToast('已完成全部练习, 继续保持!', 'success');
      }
    }
  }

  function checkAllAnswered() {
    var total = document.querySelectorAll('.cl-exercise-item').length;
    var answered = document.querySelectorAll('.cl-exercise-item.answered').length;
    return total > 0 && total === answered;
  }

  function updateExerciseScore() {
    var items = document.querySelectorAll('.cl-exercise-item');
    var total = items.length;
    var answered = 0, correct = 0;
    items.forEach(function (it) {
      if (it.classList.contains('answered')) {
        answered++;
        if (it.classList.contains('correct')) correct++;
      }
    });
    document.getElementById('cl-exercise-score').textContent = '已答 ' + answered + ' / ' + total;
    var rate = answered > 0 ? Math.round((correct / answered) * 100) : 0;
    document.getElementById('cl-exercise-rate').textContent = '正确率 ' + rate + '%';

    var submitBtn = document.getElementById('cl-exercise-submit');
    if (submitBtn) submitBtn.disabled = answered === 0;
  }

  function resetExercises() {
    exerciseState = {};
    saveExerciseState();
    renderExercises(currentExercises);
  }

  function submitExercises() {
    var total = document.querySelectorAll('.cl-exercise-item').length;
    var answered = document.querySelectorAll('.cl-exercise-item.answered').length;
    if (answered === 0) {
      showToast('请先作答再交卷', 'error');
      return;
    }
    var correct = document.querySelectorAll('.cl-exercise-item.correct').length;
    var rate = Math.round((correct / answered) * 100);
    showToast('本次得分: ' + correct + ' / ' + answered + ' (正确率 ' + rate + '%)', 'success');
    markStepCompleted('exercises');
  }

  /* ===================== 章节导航 ===================== */
  function updateNavigation() {
    var prevBtn = document.getElementById('cl-nav-prev');
    var nextBtn = document.getElementById('cl-nav-next');
    var counter = document.getElementById('cl-nav-counter');
    var currentEl = document.getElementById('cl-nav-current');

    var totalSubs = 0;
    var currentFlatIdx = 0;

    for (var i = 0; i < chapters.length; i++) {
      var children = chapters[i].children || [];
      for (var j = 0; j < children.length; j++) {
        if (i === currentChapterIdx && j === currentSubIdx) currentFlatIdx = totalSubs;
        totalSubs++;
      }
    }
    counter.textContent = (currentFlatIdx + 1) + ' / ' + totalSubs;
    prevBtn.disabled = currentFlatIdx === 0;
    nextBtn.disabled = currentFlatIdx >= totalSubs - 1;

    var ch = chapters[currentChapterIdx];
    var sub = ch && ch.children[currentSubIdx];
    currentEl.textContent = sub ? sub.title : '第 ' + (currentFlatIdx + 1) + ' 节';

    updateProgressBar(currentFlatIdx + 1, totalSubs);
  }

  function updateProgressBar(current, total) {
    var pct = total > 0 ? Math.round((current / total) * 100) : 0;
    document.getElementById('cl-progress-fill').style.width = pct + '%';
    document.getElementById('cl-progress-text').textContent = pct + '%';
    if (course) course.progress = pct;
    saveCourseData();
    saveProgress();
  }

  function navigatePrev() {
    if (currentSubIdx > 0) selectChapter(currentChapterIdx, currentSubIdx - 1);
    else if (currentChapterIdx > 0) {
      var prev = chapters[currentChapterIdx - 1];
      var last = (prev.children || []).length - 1;
      if (last >= 0) selectChapter(currentChapterIdx - 1, last);
    }
  }

  function navigateNext() {
    var cur = chapters[currentChapterIdx];
    if (cur && currentSubIdx < (cur.children || []).length - 1) {
      selectChapter(currentChapterIdx, currentSubIdx + 1);
    } else if (currentChapterIdx < chapters.length - 1) {
      var next = chapters[currentChapterIdx + 1];
      if (next.children && next.children.length > 0) selectChapter(currentChapterIdx + 1, 0);
    }
  }

  function findStartIndex() {
    try {
      var saved = JSON.parse(localStorage.getItem(PROGRESS_KEY)) || {};
      var p = saved[courseId];
      if (p && p.currentChapterIdx !== undefined) return p.currentChapterIdx;
    } catch (e) { /* ignore */ }
    return 0;
  }

  /* ===================== 标记章节完成 ===================== */
  function markChapterComplete() {
    if (currentChapterIdx < 0) return;
    var sub = chapters[currentChapterIdx].children[currentSubIdx];
    if (!sub) return;
    sub.completed = true;
    renderChapterTree();
    var btn = document.getElementById('cl-mark-complete');
    if (btn) {
      btn.classList.add('completed');
      btn.querySelector('span').textContent = '已完成';
    }
    showToast('已标记本节完成 🎉', 'success');
  }

  /* ===================== 持久化 ===================== */
  function saveProgress() {
    try {
      var data = JSON.parse(localStorage.getItem(PROGRESS_KEY)) || {};
      data[courseId] = {
        currentChapterIdx: currentChapterIdx,
        currentSubIdx: currentSubIdx,
        progress: course ? course.progress : 0,
        updatedAt: new Date().toISOString()
      };
      localStorage.setItem(PROGRESS_KEY, JSON.stringify(data));
    } catch (e) { /* ignore */ }
  }

  function saveCourseData() {
    try {
      var data = JSON.parse(localStorage.getItem(STORAGE_KEY));
      if (!data || !data.subjects) return;
      for (var i = 0; i < data.subjects.length; i++) {
        var list = data.subjects[i].courses || [];
        for (var j = 0; j < list.length; j++) {
          if (list[j].id === courseId) {
            list[j].totalLessons = course.totalLessons;
            list[j].totalDuration = course.totalDuration;
            list[j].progress = course.progress;
            return;
          }
        }
      }
    } catch (e) { /* ignore */ }
  }

  /* ===================== Tab / Sidebar 切换 ===================== */
  function switchSubtab(name) {
    document.querySelectorAll('.cl-subtab').forEach(function (t) {
      t.classList.toggle('active', t.getAttribute('data-subtab') === name);
    });
    document.querySelectorAll('.cl-subtab-panel').forEach(function (p) {
      p.classList.toggle('active', p.getAttribute('data-subtab-panel') === name);
    });
    if (name === 'subtitles') markStepCompleted('subtitles');
  }

  function toggleSidebar() {
    sidebarCollapsed = !sidebarCollapsed;
    var sb = document.getElementById('cl-sidebar');
    sb.classList.toggle('collapsed', sidebarCollapsed);
  }

  /* ===================== 工具 ===================== */
  function formatDuration(seconds) {
    if (!seconds) return '--:--';
    var m = Math.floor(seconds / 60);
    var s = seconds % 60;
    return m + ':' + String(s).padStart(2, '0');
  }

  function formatTime(seconds) {
    var s = Math.floor(seconds || 0);
    var m = Math.floor(s / 60);
    var h = Math.floor(m / 60);
    m = m % 60; s = s % 60;
    if (h > 0) return String(h).padStart(2, '0') + ':' + String(m).padStart(2, '0') + ':' + String(s).padStart(2, '0');
    return String(m).padStart(2, '0') + ':' + String(s).padStart(2, '0');
  }

  function escapeHtml(str) {
    var div = document.createElement('div');
    div.textContent = str == null ? '' : String(str);
    return div.innerHTML;
  }

  function showToast(message, type) {
    var container = document.getElementById('toast-container');
    if (!container) return;
    var toast = document.createElement('div');
    toast.className = 'toast ' + (type || 'info');
    toast.textContent = message;
    container.appendChild(toast);
    setTimeout(function () {
      toast.style.opacity = '0';
      toast.style.transform = 'translateX(40px)';
      setTimeout(function () { toast.remove(); }, 300);
    }, 3000);
  }

  /* ===================== AI 视频生成 ===================== */

  /**
   * 拼一段真实基于"本节"的 prompt: 课程/章节标题 + B 站字幕 + AI 概念.
   * 若 subtitleData / currentExercises / concepts 都为空, 至少会带上课程+章节标题,
   * 不会像以前那样只拼一行 "制作一个教学视频" 的水 prompt.
   */
  function buildAIVideoPrompt() {
    var ch = chapters[currentChapterIdx];
    var sub = ch && ch.children[currentSubIdx];
    if (!sub) return null;

    var lines = [];
    lines.push(
      '【课程】' + ((course && course.title) || '未命名课程') +
      (course && course.author_name ? '（作者: ' + course.author_name + '）' : '')
    );
    lines.push('【本节主题】' + (sub.title || '本节') +
      ' (B站视频 ' + (sub.bvid || '?') + ' P' + (sub.page || 1) + ', 时长 ' +
      formatDuration(sub.duration) + ')');
    if (ch && ch.title && ch.title !== sub.title) {
      lines.push('【所属章节】' + ch.title);
    }

    // 1. 优先取字幕
    var subTexts = (subtitleData || []).map(function (s) {
      return (s.content || '').trim();
    }).filter(Boolean);
    if (subTexts.length) {
      lines.push('【本节字幕要点】');
      // 取首尾关键句, 中段采样, 单条不超过 30 字
      var sample = subTexts.length <= 8
        ? subTexts
        : subTexts.slice(0, 4).concat(subTexts.slice(Math.floor(subTexts.length / 2) - 2,
                                                      Math.floor(subTexts.length / 2) + 2))
                  .concat(subTexts.slice(-4));
      lines.push(sample.map(function (t, i) { return (i + 1) + '. ' + t.slice(0, 80); }).join('\n'));
    }

    // 2. 再补 AI 生成的关键概念 (从后端)
    var conceptEls = document.querySelectorAll('#cl-concepts-grid .cl-concept-term');
    if (conceptEls.length) {
      lines.push('【关键概念】' +
        Array.from(conceptEls).slice(0, 6)
          .map(function (e) { return e.textContent.trim(); }).join('、'));
    }

    // 3. 任务指令
    lines.push('');
    lines.push(
      '请基于以上真实内容生成一段 30 秒以内的教学讲解视频。'
      + '画面: 教师在教室白板前逐条讲解字幕要点, 概念部分用英文/中文标注.'
      + '语速偏慢, 面向中学生, 不出现与课程无关的画面.'
    );

    return lines.join('\n');
  }

  function generateAIVideo() {
    var ch = chapters[currentChapterIdx];
    var sub = ch && ch.children[currentSubIdx];
    if (!sub) { showToast('请先选择章节', 'error'); return; }

    var prompt = buildAIVideoPrompt();
    if (!prompt) return;

    var btn = document.getElementById('cl-ai-gen-btn');
    var progress = document.getElementById('cl-ai-progress');
    var player = document.getElementById('cl-ai-player');
    var errorEl = document.getElementById('cl-ai-error');

    btn.style.display = 'none';
    errorEl.style.display = 'none';
    player.style.display = 'none';
    progress.style.display = 'flex';
    updateAIProgressText('正在提交 AI 讲解任务...');

    fetch('/api/seed/video', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        prompt: prompt,
        ratio: '16:9',
        duration: 5,
        generate_audio: true,
        watermark: true
      })
    })
    .then(function (r) { return r.json(); })
    .then(function (res) {
      if (res.code !== 200) throw new Error((res.data && res.data.error) || '创建任务失败');
      aiVideoState.taskId = res.data.task_id;
      aiVideoState.status = 'queued';
      pollVideoTask();
    })
    .catch(function (err) {
      showAIError(err.message);
    });
  }

  function pollVideoTask() {
    clearTimeout(aiVideoState.pollTimer);

    if (!aiVideoState.taskId) return;

    fetch('/api/seed/video/' + encodeURIComponent(aiVideoState.taskId))
      .then(function (r) { return r.json(); })
      .then(function (res) {
        if (res.code !== 200) throw new Error((res.data && res.data.error) || '查询失败');
        var data = res.data;
        aiVideoState.status = data.status;

        if (data.status === 'succeeded') {
          if (data.local_url) {
            showAIVideoPlayer(data.local_url);
          } else {
            showAIError('视频生成成功但获取地址失败');
          }
        } else if (data.status === 'failed') {
          showAIError((data.error && data.error.message) || '视频生成失败');
        } else if (data.status === 'cancelled') {
          showAIError('视频生成已取消');
        } else {
          updateAIProgressText(data.status === 'queued' ? '排队中...' : 'AI 生成中, 请耐心等待...');
          aiVideoState.pollTimer = setTimeout(pollVideoTask, 5000);
        }
      })
      .catch(function (err) {
        showAIError(err.message);
      });
  }

  function showAIVideoPlayer(url) {
    document.getElementById('cl-ai-progress').style.display = 'none';
    var player = document.getElementById('cl-ai-player');
    var video = document.getElementById('cl-ai-video');
    video.src = url;
    player.style.display = 'block';
    showToast('AI 讲解视频已生成!', 'success');
  }

  function showAIError(msg) {
    document.getElementById('cl-ai-progress').style.display = 'none';
    var btn = document.getElementById('cl-ai-gen-btn');
    btn.style.display = 'inline-flex';
    btn.querySelector('span').textContent = '重新生成';
    var errorEl = document.getElementById('cl-ai-error');
    errorEl.textContent = msg;
    errorEl.style.display = 'block';
    showToast(msg, 'error');
  }

  function updateAIProgressText(text) {
    var el = document.getElementById('cl-ai-progress-text');
    if (el) el.textContent = text;
  }

  /* ===================== 事件绑定 ===================== */
  function bindEvents() {
    // 上一节 / 下一节
    document.getElementById('cl-nav-prev').addEventListener('click', navigatePrev);
    document.getElementById('cl-nav-next').addEventListener('click', navigateNext);

    // 侧边栏
    document.getElementById('cl-sidebar-toggle').addEventListener('click', toggleSidebar);
    document.getElementById('cl-sidebar-expand').addEventListener('click', toggleSidebar);

    // 步骤引导
    document.querySelectorAll('.cl-step').forEach(function (el) {
      el.addEventListener('click', function () {
        setStep(el.getAttribute('data-step'), true);
      });
    });

    // Subtab
    document.querySelectorAll('.cl-subtab').forEach(function (t) {
      t.addEventListener('click', function () { switchSubtab(t.getAttribute('data-subtab')); });
    });

    // 概念筛选
    document.querySelectorAll('.cl-filter-chip').forEach(function (c) {
      c.addEventListener('click', function () {
        document.querySelectorAll('.cl-filter-chip').forEach(function (x) { x.classList.remove('active'); });
        c.classList.add('active');
        conceptFilter = c.getAttribute('data-level');
        applyConceptFilter();
      });
    });

    // 思维导图缩放
    var mmIn = document.getElementById('cl-mm-zoom-in');
    var mmOut = document.getElementById('cl-mm-zoom-out');
    var mmReset = document.getElementById('cl-mm-reset');
    if (mmIn) mmIn.addEventListener('click', function () { zoomMindMap(0.15); });
    if (mmOut) mmOut.addEventListener('click', function () { zoomMindMap(-0.15); });
    if (mmReset) mmReset.addEventListener('click', resetMindMap);

    // 思维导图拖动
    var viewport = document.getElementById('cl-mindmap-viewport');
    if (viewport) {
      viewport.addEventListener('mousedown', function (e) {
        if (e.target.closest('.cl-mindmap-node')) return;
        isDraggingMM = true;
        dragStartX = e.clientX - mindmapOffsetX;
        dragStartY = e.clientY - mindmapOffsetY;
        viewport.style.cursor = 'grabbing';
      });
      window.addEventListener('mousemove', function (e) {
        if (!isDraggingMM) return;
        mindmapOffsetX = e.clientX - dragStartX;
        mindmapOffsetY = e.clientY - dragStartY;
        applyMindMapTransform();
      });
      window.addEventListener('mouseup', function () {
        if (isDraggingMM) {
          isDraggingMM = false;
          if (viewport) viewport.style.cursor = 'grab';
        }
      });
      // 滚轮缩放
      viewport.addEventListener('wheel', function (e) {
        if (e.ctrlKey || e.metaKey || Math.abs(e.deltaY) > 30) {
          e.preventDefault();
          zoomMindMap(e.deltaY > 0 ? -0.1 : 0.1);
        }
      }, { passive: false });
    }

    // 笔记
    var notesEditor = document.getElementById('cl-notes-editor');
    if (notesEditor) {
      var saveT;
      notesEditor.addEventListener('input', function () {
        clearTimeout(saveT);
        flashSaveStatus('保存中...');
        saveT = setTimeout(saveNotes, 800);
      });
      notesEditor.addEventListener('blur', saveNotes);
    }
    var insertBtn = document.getElementById('cl-notes-insert-time');
    if (insertBtn) insertBtn.addEventListener('click', insertTimestamp);

    // 标记完成
    var markBtn = document.getElementById('cl-mark-complete');
    if (markBtn) markBtn.addEventListener('click', markChapterComplete);

    // AI 生成讲解视频
    var aiBtn = document.getElementById('cl-ai-gen-btn');
    if (aiBtn) aiBtn.addEventListener('click', generateAIVideo);

    // 欢迎下一步
    var welcomeNext = document.getElementById('cl-welcome-next');
    if (welcomeNext) welcomeNext.addEventListener('click', function () {
      markStepCompleted('watch');
      setStep('subtitles', true);
    });

    // 练习交卷 / 重置
    var submitBtn = document.getElementById('cl-exercise-submit');
    var resetBtn = document.getElementById('cl-exercise-reset');
    if (submitBtn) submitBtn.addEventListener('click', submitExercises);
    if (resetBtn) resetBtn.addEventListener('click', resetExercises);

    // 键盘快捷键
    document.addEventListener('keydown', function (e) {
      if (e.target.closest('input, textarea')) return;
      if (e.key === 'ArrowLeft') navigatePrev();
      else if (e.key === 'ArrowRight') navigateNext();
    });

    // 窗口尺寸变化: 重渲染当前可见的思维导图, 让节点不会被裁出视口
    var mmResizeT;
    window.addEventListener('resize', function () {
      if (!currentMindMap) return;
      var mmPanel = document.querySelector('.cl-step-panel[data-panel="mindmap"]');
      if (!mmPanel || !mmPanel.classList.contains('active')) return;
      clearTimeout(mmResizeT);
      mmResizeT = setTimeout(function () {
        // 保留当前缩放与偏移, 只重排
        renderMindMap(currentMindMap);
      }, 180);
    });
  }

  /* ===================== 启动 ===================== */
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  // 暴露给 Playwright / 调试
  window.CourseLearn = {
    getCourse: function () { return course; },
    getChapters: function () { return chapters; },
    selectChapter: selectChapter,
    setStep: setStep
  };
})();
