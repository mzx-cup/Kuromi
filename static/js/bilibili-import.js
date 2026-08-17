/**
 * Bilibili Video Import Modal
 * Three tabs: Paste Links / Search / Playlist Import
 */

(function() {
  'use strict';

  var currentSubjectId = null;
  var onComplete = null;
  var parsedVideos = [];
  var searchItems = [];
  var playlistItems = [];
  var selectedBvids = [];
  var importing = false;
  var isPlaylistMode = false;
  var playlistCourseName = '';

  // ---- API calls (use fetch to backend) ----

  function api(path, body) {
    return fetch('/api/bilibili' + path, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    }).then(function(r) {
      if (!r.ok) throw new Error('API error ' + r.status);
      return r.json();
    });
  }

  function parseBilibiliUrl(url) {
    var match = url.match(/BV[a-zA-Z0-9]{10}/);
    return match ? match[0] : null;
  }

  function formatDuration(seconds) {
    if (!seconds) return '--:--';
    var m = Math.floor(seconds / 60);
    var s = seconds % 60;
    return m + ':' + String(s).padStart(2, '0');
  }

  function formatPlayCount(n) {
    if (!n) return '0';
    if (n >= 10000) return (n / 10000).toFixed(1) + '万';
    return String(n);
  }

  function fixUrl(url) {
    if (!url) return '';
    if (url.startsWith('//')) return 'https:' + url;
    return url;
  }

  function escapeHtml(str) {
    var div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }

  // ---- Open ----

  function open(subjectId, callback) {
    currentSubjectId = subjectId;
    onComplete = callback;
    resetState();

    var modal = document.getElementById('bilibili-import-modal');
    if (!modal) return;
    modal.classList.remove('hidden');

    // Set initial tab
    switchTab('link');
    bindEvents();
  }

  function close() {
    var modal = document.getElementById('bilibili-import-modal');
    if (modal) modal.classList.add('hidden');
    if (onComplete) onComplete();
  }

  function resetState() {
    parsedVideos = [];
    searchItems = [];
    playlistItems = [];
    selectedBvids = [];
    importing = false;
    isPlaylistMode = false;
    playlistCourseName = '';
    document.getElementById('im-link-text').value = '';
    document.getElementById('im-search-input').value = '';
    document.getElementById('im-playlist-url').value = '';
    document.getElementById('im-link-results').classList.add('hidden');
    document.getElementById('im-search-results').classList.add('hidden');
    document.getElementById('im-playlist-results').classList.add('hidden');
  }

  function switchTab(tabName) {
    document.querySelectorAll('.im-tab').forEach(function(t) {
      t.classList.toggle('active', t.getAttribute('data-tab') === tabName);
    });
    document.getElementById('im-tab-link').classList.toggle('hidden', tabName !== 'link');
    document.getElementById('im-tab-search').classList.toggle('hidden', tabName !== 'search');
    document.getElementById('im-tab-playlist').classList.toggle('hidden', tabName !== 'playlist');
  }

  // ---- Tab 1: Paste Links ----

  function parseLinks() {
    var text = document.getElementById('im-link-text').value;
    var urls = text.split('\n').filter(function(l) { return l.trim(); });
    if (urls.length === 0) return;

    var resultsDiv = document.getElementById('im-link-results');
    resultsDiv.classList.remove('hidden');
    resultsDiv.innerHTML = '<p style="color:rgba(255,255,255,0.4);font-size:12px;">解析中...</p>';

    isPlaylistMode = false;
    parsedVideos = [];
    selectedBvids = [];

    var promises = urls.map(function(url) {
      return api('/parse', { url: url.trim() }).catch(function() { return null; });
    });

    Promise.all(promises).then(function(results) {
      parsedVideos = [];
      for (var i = 0; i < results.length; i++) {
        var r = results[i];
        if (r && r.data && r.data.bvid) {
          parsedVideos.push(r.data);
          selectedBvids.push(r.data.bvid);
        }
      }
      renderParsedVideos(resultsDiv);
    });
  }

  function renderParsedVideos(container) {
    if (parsedVideos.length === 0) {
      container.innerHTML = '<p style="color:rgba(255,255,255,0.3);font-size:12px;">未解析到视频，请检查链接格式</p>';
      return;
    }
    var html = '<div style="font-size:10px;text-transform:uppercase;letter-spacing:1px;color:rgba(255,255,255,0.3);margin-bottom:10px;">解析结果 (' + parsedVideos.length + ' 个)</div>';
    for (var i = 0; i < parsedVideos.length; i++) {
      var v = parsedVideos[i];
      html += renderVideoRow(v, true);
    }
    html += '<button class="im-btn primary" id="im-import-parsed"' + (importing ? ' disabled' : '') + '>' + (importing ? '导入中...' : '一键导入 ' + selectedBvids.length + ' 个视频') + '</button>';
    container.innerHTML = html;

    document.getElementById('im-import-parsed').addEventListener('click', function() {
      doImport(selectedBvids);
    });
  }

  function renderVideoRow(v, showCheckbox) {
    var html = '<div class="im-video-row">';
    if (showCheckbox) {
      html += '<input type="checkbox" class="im-checkbox" value="' + escapeHtml(v.bvid) + '" ' + (selectedBvids.indexOf(v.bvid) !== -1 ? 'checked' : '') + '>';
    }
    html += '<div class="im-cover-wrap">';
    if (v.coverUrl) {
      html += '<img src="' + fixUrl(v.coverUrl) + '" class="im-cover" loading="lazy" onerror="this.style.display=\'none\'">';
    } else {
      html += '<div class="im-cover-placeholder"></div>';
    }
    html += '</div>';
    html += '<div class="im-video-info">';
    html += '<div class="im-video-title">' + escapeHtml(v.title || v.partTitle || '') + '</div>';
    html += '<div class="im-video-meta">' + (v.bvid || '') + ' | ' + formatDuration(v.duration) + (v.authorName ? ' | ' + escapeHtml(v.authorName) : '') + '</div>';
    html += '</div>';
    html += '</div>';
    return html;
  }

  // ---- Tab 2: Search ----

  function doSearch() {
    var keyword = document.getElementById('im-search-input').value.trim();
    if (!keyword) return;

    var resultsDiv = document.getElementById('im-search-results');
    resultsDiv.classList.remove('hidden');
    resultsDiv.innerHTML = '<p style="color:rgba(255,255,255,0.4);font-size:12px;">搜索中...</p>';

    isPlaylistMode = false;

    api('/search', { keyword: keyword, page: 1, pageSize: 10 }).then(function(res) {
      searchItems = res.data.items || [];
      selectedBvids = searchItems.map(function(v) { return v.bvid; });
      renderSearchResults(resultsDiv);
    }).catch(function() {
      resultsDiv.innerHTML = '<p style="color:rgba(255,255,255,0.3);font-size:12px;">搜索失败</p>';
    });
  }

  function renderSearchResults(container) {
    if (searchItems.length === 0) {
      container.innerHTML = '<p style="color:rgba(255,255,255,0.3);font-size:12px;">未找到结果</p>';
      return;
    }
    var html = '<div style="font-size:10px;text-transform:uppercase;letter-spacing:1px;color:rgba(255,255,255,0.3);margin-bottom:10px;">搜索结果</div>';
    for (var i = 0; i < searchItems.length; i++) {
      var v = searchItems[i];
      html += '<div class="im-video-row">';
      html += '<input type="checkbox" class="im-checkbox" value="' + escapeHtml(v.bvid) + '" checked>';
      html += '<div class="im-cover-wrap">';
      if (v.coverUrl) {
        html += '<img src="' + fixUrl(v.coverUrl) + '" class="im-cover" loading="lazy" onerror="this.style.display=\'none\'">';
      } else {
        html += '<div class="im-cover-placeholder"></div>';
      }
      html += '</div>';
      html += '<div class="im-video-info">';
      html += '<div class="im-video-title">' + escapeHtml(v.title) + '</div>';
      html += '<div class="im-video-meta">' + formatDuration(v.duration) + ' | ' + formatPlayCount(v.playCount) + '播放 | ' + escapeHtml(v.authorName) + '</div>';
      html += '</div>';
      html += '</div>';
    }
    html += '<button class="im-btn primary" id="im-import-search"' + (importing ? ' disabled' : '') + '>' + (importing ? '导入中...' : '导入选中视频（' + selectedBvids.length + '）') + '</button>';
    container.innerHTML = html;

    // Checkbox change events
    container.querySelectorAll('.im-checkbox').forEach(function(cb) {
      cb.addEventListener('change', function() {
        selectedBvids = [];
        container.querySelectorAll('.im-checkbox:checked').forEach(function(c) { selectedBvids.push(c.value); });
      });
    });

    document.getElementById('im-import-search').addEventListener('click', function() {
      doImport(selectedBvids);
    });
  }

  // ---- Tab 3: Playlist ----

  function parsePlaylist() {
    var url = document.getElementById('im-playlist-url').value.trim();
    if (!url) return;

    var resultsDiv = document.getElementById('im-playlist-results');
    resultsDiv.classList.remove('hidden');
    resultsDiv.innerHTML = '<p style="color:rgba(255,255,255,0.4);font-size:12px;">解析合集中...</p>';

    api('/playlist', { url: url }).then(function(res) {
      playlistItems = res.data || [];
      if (playlistItems.length > 0) {
        isPlaylistMode = true;
        playlistCourseName = playlistItems[0].title || '';
        selectedBvids = playlistItems.map(function(v) { return v.bvid; });
      }
      renderPlaylistResults(resultsDiv);
    }).catch(function() {
      resultsDiv.innerHTML = '<p style="color:rgba(255,255,255,0.3);font-size:12px;">合集解析失败</p>';
    });
  }

  function renderPlaylistResults(container) {
    if (playlistItems.length === 0) {
      container.innerHTML = '<p style="color:rgba(255,255,255,0.3);font-size:12px;">未解析到视频</p>';
      return;
    }
    var html = '<div style="font-size:10px;text-transform:uppercase;letter-spacing:1px;color:rgba(255,255,255,0.3);margin-bottom:10px;">共 ' + playlistItems.length + ' 个视频</div>';
    for (var i = 0; i < playlistItems.length; i++) {
      var v = playlistItems[i];
      html += '<div class="im-video-row">';
      html += '<input type="checkbox" class="im-checkbox" value="' + escapeHtml(v.bvid) + '" checked>';
      html += '<div class="im-cover-wrap">';
      if (v.coverUrl) {
        html += '<img src="' + fixUrl(v.coverUrl) + '" class="im-cover" loading="lazy" onerror="this.style.display=\'none\'">';
      } else {
        html += '<div class="im-cover-placeholder"></div>';
      }
      html += '</div>';
      html += '<div class="im-video-info">';
      html += '<div class="im-video-title">' + escapeHtml(v.title) + '</div>';
      html += '<div class="im-video-meta">' + formatDuration(v.duration) + '</div>';
      html += '</div>';
      html += '</div>';
    }

    html += '<div class="im-course-name-row" style="margin-bottom:14px;">';
    html += '<label style="display:block;font-size:11px;color:rgba(255,255,255,0.4);margin-bottom:6px;">课程名称（将作为合集名称创建一门新课）</label>';
    html += '<input type="text" class="im-course-input" id="im-course-name" value="' + escapeHtml(playlistCourseName) + '" placeholder="输入课程名称...">';
    html += '</div>';

    html += '<button class="im-btn primary" id="im-import-playlist"' + (importing ? ' disabled' : '') + '>' + (importing ? '导入中...' : '导入为课程 | ' + selectedBvids.length + ' 个视频') + '</button>';
    container.innerHTML = html;

    container.querySelectorAll('.im-checkbox').forEach(function(cb) {
      cb.addEventListener('change', function() {
        selectedBvids = [];
        container.querySelectorAll('.im-checkbox:checked').forEach(function(c) { selectedBvids.push(c.value); });
      });
    });

    document.getElementById('im-import-playlist').addEventListener('click', function() {
      var courseName = document.getElementById('im-course-name').value.trim() || playlistCourseName;
      doImportPlaylist(selectedBvids, courseName);
    });
  }

  // ---- Import ----

  function doImport(bvids) {
    if (bvids.length === 0 || importing) return;
    importing = true;

    var results = [];
    var promises = bvids.map(function(bvid) {
      return fetch('/api/courses/import-bilibili', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ bvid: bvid, subject_id: currentSubjectId })
      }).then(function(r) { return r.json(); });
    });

    Promise.all(promises).then(function(responses) {
      importing = false;
      // Save imported courses to localStorage
      for (var i = 0; i < responses.length; i++) {
        if (responses[i] && responses[i].code === 200) {
          saveImportedCourse(responses[i].data);
        }
      }
      close();
      if (onComplete) onComplete();
      window.location.reload();
    }).catch(function() {
      importing = false;
      showToast('导入失败，请重试', 'error');
    });
  }

  function doImportPlaylist(bvids, courseName) {
    if (bvids.length === 0 || importing) return;
    importing = true;

    var playlistUrl = document.getElementById('im-playlist-url').value.trim();

    fetch('/api/courses/import-playlist', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ playlist_url: playlistUrl, subject_id: currentSubjectId, course_name: courseName })
    })
    .then(function(r) { return r.json(); })
    .then(function(res) {
      importing = false;
      if (res && res.code === 200) {
        saveImportedCourse({ courseId: res.data.courseId, title: res.data.title, bvid: '', lessons: res.data.lessons || 0 });
      }
      close();
      if (onComplete) onComplete();
      window.location.reload();
    }).catch(function() {
      importing = false;
      showToast('导入失败，请重试', 'error');
    });
  }

  function saveImportedCourse(courseData) {
    if (!courseData) return;
    try {
      var storageKey = 'starlearn_courses_data';
      var data = JSON.parse(localStorage.getItem(storageKey)) || { subjects: [] };
      if (!data.subjects) data.subjects = [];

      // Find or create the subject
      var subject = null;
      for (var i = 0; i < data.subjects.length; i++) {
        if (data.subjects[i].id === currentSubjectId) {
          subject = data.subjects[i];
          break;
        }
      }
      if (!subject) {
        subject = { id: currentSubjectId, name: currentSubjectId, slug: currentSubjectId, visible: true, courses: [] };
        data.subjects.push(subject);
      }
      if (!subject.courses) subject.courses = [];

      // Check if course already exists
      var exists = false;
      for (var j = 0; j < subject.courses.length; j++) {
        if (subject.courses[j].id === courseData.courseId) { exists = true; break; }
      }
      if (!exists) {
        subject.courses.push({
          id: courseData.courseId,
          title: courseData.title,
          bvid: courseData.bvid,
          totalLessons: courseData.lessons || 1,
          totalDuration: 0,
          progress: 0,
          visible: true,
          createdAt: new Date().toISOString()
        });
        localStorage.setItem(storageKey, JSON.stringify(data));
      }
    } catch (e) { /* ignore */ }
  }

  function addCourseFromImport(bvids, results) {
    // Deprecated: backend now handles course creation directly
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
    // Tab switching
    document.querySelectorAll('.im-tab').forEach(function(tab) {
      tab.addEventListener('click', function() {
        switchTab(this.getAttribute('data-tab'));
      });
    });

    // Close
    var closeBtn = document.getElementById('im-close');
    if (closeBtn) {
      closeBtn.addEventListener('click', close);
    }

    // Overlay click
    var modal = document.getElementById('bilibili-import-modal');
    if (modal) {
      modal.addEventListener('click', function(e) {
        if (e.target === modal) close();
      });
    }

    // Parse link
    var parseBtn = document.getElementById('im-link-parse');
    if (parseBtn) {
      parseBtn.addEventListener('click', parseLinks);
    }

    // Search
    var searchBtn = document.getElementById('im-search-btn');
    if (searchBtn) {
      searchBtn.addEventListener('click', doSearch);
    }
    var searchInput = document.getElementById('im-search-input');
    if (searchInput) {
      searchInput.addEventListener('keydown', function(e) {
        if (e.key === 'Enter') doSearch();
      });
    }

    // Playlist
    var playlistBtn = document.getElementById('im-playlist-parse');
    if (playlistBtn) {
      playlistBtn.addEventListener('click', parsePlaylist);
    }
  }

  // ---- Public API ----

  window.BilibiliImport = {
    open: open,
    close: close
  };
})();
