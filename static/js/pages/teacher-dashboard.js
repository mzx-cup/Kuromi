document.addEventListener('alpine:init', () => {
  Alpine.data('teacherDashboard', () => ({
    // ---- Stat Cards (spec labels) ----
    stats: { classes: 0, courses: 0, pendingReviews: 0, avgScore: '--' },

    // ---- Class List ----
    classes: [],

    // ---- Recent Tasks ----
    recentTasks: [],

    // ---- AI Suggestions ----
    aiSuggestions: [],

    // ---- ECharts instances ----
    barChart: null,
    radarChart: null,

    // ---- Lifecycle ----
    async init() {
      await Auth.fetchMe();
      if (!Auth.isTeacher()) { window.location.href = '/login.html'; return; }
      await Promise.all([
        this.loadStats(),
        this.loadClasses(),
        this.loadRecentTasks(),
        this.loadAiSuggestions(),
      ]);
      await this.$nextTick();
      this.initBarChart();
      this.initRadarChart();
    },

    // ---- Data Loading ----
    async loadStats() {
      try {
        const res = await fetch('/api/teacher/dashboard');
        const data = await res.json();
        if (data.success) {
          this.stats = {
            classes: data.class_count || 0,
            courses: data.course_count || 0,
            pendingReviews: data.pending_review_count || 0,
            avgScore: data.avg_score != null ? data.avg_score.toFixed(1) : '--',
          };
        }
      } catch (_) { /* keep defaults */ }
    },

    async loadClasses() {
      try {
        const res = await fetch('/api/teacher/classes');
        const data = await res.json();
        this.classes = (data.classes || []).slice(0, 6);
      } catch (_) { this.classes = []; }
    },

    async loadRecentTasks() {
      try {
        const res = await fetch('/api/teacher/dashboard/recent-tasks');
        const data = await res.json();
        this.recentTasks = data.tasks || [];
      } catch (_) { this.recentTasks = []; }
    },

    async loadAiSuggestions() {
      try {
        const res = await fetch('/api/teacher/dashboard/ai-suggestions');
        const data = await res.json();
        this.aiSuggestions = data.suggestions || [];
      } catch (_) { this.aiSuggestions = []; }
    },

    // ---- ECharts: Class Progress Bar Chart ----
    initBarChart() {
      const el = this.$refs.barChart;
      if (!el) return;
      if (this.barChart) this.barChart.dispose();
      this.barChart = echarts.init(el);

      const names = this.classes.map(c => c.name || `班级${c.id}`);
      const scores = this.classes.map(c => c.avg_score || 0);

      this.barChart.setOption({
        title: { text: '班级学习概览', left: 'center', textStyle: { fontSize: 14, color: '#64748b' } },
        tooltip: { trigger: 'axis' },
        xAxis: {
          type: 'category',
          data: names.length ? names : ['暂无班级'],
          axisLabel: { color: '#94a3b8', fontSize: 12 },
          axisLine: { lineStyle: { color: '#e2e8f0' } },
        },
        yAxis: {
          type: 'value', name: '平均分', max: 100,
          axisLabel: { color: '#94a3b8' },
          splitLine: { lineStyle: { color: '#f1f5f9' } },
        },
        series: [{
          data: scores.length ? scores : [0],
          type: 'bar', barWidth: '40%',
          itemStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: '#6366f1' }, { offset: 1, color: '#a78bfa' },
            ]),
            borderRadius: [6, 6, 0, 0],
          },
          label: { show: true, position: 'top', color: '#6366f1', fontSize: 12 },
        }],
        grid: { top: 40, right: 20, bottom: 30, left: 50 },
      });
      window.addEventListener('resize', () => this.barChart && this.barChart.resize());
    },

    // ---- ECharts: Capability Radar Chart ----
    initRadarChart() {
      const el = this.$refs.radarChart;
      if (!el) return;
      if (this.radarChart) this.radarChart.dispose();
      this.radarChart = echarts.init(el);

      this.radarChart.setOption({
        title: { text: '学生能力维度', left: 'center', textStyle: { fontSize: 14, color: '#64748b' } },
        radar: {
          indicator: [
            { name: '编程能力', max: 100 },
            { name: '理论知识', max: 100 },
            { name: '实践操作', max: 100 },
            { name: '问题解决', max: 100 },
            { name: '协作沟通', max: 100 },
          ],
          axisName: { color: '#94a3b8', fontSize: 11 },
          shape: 'polygon', splitNumber: 4,
        },
        series: [{
          type: 'radar',
          data: [{
            value: [72, 68, 75, 80, 65], name: '班级平均',
            areaStyle: { color: 'rgba(99,102,241,0.2)' },
            lineStyle: { color: '#6366f1', width: 2 },
            itemStyle: { color: '#6366f1' },
          }],
        }],
      });
      window.addEventListener('resize', () => this.radarChart && this.radarChart.resize());
    },

    // ---- Helpers ----
    getTaskStatusLabel(s) {
      return { pending: '待批改', grading: '批改中', done: '已完成' }[s] || s;
    },

    // ---- Cleanup ----
    destroy() {
      if (this.barChart) { this.barChart.dispose(); this.barChart = null; }
      if (this.radarChart) { this.radarChart.dispose(); this.radarChart = null; }
    },
  }));
});
