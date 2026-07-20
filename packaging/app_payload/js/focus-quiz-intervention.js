/**
 * FocusQuizIntervention — 专注检测驱动的主动测验干预
 *
 * Listens to FocusAnalysis realtime-changed events, tracks consecutive
 * distraction states, enforces cooldown, fetches quiz questions from
 * /api/focus/quiz, and injects interactive quiz cards into the chat.
 */
(function () {
  'use strict';

  // ── Configuration ──
  var COOLDOWN_MS = 8 * 60 * 1000;
  var CONSECUTIVE_THRESHOLD = 2;
  var CHECK_INTERVAL_MS = 3000;
  var API_BASE = window.location.origin;
  var QUIZ_ENDPOINT = API_BASE + '/api/focus/quiz';

  // ── State ──
  var _lastInterventionTime = 0;
  var _distractedCount = 0;
  var _checkTimer = null;
  var _isActive = false;
  var _currentQuizData = null;
  var _answeredQuestions = {};
  var _quizAnswered = false;

  // ── helpers ──

  function isCooldownActive() {
    return (Date.now() - _lastInterventionTime) < COOLDOWN_MS;
  }

  function escapeHtml(text) {
    if (!text) return '';
    var div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  function getUserId() {
    try {
      var user = JSON.parse(localStorage.getItem('starlearn_user') || '{}');
      return user.id || null;
    } catch (e) { return null; }
  }

  function getRecentContext() {
    if (typeof messages === 'undefined') return '';
    var recent = messages.slice(-3);
    return recent.map(function (m) {
      var content = m.content || '';
      return content.substring(0, 200);
    }).join('\n');
  }

  function getCurrentTopics() {
    if (typeof currentPath === 'undefined' || !currentPath || !currentPath.length) {
      return ['当前学习内容'];
    }
    return currentPath
      .filter(function (n) { return n.status === 'current' || n.status === 'in_progress'; })
      .map(function (n) { return n.topic || n.name || n.title || ''; })
      .filter(Boolean);
  }

  // ── API ──

  function fetchQuiz() {
    var userId = getUserId();
    if (!userId) return Promise.resolve(null);

    var topics = getCurrentTopics();
    var context = getRecentContext();

    return fetch(QUIZ_ENDPOINT, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user_id: parseInt(userId, 10),
        topics: topics.length ? topics : ['当前学习内容'],
        context: context,
        course_id: (
          (typeof currentUser !== 'undefined' && currentUser.currentTask) ||
          'bigdata'
        )
      })
    })
    .then(function (resp) {
      if (!resp.ok) throw new Error('HTTP ' + resp.status);
      return resp.json();
    })
    .then(function (data) {
      if (data.success === false) return null;
      return data;
    })
    .catch(function (err) {
      console.warn('[FocusQuiz] Fetch quiz failed:', err.message);
      return null;
    });
  }

  // ── quiz interaction ──

  function handleOptionClick(optionEl, cardEl) {
    var questionId = parseInt(cardEl.dataset.questionId, 10);
    var selectedIdx = parseInt(optionEl.dataset.optionIndex, 10);

    if (_answeredQuestions[questionId] !== undefined) return;
    if (!_currentQuizData || !_currentQuizData.questions) return;

    var question = _currentQuizData.questions.find(function (q) { return q.id === questionId; });
    if (!question) return;

    var isCorrect = (selectedIdx === question.correct);
    _answeredQuestions[questionId] = selectedIdx;

    // Highlight selected & correct
    var allOptions = cardEl.querySelectorAll('.focus-quiz-option');
    for (var i = 0; i < allOptions.length; i++) {
      var opt = allOptions[i];
      opt.style.pointerEvents = 'none';
      var idx = parseInt(opt.dataset.optionIndex, 10);
      if (idx === selectedIdx) {
        opt.classList.add(isCorrect ? 'focus-quiz-correct' : 'focus-quiz-wrong');
      }
      if (idx === question.correct && idx !== selectedIdx) {
        opt.classList.add('focus-quiz-correct');
      }
    }

    // Show explanation
    var feedbackEl = cardEl.querySelector('.focus-quiz-feedback');
    if (feedbackEl) {
      feedbackEl.textContent = (isCorrect ? '✓ 正确！' : '✗ 不对哦，') + question.explanation;
      feedbackEl.classList.add(isCorrect ? 'focus-quiz-feedback-correct' : 'focus-quiz-feedback-wrong');
      feedbackEl.style.display = 'block';
    }

    checkAllAnswered();
  }

  function checkAllAnswered() {
    if (!_currentQuizData || !_currentQuizData.questions) return;
    var total = _currentQuizData.questions.length;
    var answered = Object.keys(_answeredQuestions).length;

    if (answered >= total && !_quizAnswered) {
      _quizAnswered = true;
      var correctCount = 0;
      _currentQuizData.questions.forEach(function (q) {
        if (_answeredQuestions[q.id] === q.correct) correctCount++;
      });

      var summaryText = correctCount === total
        ? '太棒了！你全部答对了，继续保持专注！'
        : '完成了！答对了 ' + correctCount + '/' + total + ' 题，再接再厉！';

      if (typeof messages !== 'undefined') {
        messages.push({
          role: 'assistant',
          content: summaryText,
          _isProactive: true,
          _persona: 'patient_tutor',
          _agentId: 'focus_quiz',
          _agentName: '专注助手',
          _timestamp: Date.now()
        });
        if (typeof renderMessages === 'function') renderMessages();
      }
    }
  }

  function attachQuizListeners() {
    var quizCards = document.querySelectorAll('.focus-quiz-card');
    for (var i = 0; i < quizCards.length; i++) {
      var card = quizCards[i];
      var options = card.querySelectorAll('.focus-quiz-option');
      for (var j = 0; j < options.length; j++) {
        var opt = options[j];
        // Replace with clone to remove old listeners
        var newOpt = opt.cloneNode(true);
        opt.parentNode.replaceChild(newOpt, opt);
        (function (optionEl, cardEl) {
          newOpt.addEventListener('click', function () {
            handleOptionClick(optionEl, cardEl);
          });
        })(newOpt, card);
      }
    }
  }

  function injectQuizCards() {
    if (typeof messages === 'undefined') return;

    for (var i = 0; i < messages.length; i++) {
      var msg = messages[i];
      if (!msg._quizData || !msg._quizData.questions) continue;

      var msgRow = document.querySelector('.msg-row[data-msg-id="' + (msg._timestamp || '') + '"]');
      if (!msgRow) continue;

      var bubble = msgRow.querySelector('.msg-bubble');
      if (!bubble) continue;

      // Guard: already injected
      if (bubble.querySelector('.focus-quiz-container')) continue;

      var quizData = msg._quizData;
      var labels = ['A', 'B', 'C', 'D'];
      var quizHtml = '<div class="focus-quiz-container">';

      for (var q = 0; q < quizData.questions.length; q++) {
        var qData = quizData.questions[q];
        var alreadyAnswered = _answeredQuestions[qData.id] !== undefined;
        var selectedIdx = _answeredQuestions[qData.id];
        var isCorrectSelection = (selectedIdx === qData.correct);

        quizHtml += '<div class="focus-quiz-card" data-question-id="' + qData.id + '">';
        quizHtml += '<div class="focus-quiz-question-text">' + escapeHtml(qData.question) + '</div>';
        quizHtml += '<div class="focus-quiz-options">';

        for (var oi = 0; oi < qData.options.length; oi++) {
          var extraClass = '';
          if (alreadyAnswered) {
            if (oi === qData.correct) extraClass += ' focus-quiz-correct';
            if (oi === selectedIdx && !isCorrectSelection) extraClass += ' focus-quiz-wrong';
          }
          quizHtml += '<div class="focus-quiz-option' + extraClass + '" data-option-index="' + oi + '"' +
            (alreadyAnswered ? ' style="pointer-events:none;"' : '') + '>';
          quizHtml += '<span class="focus-quiz-option-key">' + (labels[oi] || oi + 1) + '</span>';
          quizHtml += '<span class="focus-quiz-option-text">' + escapeHtml(qData.options[oi]) + '</span>';
          quizHtml += '</div>';
        }

        quizHtml += '</div>';
        quizHtml += '<div class="focus-quiz-feedback" style="display:' +
          (alreadyAnswered ? 'block' : 'none') + ';">';
        if (alreadyAnswered) {
          quizHtml += (isCorrectSelection ? '✓ 正确！' : '✗ 不对哦，') +
            escapeHtml(qData.explanation || '');
        }
        quizHtml += '</div>';
        quizHtml += '</div>';
      }

      quizHtml += '</div>';
      bubble.insertAdjacentHTML('beforeend', quizHtml);
    }

    attachQuizListeners();
  }

  // ── monkey-patch renderMessages ──

  var _origRenderMessages = null;
  var _patched = false;

  function patchRenderMessages() {
    if (_patched || typeof renderMessages !== 'function') return false;
    _origRenderMessages = renderMessages;
    _patched = true;

    window.renderMessages = async function () {
      await _origRenderMessages();
      try {
        injectQuizCards();
      } catch (e) { /* ignore */ }
    };
    return true;
  }

  // ── trigger ──

  function triggerIntervention() {
    if (!_isActive || isCooldownActive()) return;

    _lastInterventionTime = Date.now();
    _distractedCount = 0;
    _quizAnswered = false;
    _answeredQuestions = {};

    fetchQuiz().then(function (quizData) {
      if (!quizData || !quizData.questions || !quizData.questions.length) return;

      _currentQuizData = quizData;

      if (typeof messages !== 'undefined') {
        messages.push({
          role: 'assistant',
          content: quizData.reminder || '检测到你可能有些分心，来做几道小题目提提神吧！',
          _isProactive: true,
          _quizData: quizData,
          _persona: 'patient_tutor',
          _agentId: 'focus_quiz',
          _agentName: '专注助手',
          _timestamp: Date.now()
        });
        if (typeof renderMessages === 'function') renderMessages();
      }
    });
  }

  // ── focus check ──

  function checkFocusState() {
    if (!_isActive || _quizAnswered) return;
    if (!window.FocusAnalysis) return;

    var state = window.FocusAnalysis.getRealtimeState();
    if (!state) return;

    if (state.state === 'distracted' && state.confidence > 0.5) {
      _distractedCount++;
      if (_distractedCount >= CONSECUTIVE_THRESHOLD && !isCooldownActive()) {
        triggerIntervention();
      }
    } else if (state.state === 'focused') {
      _distractedCount = 0;
    }
    // 'lightly': maintain current count, don't increment or reset
  }

  // ── public API ──

  function start() {
    if (_isActive) return;
    _isActive = true;

    // Ensure patch is applied
    if (!patchRenderMessages()) {
      // renderMessages not available yet, retry
      var retryCount = 0;
      var retryTimer = setInterval(function () {
        retryCount++;
        if (patchRenderMessages() || retryCount > 30) {
          clearInterval(retryTimer);
        }
      }, 500);
    }

    // Start FocusAnalysis polling
    if (window.FocusAnalysis && typeof window.FocusAnalysis.startPolling === 'function') {
      window.FocusAnalysis.startPolling(5000);
    }

    // Subscribe to realtime changes
    if (window.FocusAnalysis && typeof window.FocusAnalysis.on === 'function') {
      window.FocusAnalysis.on('realtime-changed', function (state) {
        if (!_isActive || _quizAnswered) return;
        if (state.state === 'distracted' && state.confidence > 0.5) {
          _distractedCount++;
          if (_distractedCount >= CONSECUTIVE_THRESHOLD && !isCooldownActive()) {
            triggerIntervention();
          }
        } else if (state.state === 'focused') {
          _distractedCount = 0;
        }
      });
    }

    // Periodic fallback check
    if (_checkTimer) clearInterval(_checkTimer);
    _checkTimer = setInterval(checkFocusState, CHECK_INTERVAL_MS);
  }

  function stop() {
    _isActive = false;
    if (_checkTimer) {
      clearInterval(_checkTimer);
      _checkTimer = null;
    }
    _distractedCount = 0;
  }

  function resetCooldown() {
    _lastInterventionTime = 0;
    _distractedCount = 0;
    _quizAnswered = false;
    _answeredQuestions = {};
    _currentQuizData = null;
  }

  // ── init ──

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function () {
      setTimeout(function () { patchRenderMessages(); }, 2000);
    });
  } else {
    setTimeout(function () { patchRenderMessages(); }, 2000);
  }

  window.FocusQuizIntervention = {
    start: start,
    stop: stop,
    resetCooldown: resetCooldown,
    triggerIntervention: triggerIntervention
  };
})();
