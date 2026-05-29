/**
 * Course Learning Page
 * Two-column layout: chapter tree (left) + B站 player & content (right)
 */

(function() {
  'use strict';

  var STORAGE_KEY = 'starlearn_courses_data';
  var NOTES_KEY = 'starlearn_course_notes';
  var PROGRESS_KEY = 'starlearn_course_progress';

  var courseId = null;
  var subjectSlug = null;
  var course = null;
  var chapters = [];
  var currentChapterIdx = -1;
  var currentSubIdx = -1;
  var subtitleData = [];
  var sidebarCollapsed = false;

  // ---- Init ----

  function init() {
    var params = new URLSearchParams(window.location.search);
    courseId = params.get('courseId');
    subjectSlug = params.get('subject');

    if (!courseId) {
      showToast('未指定课程', 'error');
      return;
    }

    loadCourse();
    if (!course) {
      // Try loading from backend first, then fall back to bvid from URL or courseId
      course = { id: courseId, title: '加载中...', bvid: extractBvidFromCourseId(courseId), totalLessons: 1, totalDuration: 0, progress: 0 };
    }

    document.getElementById('cl-course-title').textContent = course.title;
    buildChapterTree();
    loadNotes();
    bindEvents();

    // Try loading from backend for richer data (will rebuild tree on success)
    loadCourseFromBackend();
  }

  function extractBvidFromCourseId(id) {
    // courseId may be a URL like 'https://...' or contain a BV id
    var match = id.match(/BV[a-zA-Z0-9]{10}/);
    return match ? match[0] : '';
  }

  function loadCourse() {
    try {
      var data = JSON.parse(localStorage.getItem(STORAGE_KEY));
      if (!data || !data.subjects) return;
      for (var i = 0; i < data.subjects.length; i++) {
        var courses = data.subjects[i].courses;
        for (var j = 0; j < courses.length; j++) {
          if (courses[j].id === courseId) {
            course = courses[j];
            return;
          }
        }
      }
    } catch (e) { /* ignore */ }
  }

  function loadCourseFromBackend() {
    fetch('/api/courses/courses/' + courseId)
      .then(function(r) { return r.json(); })
      .then(function(res) {
        if (res.code === 200 && res.data) {
          var d = res.data;
          course = {
            id: d.id,
            title: d.title,
            bvid: d.bvid,
            totalLessons: d.total_lessons,
            totalDuration: d.total_duration,
            progress: d.progress,
            coverUrl: d.cover_url,
          };
          // Build chapters from backend nested data
          chapters = (d.chapters || []).map(function(ch) {
            return {
              id: ch.id,
              title: ch.title,
              expanded: true,
              children: (ch.subchapters || []).map(function(sc) {
                return {
                  id: sc.id,
                  title: sc.title,
                  duration: sc.duration,
                  cid: sc.cid,
                  page: sc.page,
                  bvid: sc.bvid,
                  completed: sc.completed,
                };
              }),
            };
          });
          document.getElementById('cl-course-title').textContent = course.title;
          renderChapterTree();
          var startIdx = findStartIndex();
          if (chapters.length > 0) {
            selectChapter(startIdx, 0);
          }
        }
      })
      .catch(function() { /* silent fail, keep localStorage data */ });
  }

  // ---- Chapter Tree ----

  function buildChapterTree() {
    chapters = [];
    if (!course) return;

    if (course.bvid) {
      loadBilibiliChapters(course.bvid);
    } else {
      // No bvid — show placeholder, will be populated by loadCourseFromBackend
      chapters = [{
        id: 'ch-1',
        title: course.title || '课程内容',
        expanded: true,
        children: [{
          id: 'sub-1',
          title: '加载中...',
          duration: 0,
          cid: 0,
          page: 1,
          bvid: '',
          completed: false
        }]
      }];
      renderChapterTree();
    }
  }

  function loadBilibiliChapters(bvid) {
    var treeContainer = document.getElementById('cl-chapter-tree');
    treeContainer.innerHTML = '<div class="cl-tree-loading">正在加载课程目录...</div>';

    fetch('/api/bilibili/parse', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url: 'https://www.bilibili.com/video/' + bvid })
    })
      .then(function(r) { return r.json(); })
      .then(function(res) {
        if (res.code === 200 && res.data) {
          var videoData = res.data;
          var pages = videoData.pages || [];

          if (pages.length > 0) {
            // Multi-page video: each page is a subchapter
            chapters = [{
              id: 'ch-1',
              title: videoData.title || '课程内容',
              expanded: true,
              children: pages.map(function(p) {
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

            if (chapters.length > 0 && chapters[0].children.length > 0) {
              course.totalLessons = chapters[0].children.length;
              course.totalDuration = chapters[0].children.reduce(function(s, c) { return s + (c.duration || 0); }, 0);
            }
          } else {
            // Single video: one chapter
            chapters = [{
              id: 'ch-1',
              title: videoData.title || '课程内容',
              expanded: true,
              children: [{
                id: 'sub-1',
                title: videoData.title || '视频',
                duration: videoData.duration || 0,
                cid: videoData.cid,
                page: 1,
                bvid: bvid,
                completed: false
              }]
            }];
            course.totalLessons = 1;
            course.totalDuration = videoData.duration || 0;
          }

          saveCourseData();
        } else {
          // API failed; create fallback single chapter
          chapters = [{
            id: 'ch-1',
            title: course.title || '课程内容',
            expanded: true,
            children: [{
              id: 'sub-1',
              title: course.title || '视频',
              duration: course.totalDuration || 0,
              cid: 0,
              page: 1,
              bvid: bvid,
              completed: false
            }]
          }];
          course.totalLessons = 1;
        }

        renderChapterTree();
        updateTotalCount();

        // Select first chapter
        if (chapters.length > 0 && chapters[0].children.length > 0) {
          selectChapter(0, 0);
        }
      })
      .catch(function() {
        // Network error; create fallback
        chapters = [{
          id: 'ch-1',
          title: course.title || '课程内容',
          expanded: true,
          children: [{
            id: 'sub-1',
            title: course.title || '视频',
            duration: course.totalDuration || 0,
            cid: 0,
            page: 1,
            bvid: bvid,
            completed: false
          }]
        }];
        course.totalLessons = 1;
        renderChapterTree();
        if (chapters.length > 0 && chapters[0].children.length > 0) {
          selectChapter(0, 0);
        }
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
      var isExpanded = ch.expanded !== false;
      html += '<div class="cl-chapter-node">';
      html += '<div class="cl-chapter-header' + (currentChapterIdx === i ? ' active' : '') + '" data-chapter="' + i + '">';
      html += '<svg class="cl-chapter-arrow' + (isExpanded ? ' expanded' : '') + '" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="9 18 15 12 9 6"/></svg>';
      html += '<div class="cl-chapter-icon video"><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="5 3 19 12 5 21 5 3"/></svg></div>';
      html += '<div class="cl-chapter-info">';
      html += '<div class="cl-chapter-name">' + escapeHtml(ch.title) + '</div>';
      html += '<div class="cl-chapter-meta">' + (ch.children ? ch.children.length : 0) + ' 个视频</div>';
      html += '</div>';
      html += '</div>';

      if (ch.children && ch.children.length > 0) {
        html += '<div class="cl-chapter-children' + (isExpanded ? '' : ' collapsed') + '" data-chapter-children="' + i + '">';
        for (var j = 0; j < ch.children.length; j++) {
          var sub = ch.children[j];
          var isActive = currentChapterIdx === i && currentSubIdx === j;
          html += '<div class="cl-subchapter' + (isActive ? ' active' : '') + (sub.completed ? ' completed' : '') + '" data-chapter="' + i + '" data-sub="' + j + '">';
          html += '<div class="cl-subchapter-dot"></div>';
          html += '<span class="cl-subchapter-name">' + escapeHtml(sub.title) + '</span>';
          html += '<span class="cl-subchapter-dur">' + formatDuration(sub.duration) + '</span>';
          html += '</div>';
        }
        html += '</div>';
      }
      html += '</div>';
    }
    container.innerHTML = html;

    // Bind chapter header clicks (expand/collapse)
    container.querySelectorAll('.cl-chapter-header').forEach(function(header) {
      header.addEventListener('click', function(e) {
        var idx = parseInt(this.getAttribute('data-chapter'));
        toggleChapter(idx);
      });
    });

    // Bind subchapter clicks
    container.querySelectorAll('.cl-subchapter').forEach(function(sub) {
      sub.addEventListener('click', function(e) {
        e.stopPropagation();
        var chIdx = parseInt(this.getAttribute('data-chapter'));
        var subIdx = parseInt(this.getAttribute('data-sub'));
        selectChapter(chIdx, subIdx);
      });
    });

    // Set children container heights for animation
    container.querySelectorAll('.cl-chapter-children').forEach(function(el) {
      if (!el.classList.contains('collapsed')) {
        el.style.maxHeight = el.scrollHeight + 'px';
      } else {
        el.style.maxHeight = '0px';
      }
    });
  }

  function toggleChapter(idx) {
    chapters[idx].expanded = !chapters[idx].expanded;
    var container = document.querySelector('[data-chapter-children="' + idx + '"]');
    if (container) {
      if (chapters[idx].expanded) {
        container.classList.remove('collapsed');
        container.style.maxHeight = container.scrollHeight + 'px';
      } else {
        container.style.maxHeight = container.scrollHeight + 'px';
        requestAnimationFrame(function() {
          container.classList.add('collapsed');
          container.style.maxHeight = '0px';
        });
      }
    }
    // Update arrow
    var header = document.querySelector('[data-chapter="' + idx + '"].cl-chapter-header');
    if (header) {
      var arrow = header.querySelector('.cl-chapter-arrow');
      if (arrow) arrow.classList.toggle('expanded', chapters[idx].expanded);
    }
  }

  // ---- Chapter Selection ----

  function selectChapter(chIdx, subIdx) {
    if (chIdx >= chapters.length) return;
    var ch = chapters[chIdx];
    if (!ch.children || subIdx >= ch.children.length) return;

    currentChapterIdx = chIdx;
    currentSubIdx = subIdx;

    var sub = ch.children[subIdx];
    loadVideo(sub.bvid, sub.page, sub.cid);
    loadSubtitles(sub.bvid);

    // Update active states
    renderChapterTree();
    updateNavigation();
  }

  function loadVideo(bvid, page, cid) {
    var player = document.getElementById('cl-bilibili-player');
    var placeholder = document.getElementById('cl-player-placeholder');

    var embedUrl = 'https://player.bilibili.com/player.html?bvid=' + bvid + '&page=' + (page || 1) + '&high_quality=1&autoplay=1';

    player.src = embedUrl;
    player.style.display = 'block';
    placeholder.style.display = 'none';
  }

  // ---- Subtitles ----

  function loadSubtitles(bvid) {
    var container = document.getElementById('cl-subtitle-container');
    container.innerHTML = '<div class="cl-subtitle-empty">加载字幕中...</div>';

    fetch('/api/bilibili/subtitles', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ bvid: bvid })
    })
      .then(function(r) { return r.json(); })
      .then(function(res) {
        if (res.code === 200 && res.data && res.data.length > 0) {
          subtitleData = res.data[0].content || [];
          renderSubtitles();
        } else {
          container.innerHTML = '<div class="cl-subtitle-empty">该视频暂无字幕</div>';
          subtitleData = [];
        }
      })
      .catch(function() {
        container.innerHTML = '<div class="cl-subtitle-empty">字幕加载失败</div>';
        subtitleData = [];
      });
  }

  function renderSubtitles() {
    var container = document.getElementById('cl-subtitle-container');
    if (subtitleData.length === 0) {
      container.innerHTML = '<div class="cl-subtitle-empty">该视频暂无字幕</div>';
      return;
    }

    var html = '';
    for (var i = 0; i < subtitleData.length; i++) {
      var sub = subtitleData[i];
      html += '<div class="cl-subtitle-line" data-time="' + sub.from + '" data-index="' + i + '">';
      html += '<span class="cl-subtitle-time">' + formatTime(sub.from) + '</span>';
      html += '<span class="cl-subtitle-text">' + escapeHtml(sub.content) + '</span>';
      html += '</div>';
    }
    container.innerHTML = html;

    // Click to seek
    container.querySelectorAll('.cl-subtitle-line').forEach(function(line) {
      line.addEventListener('click', function() {
        var time = parseFloat(this.getAttribute('data-time'));
        seekTo(time);
      });
    });
  }

  function seekTo(seconds) {
    var player = document.getElementById('cl-bilibili-player');
    // B站 iframe postMessage API
    if (player.contentWindow) {
      player.contentWindow.postMessage({
        type: 'seek',
        time: seconds
      }, '*');
    }
  }

  // ---- Navigation ----

  function updateNavigation() {
    var prevBtn = document.getElementById('cl-nav-prev');
    var nextBtn = document.getElementById('cl-nav-next');
    var counter = document.getElementById('cl-nav-counter');

    var totalSubs = 0;
    var currentFlatIdx = 0;

    for (var i = 0; i < chapters.length; i++) {
      var children = chapters[i].children || [];
      for (var j = 0; j < children.length; j++) {
        if (i === currentChapterIdx && j === currentSubIdx) {
          currentFlatIdx = totalSubs;
        }
        totalSubs++;
      }
    }

    counter.textContent = (currentFlatIdx + 1) + ' / ' + totalSubs;
    prevBtn.disabled = currentFlatIdx === 0;
    nextBtn.disabled = currentFlatIdx >= totalSubs - 1;

    updateProgressBar(currentFlatIdx + 1, totalSubs);
  }

  function updateTotalCount() {
    var totalSubs = 0;
    for (var i = 0; i < chapters.length; i++) {
      totalSubs += (chapters[i].children || []).length;
    }
    document.getElementById('cl-nav-counter').textContent = '0 / ' + totalSubs;
  }

  function updateProgressBar(current, total) {
    var pct = total > 0 ? Math.round((current / total) * 100) : 0;
    document.getElementById('cl-progress-fill').style.width = pct + '%';
    document.getElementById('cl-progress-text').textContent = pct + '%';

    // Save progress
    course.progress = pct;
    saveCourseData();
    saveProgress();
  }

  function navigatePrev() {
    if (currentSubIdx > 0) {
      selectChapter(currentChapterIdx, currentSubIdx - 1);
    } else if (currentChapterIdx > 0) {
      var prevCh = chapters[currentChapterIdx - 1];
      var lastSubIdx = (prevCh.children || []).length - 1;
      if (lastSubIdx >= 0) {
        selectChapter(currentChapterIdx - 1, lastSubIdx);
      }
    }
  }

  function navigateNext() {
    var currentCh = chapters[currentChapterIdx];
    if (currentCh && currentSubIdx < (currentCh.children || []).length - 1) {
      selectChapter(currentChapterIdx, currentSubIdx + 1);
    } else if (currentChapterIdx < chapters.length - 1) {
      var nextCh = chapters[currentChapterIdx + 1];
      if (nextCh.children && nextCh.children.length > 0) {
        selectChapter(currentChapterIdx + 1, 0);
      }
    }
  }

  function findStartIndex() {
    // Load progress to resume
    var saved = loadProgress();
    if (saved && saved.currentChapterIdx !== undefined) {
      return saved.currentChapterIdx;
    }
    return 0;
  }

  // ---- Notes ----

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
    } catch (e) { /* ignore */ }
  }

  // ---- Progress Persistence ----

  function saveProgress() {
    try {
      var progress = JSON.parse(localStorage.getItem(PROGRESS_KEY)) || {};
      progress[courseId] = {
        currentChapterIdx: currentChapterIdx,
        currentSubIdx: currentSubIdx,
        progress: course.progress,
        updatedAt: new Date().toISOString()
      };
      localStorage.setItem(PROGRESS_KEY, JSON.stringify(progress));
    } catch (e) { /* ignore */ }
  }

  function loadProgress() {
    try {
      var progress = JSON.parse(localStorage.getItem(PROGRESS_KEY)) || {};
      return progress[courseId] || null;
    } catch (e) {
      return null;
    }
  }

  function saveCourseData() {
    try {
      var data = JSON.parse(localStorage.getItem(STORAGE_KEY));
      if (!data || !data.subjects) return;
      for (var i = 0; i < data.subjects.length; i++) {
        var courses = data.subjects[i].courses;
        for (var j = 0; j < courses.length; j++) {
          if (courses[j].id === courseId) {
            courses[j].totalLessons = course.totalLessons;
            courses[j].totalDuration = course.totalDuration;
            courses[j].progress = course.progress;
            break;
          }
        }
      }
      localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
    } catch (e) { /* ignore */ }
  }

  // ---- Tab Switching ----

  function switchTab(tabName) {
    document.querySelectorAll('.cl-content-tab').forEach(function(t) {
      t.classList.toggle('active', t.getAttribute('data-tab') === tabName);
    });
    document.querySelectorAll('.cl-tab-panel').forEach(function(p) {
      p.classList.toggle('active', p.id === 'cl-panel-' + tabName);
    });
  }

  // ---- Sidebar Toggle ----

  function toggleSidebar() {
    sidebarCollapsed = !sidebarCollapsed;
    var sidebar = document.getElementById('cl-sidebar');
    if (sidebarCollapsed) {
      sidebar.classList.add('collapsed');
    } else {
      sidebar.classList.remove('collapsed');
    }
  }

  // ---- Helpers ----

  function formatDuration(seconds) {
    if (!seconds) return '--:--';
    var m = Math.floor(seconds / 60);
    var s = seconds % 60;
    return m + ':' + String(s).padStart(2, '0');
  }

  function formatTime(seconds) {
    var s = Math.floor(seconds);
    var m = Math.floor(s / 60);
    var h = Math.floor(m / 60);
    m = m % 60;
    s = s % 60;
    if (h > 0) {
      return String(h).padStart(2, '0') + ':' + String(m).padStart(2, '0') + ':' + String(s).padStart(2, '0');
    }
    return String(m).padStart(2, '0') + ':' + String(s).padStart(2, '0');
  }

  function escapeHtml(str) {
    var div = document.createElement('div');
    div.textContent = str || '';
    return div.innerHTML;
  }

  function showToast(message, type) {
    var container = document.getElementById('toast-container');
    if (!container) return;
    var toast = document.createElement('div');
    toast.className = 'toast ' + (type || 'info');
    toast.textContent = message;
    container.appendChild(toast);
    setTimeout(function() {
      toast.style.opacity = '0';
      toast.style.transform = 'translateX(40px)';
      setTimeout(function() { toast.remove(); }, 300);
    }, 3000);
  }

  // ---- Event Bindings ----

  function bindEvents() {
    // Prev/Next navigation
    document.getElementById('cl-nav-prev').addEventListener('click', navigatePrev);
    document.getElementById('cl-nav-next').addEventListener('click', navigateNext);

    // Sidebar toggle
    document.getElementById('cl-sidebar-toggle').addEventListener('click', toggleSidebar);
    document.getElementById('cl-sidebar-expand').addEventListener('click', toggleSidebar);

    // Content tabs
    document.querySelectorAll('.cl-content-tab').forEach(function(tab) {
      tab.addEventListener('click', function() {
        switchTab(this.getAttribute('data-tab'));
      });
    });

    // Notes auto-save
    var notesEditor = document.getElementById('cl-notes-editor');
    if (notesEditor) {
      var saveTimeout;
      notesEditor.addEventListener('input', function() {
        clearTimeout(saveTimeout);
        saveTimeout = setTimeout(saveNotes, 1000);
      });
    }

    // Keyboard shortcuts
    document.addEventListener('keydown', function(e) {
      if (e.key === 'ArrowLeft' && !e.target.closest('input, textarea')) {
        navigatePrev();
      } else if (e.key === 'ArrowRight' && !e.target.closest('input, textarea')) {
        navigateNext();
      }
    });
  }

  // ---- Init on load ----

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  // Expose
  window.CourseLearn = {
    getCourse: function() { return course; },
    getChapters: function() { return chapters; },
    selectChapter: selectChapter
  };
})();
