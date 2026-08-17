document.addEventListener('alpine:init', () => {
  Alpine.data('dataDashboard', () => ({
    hierarchy: 'school', trends: [], sseEvents: [], sseCleanup: null, error: '',
    hierarchyLabels: { school: '学校', college: '学院/专业', class: '班级', personal: '个人' },
    stats: { total_courses: 0, total_students: 0, completion_rate: 0, total_hours: 0 },
    trendsChart: null, radarChart: null, completionChart: null, mapChart: null,

    async init() {
      await Auth.fetchMe();
      if (!Auth.me || !Auth.me.id) { window.location.href = '/login.html'; return; }
      await this.loadStats(); await this.loadTrends(); this.initCharts(); this.connectSSE();
      this.$cleanup(() => this.disposeAll());
    },

    async loadStats() {
      try { const res = await fetch(`/api/datacenter/stats?level=${this.hierarchy}`); const data = await res.json();
        if (data) { this.stats = { total_courses: data.total_courses || data.course_count || 0, total_students: data.total_students || data.student_count || 0, completion_rate: data.completion_rate || 0, total_hours: data.total_hours || data.study_hours || 0 }; }
      } catch (_) {}
    },

    async loadTrends() {
      try { const res = await fetch(`/api/datacenter/trends?level=${this.hierarchy}`); const data = await res.json(); this.trends = data.trends || data.points || [];
        await this.$nextTick(); this.updateTrendsChart(); this.updateRadarChart(); this.updateCompletionChart(); this.updateMapChart();
      } catch (_) { this.trends = []; }
    },

    async switchHierarchy(level) { this.hierarchy = level; await this.loadStats(); await this.loadTrends(); },
    initCharts() { this.$nextTick(() => { this.initTrendsChart(); this.initRadarChart(); this.initCompletionChart(); this.initMapChart(); }); },

    initTrendsChart() { const el = this.$refs.trendsChart; if (!el) return; if (this.trendsChart) this.trendsChart.dispose(); this.trendsChart = echarts.init(el); },
    updateTrendsChart() { if (!this.trendsChart) return; const dates = this.trends.map(t => t.date || t.label || ''); const values = this.trends.map(t => t.value || t.count || 0); this.trendsChart.setOption({ title: { text: '学习趋势', left: 'center', textStyle: { fontSize: 14, color: '#94a3b8' } }, tooltip: { trigger: 'axis' }, xAxis: { type: 'category', data: dates, axisLabel: { color: '#64748b', fontSize: 11 } }, yAxis: { type: 'value', axisLabel: { color: '#64748b' }, splitLine: { lineStyle: { color: 'rgba(148,163,184,0.1)' } } }, series: [{ data: values, type: 'line', smooth: true, symbol: 'circle', symbolSize: 6, lineStyle: { color: '#a78bfa', width: 2 }, itemStyle: { color: '#a78bfa' }, areaStyle: { color: new echarts.graphic.LinearGradient(0,0,0,1, [{ offset: 0, color: 'rgba(167,139,250,0.3)' }, { offset: 1, color: 'rgba(167,139,250,0.02)' }]) } }], grid: { top: 40, right: 20, bottom: 30, left: 45 } }); },

    initRadarChart() { const el = this.$refs.radarChart; if (!el) return; if (this.radarChart) this.radarChart.dispose(); this.radarChart = echarts.init(el); },
    updateRadarChart() { if (!this.radarChart) return; this.radarChart.setOption({ title: { text: '综合指标', left: 'center', textStyle: { fontSize: 14, color: '#94a3b8' } }, tooltip: {}, radar: { indicator: [{ name: '课程数', max: 100 }, { name: '学生数', max: 500 }, { name: '完成率', max: 100 }, { name: '学习时长', max: 1000 }, { name: '活跃度', max: 100 }], axisName: { color: '#94a3b8' }, splitArea: { areaStyle: { color: ['rgba(167,139,250,0.02)', 'rgba(167,139,250,0.05)'] } }, splitLine: { lineStyle: { color: 'rgba(148,163,184,0.15)' } }, axisLine: { lineStyle: { color: 'rgba(148,163,184,0.15)' } } }, series: [{ type: 'radar', data: [{ value: [this.stats.total_courses || 0, this.stats.total_students || 0, (this.stats.completion_rate || 0) * 100, this.stats.total_hours || 0, 0], name: this.hierarchyLabels[this.hierarchy] || '数据', areaStyle: { color: 'rgba(99,102,241,0.2)' }, lineStyle: { color: '#818cf8' }, itemStyle: { color: '#818cf8' } }] }] }); },

    initCompletionChart() { const el = this.$refs.completionChart; if (!el) return; if (this.completionChart) this.completionChart.dispose(); this.completionChart = echarts.init(el); },
    updateCompletionChart() { if (!this.completionChart) return; this.completionChart.setOption({ title: { text: '完成率分布', left: 'center', textStyle: { fontSize: 14, color: '#94a3b8' } }, tooltip: { trigger: 'item' }, series: [{ name: '完成率', type: 'pie', radius: ['45%', '70%'], center: ['50%', '55%'], label: { color: '#94a3b8', fontSize: 11 }, data: [{ value: Math.round((this.stats.completion_rate || 0) * 100), name: '已完成', itemStyle: { color: '#818cf8' } }, { value: Math.round(100 - (this.stats.completion_rate || 0) * 100), name: '未完成', itemStyle: { color: 'rgba(148,163,184,0.2)' } }] }] }); },

    initMapChart() { const el = this.$refs.mapChart; if (!el) return; if (this.mapChart) this.mapChart.dispose(); this.mapChart = echarts.init(el); },
    updateMapChart() { if (!this.mapChart) return; const coords = this.trends.filter(t => t.lat && t.lng).map(t => ({ value: [t.lng, t.lat, t.value || 1], name: t.label || t.date || '' })); this.mapChart.setOption({ title: { text: '分布地图', left: 'center', textStyle: { fontSize: 14, color: '#94a3b8' } }, tooltip: { trigger: 'item', formatter: p => p.name ? `${p.name}: ${p.value[2]}` : '' }, xAxis: { type: 'value', show: false, min: 73, max: 135 }, yAxis: { type: 'value', show: false, min: 18, max: 54 }, series: [{ type: 'scatter', data: coords.length ? coords : [[116, 39, 1]], symbolSize: d => Math.min(20, 6 + (d[2] || 1) * 2), itemStyle: { color: '#818cf8', opacity: 0.7 }, emphasis: { itemStyle: { color: '#a78bfa', opacity: 1 } } }], grid: { top: 40, right: 10, bottom: 10, left: 10 } }); },

    connectSSE() { try { const es = new EventSource(`/api/datacenter/events?level=${this.hierarchy}`); es.onmessage = (e) => { try { const d = JSON.parse(e.data); this.sseEvents.unshift(d); if (this.sseEvents.length > 50) this.sseEvents.pop(); } catch (_) {} }; es.onerror = () => {}; this.sseCleanup = () => { es.close(); }; } catch (_) {} },

    disposeAll() { if (this.trendsChart) { this.trendsChart.dispose(); this.trendsChart = null; } if (this.radarChart) { this.radarChart.dispose(); this.radarChart = null; } if (this.completionChart) { this.completionChart.dispose(); this.completionChart = null; } if (this.mapChart) { this.mapChart.dispose(); this.mapChart = null; } if (this.sseCleanup) { this.sseCleanup(); this.sseCleanup = null; } },

    formatPercent(v) { return v != null ? (v * 100).toFixed(1) + '%' : '--'; },
    timeAgo(ts) { if (!ts) return ''; const d = Math.floor((Date.now() - new Date(ts).getTime()) / 1000); if (d < 60) return `${d}s ago`; if (d < 3600) return `${Math.floor(d/60)}m ago`; return `${Math.floor(d/3600)}h ago`; },
  }));
});
