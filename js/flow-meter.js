/**
 * FlowMeter — 心流共振仪
 * 使用 FocusAnalysis 共享模块 + ECharts 驱动所有面板
 */
(function () {
  'use strict';

  var _waveformChart = null;
  var _timeOfDayChart = null;
  var _historyChart = null;
  var _filterRange = 'week';
  var _resizeObserver = null;

  // ============ helpers ============

  // 从 CSS 自定义属性读取颜色，与 tokens.css 主题保持一致
  var _tokenColors = null;
  function tok(name) {
    if (!_tokenColors) {
      var s = getComputedStyle(document.documentElement);
      _tokenColors = {
        success: s.getPropertyValue('--success').trim() || '#10b981',
        warning: s.getPropertyValue('--warning').trim() || '#f59e0b',
        danger:  s.getPropertyValue('--danger').trim()  || '#ef4444',
        info:    s.getPropertyValue('--info').trim()    || '#06b6d4',
        brand:   s.getPropertyValue('--brand-500').trim() || '#6366f1',
        text:    s.getPropertyValue('--text-heading').trim() || '#fff',
        muted:   s.getPropertyValue('--text-muted').trim() || 'rgba(255,255,255,0.4)',
        border:  s.getPropertyValue('--border-glass').trim() || 'rgba(255,255,255,0.06)'
      };
    }
    return _tokenColors[name];
  }

  // 主题切换时需要重新读取
  function refreshTokens() { _tokenColors = null; }

  function formatMinutes(mins) {
    var h = Math.floor(mins / 60);
    var m = mins % 60;
    return h > 0
      ? h + ':' + String(m).padStart(2, '0') + ':00'
      : String(m).padStart(2, '0') + ':00';
  }

  function escapeHtml(str) {
    var div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }

  function timeLabel(ts) {
    var d = new Date(ts);
    return String(d.getHours()).padStart(2, '0') + ':' +
      String(d.getMinutes()).padStart(2, '0');
  }

  // ============ chart init ============

  function initCharts() {
    var wf = document.getElementById('waveform-chart');
    var td = document.getElementById('timeofday-chart');
    var hs = document.getElementById('history-chart');

    if (wf) { _waveformChart = echarts.init(wf); }
    if (td) { _timeOfDayChart = echarts.init(td); }
    if (hs) { _historyChart = echarts.init(hs); }

    if (_resizeObserver) { _resizeObserver.disconnect(); }
    _resizeObserver = new ResizeObserver(function () {
      if (_waveformChart) { _waveformChart.resize(); }
      if (_timeOfDayChart) { _timeOfDayChart.resize(); }
      if (_historyChart) { _historyChart.resize(); }
    });
    if (wf) { _resizeObserver.observe(wf); }
    if (td) { _resizeObserver.observe(td); }
    if (hs) { _resizeObserver.observe(hs); }

    window.addEventListener('resize', function () {
      if (_waveformChart) { _waveformChart.resize(); }
      if (_timeOfDayChart) { _timeOfDayChart.resize(); }
      if (_historyChart) { _historyChart.resize(); }
    });
  }

  // ============ timeline filtering ============

  function filterTimeline(timeline) {
    if (!timeline || !timeline.length) { return []; }
    var now = Date.now();
    var cutoffs = {
      day: now - 86400000,
      week: now - 604800000,
      month: now - 2592000000
    };
    var cutoff = cutoffs[_filterRange] || cutoffs.week;
    return timeline.filter(function (item) {
      return new Date(item.timestamp).getTime() > cutoff;
    });
  }

  // ============ chart rendering ============

  function renderWaveformChart(timeline) {
    if (!_waveformChart) return;

    if (!timeline || !timeline.length) {
      _waveformChart.setOption({
        graphic: [{
          type: 'text', left: 'center', top: 'center',
          style: { text: '暂无数据', fill: tok('muted'), fontSize: 13 }
        }]
      }, true);
      return;
    }

    // Show newest first, but x-axis left→right = earliest→latest
    var sorted = timeline.slice().reverse();
    var scores = sorted.map(function (t) { return Math.round(t.score); });
    var times = sorted.map(function (t) { return timeLabel(t.timestamp); });
    var types = sorted.map(function (t) { return t.type; });

    var succColor = tok('success');
    var warnColor = tok('warning');
    var dangColor = tok('danger');

    var option = {
      grid: { top: 10, right: 20, bottom: 28, left: 44 },
      xAxis: {
        type: 'category',
        data: times,
        axisLine: { lineStyle: { color: tok('border') } },
        axisLabel: { color: tok('muted'), fontSize: 10, interval: 'auto' },
        axisTick: { show: false }
      },
      yAxis: {
        type: 'value', min: 0, max: 100,
        splitLine: { lineStyle: { color: tok('border') } },
        axisLabel: { color: tok('muted'), fontSize: 10 },
        axisLine: { show: false }
      },
      tooltip: {
        trigger: 'axis',
        backgroundColor: 'rgba(15,23,42,0.94)',
        borderColor: tok('border'),
        textStyle: { color: tok('text'), fontSize: 12 },
        formatter: function (params) {
          var p = params[0];
          var idx = p.dataIndex;
          var typeLabel = { deep: '深度专注', shallow: '轻度专注', warning: '走神' };
          return p.axisValue + '<br/>分数: <b>' + p.value + '</b><br/>状态: ' + (typeLabel[types[idx]] || '—');
        }
      },
      series: [{
        data: scores.map(function (v, i) {
          return {
            value: v,
            itemStyle: {
              color: types[i] === 'deep' ? succColor :
                     types[i] === 'warning' ? dangColor : warnColor
            }
          };
        }),
        type: 'line',
        smooth: true,
        symbol: 'circle',
        symbolSize: 4,
        lineStyle: { color: succColor, width: 2 },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: succColor + '30' },
            { offset: 1, color: succColor + '05' }
          ])
        },
        markLine: {
          silent: true, symbol: 'none',
          lineStyle: { color: tok('border'), type: 'dashed' },
          data: [{ yAxis: 70, label: { formatter: '深度线', fontSize: 10, color: tok('muted') } }]
        }
      }]
    };

    _waveformChart.setOption(option, true);
  }

  function renderTimeOfDayChart(tod) {
    if (!_timeOfDayChart || !tod) { return; }

    var periods = ['morning', 'afternoon', 'evening', 'night'];
    var labels = ['上午(6-12)', '下午(12-17)', '傍晚(17-20)', '夜间(20-6)'];
    var colors = [tok('warning'), tok('warning'), tok('brand'), tok('info')];
    var scores = periods.map(function (p) {
      return (tod[p] && tod[p].sessions > 0) ? Math.round(tod[p].score) : 0;
    });
    var sessions = periods.map(function (p) {
      return (tod[p] && tod[p].sessions) || 0;
    });

    var option = {
      grid: { top: 10, right: 20, bottom: 28, left: 44 },
      xAxis: {
        type: 'category',
        data: labels,
        axisLine: { lineStyle: { color: tok('border') } },
        axisLabel: { color: tok('muted'), fontSize: 10 },
        axisTick: { show: false }
      },
      yAxis: {
        type: 'value', min: 0, max: 100,
        splitLine: { lineStyle: { color: tok('border') } },
        axisLabel: { color: tok('muted'), fontSize: 10 },
        axisLine: { show: false }
      },
      tooltip: {
        trigger: 'axis',
        backgroundColor: 'rgba(15,23,42,0.94)',
        borderColor: tok('border'),
        textStyle: { color: tok('text'), fontSize: 12 },
        formatter: function (params) {
          var p = params[0];
          return p.name + '<br/>专注分: <b>' + p.value + '</b><br/>会话数: ' + sessions[p.dataIndex];
        }
      },
      series: [{
        type: 'bar',
        data: scores.map(function (v, i) {
          return {
            value: v,
            itemStyle: {
              color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                { offset: 0, color: colors[i] },
                { offset: 1, color: colors[i] + '44' }
              ]),
              borderRadius: [6, 6, 0, 0]
            }
          };
        }),
        barWidth: '40%',
        label: {
          show: true, position: 'top',
          color: tok('muted'), fontSize: 10,
          formatter: function (p) { return p.value > 0 ? p.value : ''; }
        }
      }]
    };

    _timeOfDayChart.setOption(option, true);
  }

  // ============ history chart (ECharts, replaces old div bars) ============

  function renderHistoryChart(filtered) {
    if (!_historyChart) return;

    if (!filtered || !filtered.length) {
      _historyChart.setOption({
        graphic: [{
          type: 'text', left: 'center', top: 'center',
          style: { text: '暂无数据', fill: tok('muted'), fontSize: 13 }
        }]
      }, true);
      return;
    }

    // Group by hour
    var groups = [];
    var cur = null;
    for (var i = 0; i < filtered.length; i++) {
      var item = filtered[i];
      var d = new Date(item.timestamp);
      var key = (d.getMonth() + 1) + '/' + d.getDate() + ' ' +
        String(d.getHours()).padStart(2, '0') + ':00';
      if (!cur || cur.key !== key) {
        if (cur) groups.push(cur);
        cur = { key: key, items: [], deepCount: 0, totalScore: 0 };
      }
      cur.items.push(item);
      cur.totalScore += item.score;
      if (item.type === 'deep') cur.deepCount++;
    }
    if (cur) groups.push(cur);

    if (groups.length > 20) groups = groups.slice(-20);

    var labels = groups.map(function (g) { return g.key; });
    var avgScores = groups.map(function (g) {
      return Math.round(g.totalScore / g.items.length);
    });
    var deepRatios = groups.map(function (g) {
      return Math.round((g.deepCount / g.items.length) * 100);
    });

    var succColor = tok('success');
    var brandColor = tok('brand');

    var option = {
      grid: { top: 10, right: 52, bottom: 28, left: 44 },
      xAxis: {
        type: 'category',
        data: labels,
        axisLine: { lineStyle: { color: tok('border') } },
        axisLabel: { color: tok('muted'), fontSize: 10, interval: 'auto' },
        axisTick: { show: false }
      },
      yAxis: [
        {
          type: 'value', min: 0, max: 100,
          splitLine: { lineStyle: { color: tok('border') } },
          axisLabel: { color: tok('muted'), fontSize: 10 },
          axisLine: { show: false }
        },
        {
          type: 'value', min: 0, max: 100,
          axisLabel: { show: false },
          splitLine: { show: false },
          axisLine: { show: false }
        }
      ],
      tooltip: {
        trigger: 'axis',
        backgroundColor: 'rgba(15,23,42,0.94)',
        borderColor: tok('border'),
        textStyle: { color: tok('text'), fontSize: 12 },
        formatter: function (params) {
          return params[0].name +
            '<br/>平均分: <b>' + params[0].value + '</b>' +
            '<br/>深度占比: <b>' + params[1].value + '%</b>';
        }
      },
      series: [
        {
          name: '平均分',
          type: 'bar',
          data: avgScores.map(function (v) {
            return {
              value: v,
              itemStyle: {
                color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                  { offset: 0, color: succColor + 'B3' },
                  { offset: 1, color: succColor + '20' }
                ]),
                borderRadius: [4, 4, 0, 0]
              }
            };
          }),
          barWidth: '50%'
        },
        {
          name: '深度占比',
          type: 'line',
          yAxisIndex: 1,
          data: deepRatios,
          smooth: true,
          symbol: 'circle',
          symbolSize: 5,
          lineStyle: { color: brandColor, width: 2 },
          itemStyle: { color: brandColor }
        }
      ]
    };

    _historyChart.setOption(option, true);
  }

  // ============ panel updates ============

  function updateStatsPanel(data) {
    var ratio = Math.round(data.deepRatio || 0);
    var el = document.getElementById('deep-value');
    if (el) { el.textContent = ratio; }

    var ring = document.getElementById('deep-ring');
    if (ring) {
      var circumference = 2 * Math.PI * 40;
      var offset = circumference - (ratio / 100) * circumference;
      ring.style.strokeDasharray = circumference;
      ring.style.strokeDashoffset = offset;
      ring.style.stroke = tok('success');
    }

    var focusMin = (data.today && data.today.focusMinutes) || 0;
    var ft = document.getElementById('focus-time');
    if (ft) { ft.textContent = formatMinutes(focusMin); }

    var sc = document.getElementById('switch-count');
    if (sc) { sc.textContent = (data.today && data.today.pageSwitches) || 0; }

    var fs = document.getElementById('flow-score');
    if (fs) { fs.textContent = Math.round(data.score || 0); }

    // Trend indicator
    var trend = document.getElementById('flow-trend');
    if (trend && data.trend) {
      if (data.trend.direction === 'up') {
        trend.textContent = '↗ +' + data.trend.change;
        trend.style.color = tok('success');
      } else if (data.trend.direction === 'down') {
        trend.textContent = '↘ ' + data.trend.change;
        trend.style.color = tok('danger');
      } else {
        trend.textContent = '—';
        trend.style.color = '';
      }
    }
  }

  function updateSessionPanel(data) {
    if (!data.today) { return; }
    var today = data.today;

    if (today.firstSessionTime) {
      var d = new Date(today.firstSessionTime);
      var ss = document.getElementById('session-start');
      if (ss) {
        ss.textContent = d.toLocaleTimeString('zh-CN', {
          hour: '2-digit', minute: '2-digit', second: '2-digit'
        });
      }
    }

    var focusRatio = Math.round(today.focusRatio || 0);
    var sp = document.getElementById('session-progress');
    if (sp) { sp.style.width = focusRatio + '%'; }
    var pt = document.getElementById('progress-label');
    if (pt) { pt.textContent = focusRatio + '% 完成'; }

    var remainingMin = Math.max(0, (today.studyMinutes || 60) - (today.focusMinutes || 0));
    var rt = document.getElementById('remaining-time');
    if (rt) { rt.textContent = formatMinutes(remainingMin); }
  }

  function updateStateIndicator(rt) {
    if (!rt) { return; }

    var stateText = document.getElementById('state-text');
    var stateDesc = document.getElementById('state-desc');
    var orbInner = document.querySelector('.hero-orb-inner');
    var stateFill = document.getElementById('state-fill');

    var label, desc, color, percent;

    switch (rt.state) {
      case 'focused':
        label = '深度专注中';
        desc = '继续保持，学习效率很高';
        color = tok('success');
        percent = 85 + Math.round(rt.confidence * 15);
        break;
      case 'lightly':
        label = '轻度专注';
        desc = '注意力有所分散，建议集中精神';
        color = tok('warning');
        percent = 40 + Math.round(rt.confidence * 30);
        break;
      case 'distracted':
        label = '注意力分散';
        desc = '建议休息片刻，恢复精力';
        color = tok('danger');
        percent = 10 + Math.round(rt.confidence * 30);
        break;
      default:
        label = '监测中';
        desc = '正在分析学习状态';
        color = tok('muted');
        percent = 50;
    }

    if (stateText) {
      stateText.textContent = label;
      stateText.style.color = color;
    }
    if (stateDesc) { stateDesc.textContent = desc; }
    if (orbInner) {
      orbInner.classList.remove('warn', 'light');
      if (rt.state === 'distracted') orbInner.classList.add('warn');
      else if (rt.state === 'lightly') orbInner.classList.add('light');
    }
    if (stateFill) { stateFill.style.width = percent + '%'; }
  }

  function updateTips(tips) {
    if (!tips || !tips.length) { return; }
    var container = document.querySelector('.tips-list');
    if (!container) { return; }

    var iconMap = { good: '✓', info: '◐', warn: '!' };
    container.innerHTML = tips.map(function (tip) {
      return '<div class="tip-item">' +
        '<span class="tip-icon ' + (tip.type || 'info') + '">' +
        (iconMap[tip.type] || '◐') + '</span>' +
        '<span class="tip-text">' + escapeHtml(tip.text) + '</span>' +
        '</div>';
    }).join('');
  }

  // ============ chart refresh ============

  function updateCharts() {
    var analysis = window.FocusAnalysis.getAnalysis();
    if (!analysis) { return; }

    var filtered = filterTimeline(analysis.timeline);
    renderWaveformChart(filtered);
    renderTimeOfDayChart(analysis.timeOfDay);
    renderHistoryChart(filtered);
  }

  function updateAllCards(data) {
    if (!data) { return; }
    updateStatsPanel(data);
    updateSessionPanel(data);
    updateStateIndicator(window.FocusAnalysis.getRealtimeState());
    updateCharts();
    updateTips(data.tips);
  }

  // ============ event listeners ============

  function initFilterButtons() {
    var btns = document.querySelectorAll('.filter-btn');
    for (var i = 0; i < btns.length; i++) {
      btns[i].addEventListener('click', function () {
        for (var j = 0; j < btns.length; j++) {
          btns[j].classList.remove('active');
        }
        this.classList.add('active');
        _filterRange = this.dataset.range;
        updateCharts();
      });
    }
  }

  // ============ init ============

  function init() {
    if (!window.FocusAnalysis) {
      console.warn('[FlowMeter] FocusAnalysis module not loaded');
      return;
    }

    initCharts();
    initFilterButtons();

    window.FocusAnalysis.on('analysis-updated', function (data) {
      updateAllCards(data);
    });

    window.FocusAnalysis.on('realtime-changed', function (state) {
      updateStateIndicator(state);
    });

    window.FocusAnalysis.startPolling(3000);

    window.FocusAnalysis.fetchAnalysis().then(function (data) {
      if (data) { updateAllCards(data); }
    });

    // 主题切换时重读 tokens 并刷新所有图表
    var themeObserver = new MutationObserver(function () {
      refreshTokens();
      var analysis = window.FocusAnalysis.getAnalysis();
      if (analysis) {
        var filtered = filterTimeline(analysis.timeline);
        renderWaveformChart(filtered);
        renderTimeOfDayChart(analysis.timeOfDay);
        renderHistoryChart(filtered);
      }
      updateStateIndicator(window.FocusAnalysis.getRealtimeState());
    });
    themeObserver.observe(document.documentElement, {
      attributes: true, attributeFilter: ['data-theme']
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
