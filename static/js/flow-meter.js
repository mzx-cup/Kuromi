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

  // 将任意 CSS 颜色转换为 RGB 字符串（ECharts addColorStop 不支持 oklch/lab 等格式）
  function toRgb(color) {
    if (!color || color === 'transparent' || color === 'none') return 'rgb(128,128,128)';
    var canvas = document.createElement('canvas');
    canvas.width = canvas.height = 1;
    var ctx = canvas.getContext('2d');
    ctx.fillStyle = color;
    ctx.fillRect(0, 0, 1, 1);
    var d = ctx.getImageData(0, 0, 1, 1).data;
    return 'rgb(' + d[0] + ',' + d[1] + ',' + d[2] + ')';
  }

  // 从 CSS 自定义属性读取颜色，与 tokens.css 主题保持一致
  var _tokenColors = null;
  function tok(name) {
    if (!_tokenColors) {
      var s = getComputedStyle(document.documentElement);
      _tokenColors = {
        success: toRgb(s.getPropertyValue('--success').trim() || '#10b981'),
        warning: toRgb(s.getPropertyValue('--warning').trim() || '#f59e0b'),
        danger:  toRgb(s.getPropertyValue('--danger').trim()  || '#ef4444'),
        info:    toRgb(s.getPropertyValue('--info').trim()    || '#06b6d4'),
        brand:   toRgb(s.getPropertyValue('--brand-500').trim() || '#6366f1'),
        text:    toRgb(s.getPropertyValue('--text-heading').trim() || '#fff'),
        muted:   toRgb(s.getPropertyValue('--text-muted').trim() || 'rgba(255,255,255,0.4)'),
        border:  toRgb(s.getPropertyValue('--border-glass').trim() || 'rgba(255,255,255,0.06)')
      };
    }
    return _tokenColors[name];
  }

  // 主题切换时需要重新读取
  function refreshTokens() { _tokenColors = null; }

  // 拿 RGB 三元组（用于构造 rgba / 多停色渐变）
  function tokRGB(name) {
    var v = tok(name);
    var m = v.match(/\d+/g);
    return m ? [parseInt(m[0], 10), parseInt(m[1], 10), parseInt(m[2], 10)] : [128, 128, 128];
  }
  function tokRgba(name, a) {
    var c = tokRGB(name);
    return 'rgba(' + c[0] + ',' + c[1] + ',' + c[2] + ',' + a + ')';
  }

  // 多停色渐变构造器 — 给定 token 名 + 透明度序列
  function gradStops(name, stops) {
    var c = tokRGB(name);
    return stops.map(function (s) {
      return { offset: s.offset, color: 'rgba(' + c[0] + ',' + c[1] + ',' + c[2] + ',' + s.a + ')' };
    });
  }

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

  // ============ empty state for charts ============
  function showEmpty(chartId, icon, title, desc) {
    var dom = document.getElementById(chartId);
    if (!dom) return;
    clearEmpty(chartId);
    var el = document.createElement('div');
    el.className = 'fm-empty';
    el.setAttribute('data-empty-for', chartId);
    el.innerHTML =
      '<div class="fm-empty-orb"><i data-lucide="' + icon + '"></i></div>' +
      '<div class="fm-empty-title">' + escapeHtml(title) + '</div>' +
      '<div class="fm-empty-desc">' + escapeHtml(desc) + '</div>';
    // 让 empty 覆盖 chart 区域
    dom.style.position = dom.style.position || 'relative';
    dom.appendChild(el);
    if (window.lucide && lucide.createIcons) lucide.createIcons();
  }
  function clearEmpty(chartId) {
    var dom = document.getElementById(chartId);
    if (!dom) return;
    var exist = dom.querySelector('[data-empty-for="' + chartId + '"]');
    if (exist) exist.remove();
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
      _waveformChart.clear();
      showEmpty('waveform-chart', 'activity', '暂无波形数据', '开始一次专注会话后，这里会显示实时心流曲线');
      return;
    }
    clearEmpty('waveform-chart');

    // Show newest first, but x-axis left→right = earliest→latest
    var sorted = timeline.slice().reverse();
    var scores = sorted.map(function (t) { return Math.round(t.score); });
    var times = sorted.map(function (t) { return timeLabel(t.timestamp); });
    var types = sorted.map(function (t) { return t.type; });

    var succColor = tok('success');
    var warnColor = tok('warning');
    var dangColor = tok('danger');

    var option = {
      animation: true,
      animationDuration: 1200,
      animationEasing: 'cubicOut',
      animationDelay: function (idx) { return idx * 28; },
      animationDurationUpdate: 700,
      animationEasingUpdate: 'cubicInOut',
      grid: { top: 18, right: 22, bottom: 26, left: 42, containLabel: false },
      xAxis: {
        type: 'category',
        data: times,
        boundaryGap: false,
        axisLine: { lineStyle: { color: tok('border') } },
        axisLabel: {
          color: tok('muted'), fontSize: 10, interval: 'auto',
          margin: 10, hideOverlap: true
        },
        axisTick: { show: false }
      },
      yAxis: {
        type: 'value', min: 0, max: 100,
        splitNumber: 4,
        splitLine: {
          lineStyle: {
            color: tok('border'),
            type: [3, 4],
            opacity: 0.55
          }
        },
        axisLabel: { color: tok('muted'), fontSize: 10, margin: 10 },
        axisLine: { show: false }
      },
      tooltip: {
        trigger: 'axis',
        backgroundColor: tokRgba('text', 0.04),
        borderWidth: 0,
        padding: 0,
        extraCssText: 'box-shadow: var(--shadow-md); backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px); border-radius: 12px;',
        axisPointer: {
          type: 'line',
          lineStyle: {
            color: tokRgba('success', 0.55),
            width: 1,
            type: 'solid'
          }
        },
        formatter: function (params) {
          if (!params || !params.length) return '';
          var p = params[0];
          var idx = p.dataIndex;
          var typeLabel = { deep: '深度专注', shallow: '轻度专注', warning: '走神' };
          var typeColor = types[idx] === 'deep' ? succColor
                        : types[idx] === 'warning' ? dangColor : warnColor;
          return '<div style="padding:10px 14px;min-width:160px;">'
            + '<div style="font-size:11px;color:var(--text-muted);margin-bottom:6px;letter-spacing:0.04em">'
            + p.axisValue + '</div>'
            + '<div style="display:flex;align-items:center;gap:8px">'
            + '<span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:' + typeColor + ';box-shadow:0 0 8px ' + typeColor + '"></span>'
            + '<span style="font-size:11px;color:var(--text-body)">' + (typeLabel[types[idx]] || '—') + '</span>'
            + '<span style="margin-left:auto;font-size:14px;font-weight:700;color:var(--text-heading);font-variant-numeric:tabular-nums">' + p.value + '</span>'
            + '</div></div>';
        }
      },
      series: [{
        data: scores.map(function (v, i) {
          var c = types[i] === 'deep' ? succColor
                : types[i] === 'warning' ? dangColor : warnColor;
          return {
            value: v,
            itemStyle: {
              color: c,
              borderColor: c,
              borderWidth: 0,
              shadowBlur: 12,
              shadowColor: c
            }
          };
        }),
        type: 'line',
        smooth: 0.4,
        symbol: 'circle',
        symbolSize: 6,
        showSymbol: true,
        cursor: 'pointer',
        lineStyle: {
          color: succColor,
          width: 2.5,
          shadowBlur: 8,
          shadowColor: tokRgba('success', 0.45)
        },
        areaStyle: {
          opacity: 0.85,
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: tokRgba('success', 0.32) },
            { offset: 0.55, color: tokRgba('success', 0.10) },
            { offset: 1, color: tokRgba('success', 0) }
          ])
        },
        emphasis: {
          focus: 'series',
          lineStyle: { width: 3 },
          itemStyle: { borderColor: '#fff', borderWidth: 2, shadowBlur: 16 }
        },
        markLine: {
          silent: true,
          symbol: 'none',
          lineStyle: {
            color: tokRgba('muted', 0.55),
            type: 'dashed',
            width: 1
          },
          data: [{
            yAxis: 70,
            label: {
              formatter: '深度线',
              fontSize: 10,
              color: tok('muted'),
              position: 'insideEndTop',
              distance: 6
            }
          }]
        }
      }]
    };

    _waveformChart.setOption(option, true);
  }

  function renderTimeOfDayChart(tod) {
    if (!_timeOfDayChart || !tod) { return; }

    var periods = ['morning', 'afternoon', 'evening', 'night'];
    var labels = ['上午', '下午', '傍晚', '夜间'];
    var ranges  = ['6 - 12', '12 - 17', '17 - 20', '20 - 6'];
    var colorTokens = ['warning', 'brand', 'success', 'info'];
    var solidColors = colorTokens.map(function (t) { return tok(t); });
    var scores = periods.map(function (p) {
      return (tod[p] && tod[p].sessions > 0) ? Math.round(tod[p].score) : 0;
    });
    var sessions = periods.map(function (p) {
      return (tod[p] && tod[p].sessions) || 0;
    });
    var maxScore = Math.max.apply(null, scores.concat([1]));

    var option = {
      animation: true,
      animationDuration: 1100,
      animationEasing: 'elasticOut',
      animationDelay: function (idx) { return idx * 110; },
      animationDurationUpdate: 600,
      animationEasingUpdate: 'cubicOut',
      grid: { top: 30, right: 16, bottom: 30, left: 38 },
      xAxis: {
        type: 'category',
        data: labels,
        axisLine: { show: false },
        axisLabel: {
          color: tok('muted'), fontSize: 11, fontWeight: 500, margin: 12,
          formatter: function (val, idx) {
            return val + '\n{sub|' + ranges[idx] + '}';
          },
          rich: {
            sub: {
              color: tokRgba('muted', 0.6),
              fontSize: 9,
              padding: [3, 0, 0, 0]
            }
          }
        },
        axisTick: { show: false }
      },
      yAxis: {
        type: 'value', min: 0, max: 100,
        splitNumber: 4,
        splitLine: {
          lineStyle: {
            color: tok('border'),
            type: [3, 4],
            opacity: 0.55
          }
        },
        axisLabel: { color: tok('muted'), fontSize: 10, margin: 10 },
        axisLine: { show: false }
      },
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'shadow', shadowStyle: { color: tokRgba('brand', 0.06) } },
        backgroundColor: 'transparent',
        borderWidth: 0,
        padding: 0,
        extraCssText: 'box-shadow: var(--shadow-md); backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px); border-radius: 12px;',
        formatter: function (params) {
          if (!params || !params.length) return '';
          var p = params[0];
          var idx = p.dataIndex;
          var c = solidColors[idx];
          return '<div style="padding:10px 14px;min-width:170px;">'
            + '<div style="display:flex;align-items:center;gap:8px;margin-bottom:8px">'
            + '<span style="display:inline-block;width:10px;height:10px;border-radius:3px;background:' + c + ';box-shadow:0 0 10px ' + c + '"></span>'
            + '<span style="font-size:12px;font-weight:600;color:var(--text-heading)">' + labels[idx] + '</span>'
            + '<span style="font-size:10px;color:var(--text-muted);margin-left:auto">' + ranges[idx] + '</span>'
            + '</div>'
            + '<div style="display:flex;justify-content:space-between;gap:18px;padding:2px 0">'
            + '<span style="font-size:11px;color:var(--text-body)">专注分</span>'
            + '<span style="font-size:12px;font-weight:700;color:var(--text-heading);font-variant-numeric:tabular-nums">' + p.value + '</span>'
            + '</div>'
            + '<div style="display:flex;justify-content:space-between;gap:18px;padding:2px 0">'
            + '<span style="font-size:11px;color:var(--text-body)">会话数</span>'
            + '<span style="font-size:12px;font-weight:600;color:var(--text-body);font-variant-numeric:tabular-nums">' + sessions[idx] + '</span>'
            + '</div>'
            + '</div>';
        }
      },
      series: [
        // 顶部发光层（增强视觉高点感）
        {
          type: 'pictorialBar',
          symbol: 'roundRect',
          symbolSize: [4, 4],
          symbolOffset: [0, -2],
          symbolPosition: 'end',
          z: 12,
          data: scores.map(function (v, i) {
            return {
              value: v,
              itemStyle: {
                color: solidColors[i],
                shadowBlur: 12,
                shadowColor: solidColors[i]
              }
            };
          })
        },
        // 主柱形
        {
          type: 'bar',
          data: scores.map(function (v, i) {
            return {
              value: v,
              itemStyle: {
                color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                  { offset: 0, color: tokRgba(colorTokens[i], 0.92) },
                  { offset: 0.55, color: tokRgba(colorTokens[i], 0.55) },
                  { offset: 1, color: tokRgba(colorTokens[i], 0.18) }
                ]),
                borderRadius: [8, 8, 4, 4],
                shadowBlur: 18,
                shadowColor: tokRgba(colorTokens[i], 0.22)
              }
            };
          }),
          barWidth: '38%',
          label: {
            show: true, position: 'top',
            color: tok('muted'), fontSize: 11, fontWeight: 600,
            formatter: function (p) { return p.value > 0 ? p.value : ''; }
          },
          emphasis: {
            focus: 'self',
            itemStyle: {
              shadowBlur: 26,
              shadowColor: tokRgba(colorTokens[0], 0.35)
            }
          }
        }
      ]
    };

    _timeOfDayChart.setOption(option, true);
  }

  // ============ history chart (ECharts, replaces old div bars) ============

  function renderHistoryChart(filtered) {
    if (!_historyChart) return;

    if (!filtered || !filtered.length) {
      _historyChart.clear();
      showEmpty('history-chart', 'bar-chart-3', '暂无历史趋势', '完成更多专注会话后，这里会显示趋势曲线');
      return;
    }
    clearEmpty('history-chart');

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
      animation: true,
      animationDuration: 1300,
      animationEasing: 'cubicOut',
      animationDelay: function (idx) { return Math.min(idx * 22, 500); },
      animationDurationUpdate: 800,
      animationEasingUpdate: 'cubicInOut',
      grid: { top: 18, right: 52, bottom: 26, left: 38 },
      legend: {
        show: true,
        top: -2,
        right: 8,
        itemWidth: 10,
        itemHeight: 10,
        itemGap: 14,
        textStyle: { color: tok('muted'), fontSize: 11 }
      },
      xAxis: {
        type: 'category',
        data: labels,
        boundaryGap: true,
        axisLine: { lineStyle: { color: tok('border') } },
        axisLabel: {
          color: tok('muted'), fontSize: 10, interval: 'auto',
          margin: 10, hideOverlap: true
        },
        axisTick: { show: false }
      },
      yAxis: [
        {
          type: 'value', min: 0, max: 100,
          splitNumber: 4,
          name: '平均分',
          nameTextStyle: { color: tokRgba('muted', 0.65), fontSize: 10, padding: [0, 0, 4, 0] },
          splitLine: {
            lineStyle: {
              color: tok('border'),
              type: [3, 4],
              opacity: 0.55
            }
          },
          axisLabel: { color: tok('muted'), fontSize: 10, margin: 10 },
          axisLine: { show: false }
        },
        {
          type: 'value', min: 0, max: 100,
          name: '深度占比',
          nameTextStyle: { color: tokRgba('muted', 0.65), fontSize: 10, padding: [0, 0, 4, 0] },
          axisLabel: { show: false },
          splitLine: { show: false },
          axisLine: { show: false }
        }
      ],
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'line', lineStyle: { color: tokRgba('success', 0.4), width: 1 } },
        backgroundColor: 'transparent',
        borderWidth: 0,
        padding: 0,
        extraCssText: 'box-shadow: var(--shadow-md); backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px); border-radius: 12px;',
        formatter: function (params) {
          if (!params || !params.length) return '';
          var head = params[0].name;
          var rows = params.map(function (p) {
            var dot = '<span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:' + p.color + ';margin-right:6px;vertical-align:middle"></span>';
            var unit = p.seriesName === '深度占比' ? '%' : '';
            return '<div style="display:flex;justify-content:space-between;align-items:center;gap:18px;padding:3px 0">'
              + '<span style="font-size:11px;color:var(--text-body)">' + dot + p.seriesName + '</span>'
              + '<span style="font-size:13px;font-weight:700;color:var(--text-heading);font-variant-numeric:tabular-nums">' + p.value + unit + '</span>'
              + '</div>';
          }).join('');
          return '<div style="padding:10px 14px;min-width:170px;">'
            + '<div style="font-size:11px;color:var(--text-muted);margin-bottom:6px;letter-spacing:0.04em">' + head + '</div>'
            + rows + '</div>';
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
                  { offset: 0, color: tokRgba('success', 0.85) },
                  { offset: 0.6, color: tokRgba('success', 0.42) },
                  { offset: 1, color: tokRgba('success', 0.12) }
                ]),
                borderRadius: [6, 6, 2, 2],
                shadowBlur: 14,
                shadowColor: tokRgba('success', 0.18)
              }
            };
          }),
          barWidth: '46%',
          emphasis: {
            focus: 'self',
            itemStyle: {
              shadowBlur: 24,
              shadowColor: tokRgba('success', 0.45)
            }
          }
        },
        {
          name: '深度占比',
          type: 'line',
          yAxisIndex: 1,
          data: deepRatios,
          smooth: 0.45,
          symbol: 'circle',
          symbolSize: 6,
          showSymbol: true,
          cursor: 'pointer',
          lineStyle: {
            color: brandColor,
            width: 2.5,
            shadowBlur: 8,
            shadowColor: tokRgba('brand', 0.45)
          },
          itemStyle: {
            color: brandColor,
            borderColor: '#fff',
            borderWidth: 0,
            shadowBlur: 10,
            shadowColor: brandColor
          },
          areaStyle: {
            opacity: 0.5,
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: tokRgba('brand', 0.18) },
              { offset: 1, color: tokRgba('brand', 0) }
            ])
          },
          emphasis: {
            focus: 'series',
            lineStyle: { width: 3 },
            itemStyle: { borderColor: '#fff', borderWidth: 2, shadowBlur: 16 }
          }
        }
      ]
    };

    _historyChart.setOption(option, true);
  }

  // ============ panel updates ============

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

    var label, color, percent;

    switch (rt.state) {
      case 'focused':
        label = '深度专注中';
        color = tok('success');
        percent = 85 + Math.round(rt.confidence * 15);
        break;
      case 'lightly':
        label = '轻度专注';
        color = tok('warning');
        percent = 40 + Math.round(rt.confidence * 30);
        break;
      case 'distracted':
        label = '注意力分散';
        color = tok('danger');
        percent = 10 + Math.round(rt.confidence * 30);
        break;
      default:
        label = '实时监测中';
        color = tok('muted');
        percent = 50;
    }

    var text = document.getElementById('fm-status-text');
    if (text) {
      text.textContent = label;
      text.style.color = color;
    }
    var dot = document.getElementById('fm-status-dot');
    if (dot) {
      var stateKey = (label || '').includes('深度') ? 'deep'
        : (label || '').includes('轻度') ? 'shallow'
        : (label || '').includes('分心') ? 'distracted'
        : 'default';
      dot.setAttribute('data-state', stateKey);
    }
  }

  function updateTips(tips) {
    if (!tips || !tips.length) { return; }
    var container = document.querySelector('.tips-list');
    if (!container) { return; }

    var iconLucide = { good: 'check', info: 'info', warn: 'alert-triangle' };
    container.innerHTML = tips.map(function (tip) {
      var t = tip.type || 'info';
      return '<div class="tip-item tip-' + t + '" tabindex="0">' +
        '<span class="tip-icon ' + t + '">' +
          '<i data-lucide="' + (iconLucide[t] || 'info') + '"></i>' +
        '</span>' +
        '<span class="tip-text">' + escapeHtml(tip.text) + '</span>' +
        '</div>';
    }).join('');
    // 重渲染后立即把 lucide 图标替换为 SVG
    if (window.lucide && lucide.createIcons) {
      lucide.createIcons({ attrs: { class: 'tip-icon-svg' } });
    }
  }

  // ============ KPI cards (Row 1) ============

  function fmtStudyHM(mins) {
    var m = Math.max(0, parseInt(mins, 10) || 0);
    var h = Math.floor(m / 60);
    var r = m % 60;
    return h > 0
        ? h + ':' + String(r).padStart(2, '0')
        : String(r).padStart(2, '0') + ':00';
  }

  function trendBadgeText(trend) {
    if (!trend) return '—';
    if (trend.direction === 'up')   return '↑ +' + trend.change;
    if (trend.direction === 'down') return '↓ ' + trend.change;
    return '—';
  }

  function trendBadgeColor(trend) {
    if (!trend) return '';
    if (trend.direction === 'up')   return 'var(--success)';
    if (trend.direction === 'down') return 'var(--danger)';
    return '';
  }

  function weekStartIso() {
    var now = new Date();
    var day = now.getDay() || 7;
    var monday = new Date(now.getFullYear(), now.getMonth(), now.getDate() - (day - 1));
    return monday.toISOString().slice(0, 10);
  }

  function weeklyAvgScore(analysis) {
    if (!analysis || !Array.isArray(analysis.recentHistory)) return null;
    var cutoff = weekStartIso();
    var samples = analysis.recentHistory.filter(function (it) {
      return it && typeof it.timestamp === 'string' && it.timestamp.slice(0, 10) >= cutoff;
    });
    if (!samples.length) return null;
    var sum = 0;
    for (var i = 0; i < samples.length; i++) {
      sum += parseInt(samples[i].score, 10) || 0;
    }
    return Math.round(sum / samples.length);
  }

  function updateKpiCards(data) {
    if (!data) return;
    var today = data.today || {};
    var study = parseInt(today.studyMinutes, 10) || 0;

    var focusVal = document.getElementById('kpi-focus-value');
    if (focusVal) focusVal.textContent = fmtStudyHM(study);
    var focusFill = document.getElementById('kpi-focus-fill');
    if (focusFill) {
      var pct = Math.min(100, Math.round((study / 60) * 100));
      focusFill.style.width = pct + '%';
    }
    var focusHint = document.getElementById('kpi-focus-hint');
    if (focusHint) focusHint.textContent = '目标 60 分钟';

    var scoreVal = document.getElementById('kpi-score-value');
    var score = parseInt(data.score, 10) || 0;
    if (scoreVal) scoreVal.textContent = score;
    var scoreFill = document.getElementById('kpi-score-fill');
    if (scoreFill) {
      scoreFill.style.width = Math.min(100, Math.max(0, score)) + '%';
    }
    var scoreHint = document.getElementById('kpi-score-hint');
    if (scoreHint) {
      var t = data.trend;
      scoreHint.textContent = t
        ? ('近3天均值 ' + (t.previousPeriodScore || 0) + ' / 当前 ' + (t.currentPeriodScore || 0))
        : '—';
    }
    var scoreTrend = document.getElementById('kpi-score-trend');
    if (scoreTrend) {
      scoreTrend.textContent = trendBadgeText(data.trend);
      scoreTrend.style.color = trendBadgeColor(data.trend);
    }

    var deep = parseFloat(data.deepRatio) || 0;
    var deepVal = document.getElementById('kpi-deep-value');
    if (deepVal) deepVal.textContent = Math.round(deep) + '%';
    var deepFill = document.getElementById('kpi-deep-fill');
    if (deepFill) {
      deepFill.style.width = Math.min(100, Math.max(0, Math.round(deep))) + '%';
    }
    var deepHint = document.getElementById('kpi-deep-hint');
    if (deepHint) {
      var avg = weeklyAvgScore(data);
      deepHint.textContent = avg === null ? '本周均值 —' : ('本周均值 ' + avg + '%');
    }
    var deepTrend = document.getElementById('kpi-deep-trend');
    if (deepTrend) deepTrend.textContent = '—';
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
    updateKpiCards(data);
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
