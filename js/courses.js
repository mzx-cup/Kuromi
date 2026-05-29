/**
 * Course Center - Khan Academy Style
 * Manages subjects/courses data, renders layout, edit modal, B站 import
 */

(function() {
  'use strict';

  var STORAGE_KEY = 'starlearn_courses_data';

  // Default subject icons
  var SUBJECT_ICONS = {
    'cs': '<svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><rect x="2" y="3" width="20" height="14" rx="2"/><path d="M8 21h8M12 17v4" stroke-linecap="round" stroke-linejoin="round"/></svg>',
    'math': '<svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path d="M4 7h16M4 12h16M4 17h16"/><path d="M8 4v16M16 4v16"/></svg>',
    'physics': '<svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><path d="M12 2a14.5 14.5 0 000 20"/></svg>',
    'default': '<svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2" stroke-linecap="round" stroke-linejoin="round"/></svg>'
  };

  var SUBJECT_COLORS = {
    'cs': { bgClass: 'cs-bg', iconClass: 'cs' },
    'math': { bgClass: 'math-bg', iconClass: 'math' },
    'physics': { bgClass: 'physics-bg', iconClass: 'physics' },
    'language': { bgClass: 'default-bg', iconClass: 'language' },
    'default': { bgClass: 'default-bg', iconClass: 'default' }
  };

  // Default data with the specified B站 collection as initial course
  function getDefaultData() {
    return {
      subjects: [
        {
          id: 'cs',
          name: '计算机科学',
          slug: 'cs',
          visible: true,
          courses: [
            {
              id: 'course-bv1ya411871j',
              title: '计算机基础入门',
              description: '完全从零掌握计算机与程序员基础知识',
              bvid: 'BV1YA411871j',
              playlistUrl: 'https://www.bilibili.com/video/BV1YA411871j',
              totalLessons: 52,
              totalDuration: 0,
              progress: 0,
              visible: true,
              createdAt: new Date().toISOString()
            }
          ]
        },
        {
          id: 'math',
          name: '数学',
          slug: 'math',
          visible: true,
          courses: []
        },
        {
          id: 'physics',
          name: '物理学',
          slug: 'physics',
          visible: true,
          courses: []
        }
      ]
    };
  }

  var data = loadData();
  var useBackend = false;

  function loadData() {
    try {
      var saved = JSON.parse(localStorage.getItem(STORAGE_KEY));
      if (saved && saved.subjects && saved.subjects.length > 0) return saved;
    } catch (e) { /* ignore */ }
    var defaults = getDefaultData();
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(defaults)); } catch (e) { /* ignore */ }
    return defaults;
  }

  function loadFromBackend() {
    fetch('/api/courses/subjects')
      .then(function(r) { return r.json(); })
      .then(function(res) {
        if (res.code === 200 && res.data && res.data.length > 0) {
          useBackend = true;
          data = { subjects: res.data };
          render();
        }
      })
      .catch(function(err) {
        console.warn('[Courses] Backend unavailable, using localStorage', err);
      });
  }

  function saveData() {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
  }

  // ---- Rendering ----

  function render() {
    var container = document.getElementById('subjects-container');
    if (!container) return;

    var visibleSubjects = data.subjects.filter(function(s) { return s.visible; });
    if (visibleSubjects.length === 0) {
      container.innerHTML = '<div class="empty-state"><div class="empty-state-icon"><svg width="64" height="64" fill="none" stroke="currentColor" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2" stroke-linecap="round" stroke-linejoin="round"/></svg></div><div class="empty-state-title">暂无课程</div><div class="empty-state-desc">点击右上角"编辑课程"按钮，通过B站导入添加课程内容</div></div>';
      return;
    }

    var html = '';
    for (var i = 0; i < visibleSubjects.length; i++) {
      var subj = visibleSubjects[i];
      var visibleCourses = subj.courses.filter(function(c) { return c.visible !== false; });
      var colorInfo = SUBJECT_COLORS[subj.slug] || SUBJECT_COLORS['default'];
      var iconSvg = SUBJECT_ICONS[subj.slug] || SUBJECT_ICONS['default'];

      html += '<section class="subject-block">';
      html += '<div class="subject-block-header">';
      html += '<div class="subject-block-icon ' + colorInfo.iconClass + '">' + iconSvg + '</div>';
      html += '<h2 class="subject-block-name">' + escapeHtml(subj.name) + '</h2>';
      html += '<span class="subject-course-count">' + visibleCourses.length + ' 门课程</span>';
      html += '</div>';

      if (visibleCourses.length === 0) {
        html += '<p style="color:var(--text-tertiary);font-size:13px;padding-left:52px;">此科目下暂无课程，点击"编辑课程"导入</p>';
      } else {
        html += '<div class="subject-courses-grid">';
        for (var j = 0; j < visibleCourses.length; j++) {
          html += renderCourseCard(visibleCourses[j], subj.slug);
        }
        html += '</div>';
      }
      html += '</section>';
    }
    container.innerHTML = html;

    // Bind course card click events
    bindCardEvents();
  }

  function renderCourseCard(course, subjectSlug) {
    var colorInfo = SUBJECT_COLORS[subjectSlug] || SUBJECT_COLORS['default'];
    var progressPercent = Math.round((course.progress || 0));
    var circumference = 2 * Math.PI * 24; // r=24
    var offset = circumference - (progressPercent / 100) * circumference;

    var html = '<div class="course-card" data-course-id="' + course.id + '" data-subject="' + subjectSlug + '">';
    html += '<div class="course-card-cover ' + colorInfo.bgClass + '">';
    html += '<div class="course-card-cover-icon">' + (SUBJECT_ICONS[subjectSlug] || SUBJECT_ICONS['default']) + '</div>';
    if (progressPercent > 0) {
      html += '<div class="course-card-progress-ring">';
      html += '<svg class="progress-ring-circle" viewBox="0 0 52 52">';
      html += '<circle class="progress-ring-bg" cx="26" cy="26" r="24"/>';
      html += '<circle class="progress-ring-fill" cx="26" cy="26" r="24" stroke-dasharray="' + circumference + '" stroke-dashoffset="' + offset + '"/>';
      html += '<text class="progress-ring-text" x="26" y="26">' + progressPercent + '%</text>';
      html += '</svg></div>';
    }
    html += '</div>';
    html += '<div class="course-card-body">';
    html += '<h3 class="course-card-title">' + escapeHtml(course.title) + '</h3>';
    html += '<div class="course-card-meta">';
    html += '<span>' + (course.totalLessons || 0) + ' 课时</span>';
    html += '</div>';
    html += '<div class="course-card-footer">';
    if (progressPercent > 0) {
      html += '<button class="course-card-btn continue">继续学习</button>';
    } else {
      html += '<button class="course-card-btn start">开始学习</button>';
    }
    html += '</div>';
    html += '</div>';
    html += '</div>';
    return html;
  }

  function bindCardEvents() {
    var cards = document.querySelectorAll('.course-card');
    cards.forEach(function(card) {
      card.addEventListener('click', function() {
        var courseId = this.getAttribute('data-course-id');
        var subjectSlug = this.getAttribute('data-subject');
        var course = findCourse(courseId);
        if (course && course.bvid) {
          window.location.href = '/course-learn.html?courseId=' + courseId + '&subject=' + subjectSlug;
        }
      });
    });
  }

  function findCourse(courseId) {
    for (var i = 0; i < data.subjects.length; i++) {
      var courses = data.subjects[i].courses;
      for (var j = 0; j < courses.length; j++) {
        if (courses[j].id === courseId) return courses[j];
      }
    }
    return null;
  }

  function findSubject(subjectId) {
    for (var i = 0; i < data.subjects.length; i++) {
      if (data.subjects[i].id === subjectId) return data.subjects[i];
    }
    return null;
  }

  // ---- Edit Courses Modal ----

  function openEditModal() {
    var modal = document.getElementById('edit-courses-modal');
    if (!modal) return;
    modal.classList.remove('hidden');
    renderEditBody();
    bindEditEvents();
  }

  function closeEditModal() {
    var modal = document.getElementById('edit-courses-modal');
    if (modal) modal.classList.add('hidden');
  }

  function renderEditBody() {
    var body = document.getElementById('edit-body');
    if (!body) return;

    var html = '';
    for (var i = 0; i < data.subjects.length; i++) {
      var subj = data.subjects[i];
      html += '<div class="edit-subject-row" data-subject-id="' + subj.id + '">';
      html += '<div class="edit-subject-header">';
      html += '<button class="edit-subject-toggle' + (subj.visible ? ' on' : '') + '" data-action="toggle-subject" data-subject-id="' + subj.id + '"></button>';
      html += '<span class="edit-subject-name">' + escapeHtml(subj.name) + '</span>';
      html += '<button class="edit-subject-hide-btn" data-action="hide-subject" data-subject-id="' + subj.id + '">' + (subj.visible ? '隐藏科目' : '显示科目') + '</button>';
      html += '<button class="edit-subject-import-btn" data-action="import-subject" data-subject-id="' + subj.id + '">B站导入</button>';
      html += '</div>';

      if (subj.courses.length > 0) {
        html += '<div class="edit-course-list">';
        for (var j = 0; j < subj.courses.length; j++) {
          var c = subj.courses[j];
          html += '<div class="edit-course-row" data-course-id="' + c.id + '">';
          html += '<button class="edit-course-toggle' + (c.visible !== false ? ' on' : '') + '" data-action="toggle-course" data-course-id="' + c.id + '"></button>';
          html += '<span class="edit-course-name">' + escapeHtml(c.title) + '</span>';
          html += '<button class="edit-course-remove-btn" data-action="remove-course" data-course-id="' + c.id + '">移除</button>';
          html += '</div>';
        }
        html += '</div>';
      }

      html += '</div>';
    }
    body.innerHTML = html;
  }

  function bindEditEvents() {
    // Toggle subject visibility
    document.querySelectorAll('[data-action="toggle-subject"]').forEach(function(btn) {
      btn.addEventListener('click', function() {
        var subjectId = this.getAttribute('data-subject-id');
        var subj = findSubject(subjectId);
        if (subj) {
          subj.visible = !subj.visible;
          this.classList.toggle('on', subj.visible);
          var hideBtn = this.parentElement.querySelector('[data-action="hide-subject"]');
          if (hideBtn) hideBtn.textContent = subj.visible ? '隐藏科目' : '显示科目';
        }
      });
    });

    // Toggle course visibility
    document.querySelectorAll('[data-action="toggle-course"]').forEach(function(btn) {
      btn.addEventListener('click', function() {
        var courseId = this.getAttribute('data-course-id');
        var course = findCourse(courseId);
        if (course) {
          course.visible = course.visible === false ? true : false;
          this.classList.toggle('on', course.visible);
        }
      });
    });

    // Remove course
    document.querySelectorAll('[data-action="remove-course"]').forEach(function(btn) {
      btn.addEventListener('click', function() {
        var courseId = this.getAttribute('data-course-id');
        if (confirm('确定要移除此课程吗？')) {
          removeCourse(courseId);
          renderEditBody();
          bindEditEvents();
        }
      });
    });

    // Import for subject
    document.querySelectorAll('[data-action="import-subject"]').forEach(function(btn) {
      btn.addEventListener('click', function() {
        var subjectId = this.getAttribute('data-subject-id');
        closeEditModal();
        openBilibiliImport(subjectId);
      });
    });
  }

  function removeCourse(courseId) {
    for (var i = 0; i < data.subjects.length; i++) {
      data.subjects[i].courses = data.subjects[i].courses.filter(function(c) { return c.id !== courseId; });
    }
    saveData();
  }

  function openBilibiliImport(subjectId) {
    if (typeof BilibiliImport !== 'undefined') {
      BilibiliImport.open(subjectId, function() {
        data = loadData();
        render();
        closeEditModal();
      });
    } else {
      showToast('B站导入模块加载中...', 'info');
    }
  }

  // Add new subject
  function addSubject() {
    var name = prompt('请输入新科目名称：');
    if (!name || !name.trim()) return;
    var slug = 'subject-' + Date.now();
    data.subjects.push({
      id: slug,
      name: name.trim(),
      slug: slug,
      visible: true,
      courses: []
    });
    saveData();
    renderEditBody();
    bindEditEvents();
  }

  function escapeHtml(str) {
    var div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }

  function showToast(message, type) {
    type = type || 'info';
    var container = document.getElementById('toast-container');
    if (!container) return;
    var toast = document.createElement('div');
    toast.className = 'toast ' + type;
    toast.textContent = message;
    container.appendChild(toast);
    setTimeout(function() {
      toast.style.opacity = '0';
      toast.style.transform = 'translateX(40px)';
      setTimeout(function() { toast.remove(); }, 300);
    }, 3000);
  }

  // ---- Init ----

  function init() {
    render();
    loadFromBackend();

    // Edit courses button
    var editBtn = document.getElementById('courses-edit-btn');
    if (editBtn) {
      editBtn.addEventListener('click', openEditModal);
    }

    // Edit modal close
    var editClose = document.getElementById('edit-close');
    if (editClose) {
      editClose.addEventListener('click', closeEditModal);
    }

    // Edit modal overlay click to close
    var editModal = document.getElementById('edit-courses-modal');
    if (editModal) {
      editModal.addEventListener('click', function(e) {
        if (e.target === editModal) closeEditModal();
      });
    }

    // Done button
    var doneBtn = document.getElementById('edit-done');
    if (doneBtn) {
      doneBtn.addEventListener('click', function() {
        saveData();
        render();
        closeEditModal();
      });
    }

    // Add subject button
    var addBtn = document.getElementById('edit-add-subject');
    if (addBtn) {
      addBtn.addEventListener('click', addSubject);
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  // Expose
  window.CoursesCenter = {
    render: render,
    getData: function() { return data; },
    reload: function() { data = loadData(); render(); },
    findCourse: findCourse,
    findSubject: findSubject
  };
})();
