/**
 * FlowMeter — 心流共振仪
 * 使用 FocusAnalysis 共享模块 + ECharts 驱动所有面板数据
 */
(function () {
  'use strict';

  var _waveformChart = null;
  var _timeOfDayChart = null;
  var _filterRange = 'week';
  var _resizeObserver = null;

  // ============ helpers ============

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

  // ============ chart init ============

  function initCharts() {
    var wf = document.getElementById('waveform-chart');
    var td = document.getElementById('timeofday-chart');
    if (wf) { _waveformChart = echarts.init(wf); }
    if (td) { _timeOfDayChart = echarts.init(td); }

    // ResizeObserver for responsive charts
    if (_resizeObserver) { _resizeObserver.disconnect(); }
    _resizeObserver = new ResizeObserver(function () {
      if (_waveformChart) { _waveformChart.resize(); }
      if (_timeOfDayChart) { _timeOfDayChart.resize(); }
    });
    if (wf) { _resizeObserver.observe(wf); }
    if (td) { _resizeObserver.observe(td); }

    window.addEventListener('resize', function () {
      if (_waveformChart) { _waveformChart.resize(); }
      if (_timeOfDayChart) { _timeOfDayChart.resize(); }
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
    if (!_waveformChart || !timeline || !timeline.length) {
      if (_waveformChart) {
        _waveformChart.setOption({
          graphic: [{
            type: 'text',
            left: 'center',
            top: 'center',
            style: { text: '暂无数据', fill: 'rgba(255,255,255,0.3)', fontSize: 14 }
          }]
        }, true);
      }
      return;
    }

    var scores = timeline.map(function (t) { return Math.round(t.score); });
    var times = timeline.map(function (t) {
      var d = new Date(t.timestamp);
      return d.getHours().toString().padStart(2, '0') + ':' +
        d.getMinutes().toString().padStart(2, '0');
    });
    var types = timeline.map(function (t) { return t.type; });

    var option = {
      grid: { top: 10, right: 12, bottom: 24, left: 40 },
      xAxis: {
        type: 'category',
        data: times,
        axisLine: { lineStyle: { color: 'rgba(255,255,255,0.12)' } },
        axisLabel: { color: 'rgba(255,255,255,0.45)', fontSize: 10, interval: 'auto' },
        axisTick: { show: false }
      },
      yAxis: {
        type: 'value',
        min: 0,
        max: 100,
        splitLine: { lineStyle: { color: 'rgba(255,255,255,0.06)' } },
        axisLabel: { color: 'rgba(255,255,255,0.35)', fontSize: 10 },
        axisLine: { show: false }
      },
      tooltip: {
        trigger: 'axis',
        backgroundColor: 'rgba(18,18,24,0.92)',
        borderColor: 'rgba(255,255,255,0.12)',
        textStyle: { color: '#fff', fontSize: 12 },
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
              color: types[i] === 'deep' ? '#00C853' :
                     types[i] === 'warning' ? '#F44336' : '#FF9800'
            }
          };
        }),
        type: 'line',
        smooth: true,
        symbol: 'circle',
        symbolSize: 4,
        lineStyle: { color: '#00C853', width: 2 },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(0, 200, 83, 0.2)' },
            { offset: 1, color: 'rgba(0, 200, 83, 0.02)' }
          ])
        },
        markLine: {
          silent: true,
          symbol: 'none',
          lineStyle: { color: 'rgba(255,255,255,0.1)', type: 'dashed' },
          data: [{ yAxis: 70, label: { formatter: '深度线', fontSize: 10, color: 'rgba(255,255,255,0.35)' } }]
        }
      }]
    };

    _waveformChart.setOption(option, true);
  }

  function renderTimeOfDayChart(tod) {
    if (!_timeOfDayChart || !tod) { return; }

    var periods = ['morning', 'afternoon', 'evening', 'night'];
    var labels = ['上午(6-12)', '下午(12-17)', '傍晚(17-20)', '夜间(20-6)'];
    var colors = ['#FFB300', '#FF9800', '#7C4DFF', '#3F51B5'];
    var scores = periods.map(function (p) {
      return (tod[p] && tod[p].sessions > 0) ? Math.round(tod[p].score) : 0;
    });
    var sessions = periods.map(function (p) {
      return (tod[p] && tod[p].sessions) || 0;
    });

    var option = {
      grid: { top: 10, right: 12, bottom: 24, left: 40 },
      xAxis: {
        type: 'category',
        data: labels,
        axisLine: { lineStyle: { color: 'rgba(255,255,255,0.12)' } },
        axisLabel: { color: 'rgba(255,255,255,0.45)', fontSize: 10 },
        axisTick: { show: false }
      },
      yAxis: {
        type: 'value',
        min: 0,
        max: 100,
        splitLine: { lineStyle: { color: 'rgba(255,255,255,0.06)' } },
        axisLabel: { color: 'rgba(255,255,255,0.35)', fontSize: 10 },
        axisLine: { show: false }
      },
      tooltip: {
        trigger: 'axis',
        backgroundColor: 'rgba(18,18,24,0.92)',
        borderColor: 'rgba(255,255,255,0.12)',
        textStyle: { color: '#fff', fontSize: 12 },
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
            itemStyle: { color: colors[i], borderRadius: [4, 4, 0, 0] }
          };
        }),
        barWidth: '45%',
        label: {
          show: true,
          position: 'top',
          color: 'rgba(255,255,255,0.5)',
          fontSize: 10,
          formatter: function (p) { return p.value > 0 ? p.value : ''; }
        }
      }]
    };

    _timeOfDayChart.setOption(option, true);
  }

  // ============ history bars ============

  function renderHistoryBars(filtered) {
    var container = document.querySelector('.history-waves');
    if (!container) { return; }

    if (!filtered || !filtered.length) {
      container.innerHTML =
        '<div class="history-item"><div class="history-time" style="color:rgba(255,255,255,0.3);padding:20px;text-align:center;">暂无数据</div></div>';
      return;
    }

    // Group by hour blocks
    var groups = [];
    var currentGroup = null;
    for (var i = 0; i < filtered.length; i++) {
      var item = filtered[i];
      var d = new Date(item.timestamp);
      var hour = d.getHours();
      var key = (d.getMonth() + 1) + '/' + d.getDate() + ' ' +
        String(hour).padStart(2, '0') + ':00';
      if (!currentGroup || currentGroup.key !== key) {
        if (currentGroup) { groups.push(currentGroup); }
        currentGroup = { key: key, bars: [], totalScore: 0 };
      }
      var h = Math.max(15, Math.min(95, item.score));
      currentGroup.bars.push({ height: h, type: item.type });
      currentGroup.totalScore += item.score;
    }
    if (currentGroup) { groups.push(currentGroup); }

    var recent = groups.slice(-3);
    container.innerHTML = recent.map(function (g) {
      var barsHtml = g.bars.map(function (b) {
        var cls = b.type === 'deep' ? 'deep' :
                   b.type === 'shallow' ? 'shallow' : 'distracted';
        return '<div class="history-bar ' + cls + '" style="height:' + b.height + '%;"></div>';
      }).join('');
      var avg = Math.round(g.totalScore / g.bars.length);
      return '<div class="history-item">' +
        '<div class="history-time">' + g.key + '</div>' +
        barsHtml +
        '<div class="history-score">' + avg + '分</div>' +
        '</div>';
    }).join('');
  }

  // ============ panel updates ============

  function updateStatsPanel(data) {
    var ratio = Math.round(data.deepRatio || 0);
    var el = document.getElementById('deep-value');
    if (el) { el.textContent = ratio; }

    var ring = document.getElementById('deep-ring');
    if (ring) {
      var circumference = 2 * Math.PI * 42;
      var offset = circumference - (ratio / 100) * circumference;
      ring.style.strokeDasharray = circumference;
      ring.style.strokeDashoffset = offset;
    }

    var focusMin = (data.today && data.today.focusMinutes) || 0;
    var ft = document.getElementById('focus-time');
    if (ft) { ft.textContent = formatMinutes(focusMin); }

    var sc = document.getElementById('switch-count');
    if (sc) { sc.textContent = (data.today && data.today.pageSwitches) || 0; }

    var fs = document.getElementById('flow-score');
    if (fs) { fs.textContent = Math.round(data.score || 0); }
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
    var pt = document.querySelector('.progress-text');
    if (pt) { pt.textContent = focusRatio + '% 完成'; }

    var remainingMin = Math.max(0, (today.studyMinutes || 60) - (today.focusMinutes || 0));
    var rt = document.getElementById('remaining-time');
    if (rt) { rt.textContent = formatMinutes(remainingMin); }
  }

  function updateStateIndicator(rt) {
    if (!rt) { return; }

    var stateText = document.getElementById('state-text');
    var stateDesc = document.getElementById('state-desc');
    var stateOrb = document.querySelector('.orb-inner');
    var stateFill = document.getElementById('state-fill');

    var label, desc, color, rgb, percent;

    switch (rt.state) {
      case 'focused':
        label = '深度专注中';
        desc = '继续保持，学习效率很高';
        color = '#00C853';
        rgb = '0, 200, 83';
        percent = 85 + Math.round(rt.confidence * 15);
        break;
      case 'lightly':
        label = '轻度专注';
        desc = '注意力有所分散，建议集中精神';
        color = '#FF9800';
        rgb = '255, 152, 0';
        percent = 40 + Math.round(rt.confidence * 30);
        break;
      case 'distracted':
        label = '注意力分散';
        desc = '建议休息片刻，恢复精力';
        color = '#F44336';
        rgb = '244, 67, 54';
        percent = 10 + Math.round(rt.confidence * 30);
        break;
      default:
        label = '监测中';
        desc = '正在分析学习状态';
        color = '#9E9E9E';
        rgb = '158, 158, 158';
        percent = 50;
    }

    if (stateText) {
      stateText.textContent = label;
      stateText.style.color = color;
    }
    if (stateDesc) { stateDesc.textContent = desc; }
    if (stateOrb) {
      stateOrb.style.background =
        'radial-gradient(circle, ' + color + ' 0%, rgba(' + rgb + ', 0.6) 100%)';
      stateOrb.style.boxShadow = '0 0 30px rgba(' + rgb + ', 0.6)';
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
    renderHistoryBars(filtered);
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

    // Poll more frequently on this dedicated page
    window.FocusAnalysis.startPolling(3000);

    // Fetch immediately, show cached data first, then live
    window.FocusAnalysis.fetchAnalysis().then(function (data) {
      if (data) { updateAllCards(data); }
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
