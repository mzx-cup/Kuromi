document.addEventListener('alpine:init', () => {
  Alpine.data('teacherExam', () => ({
    // ---- State ----
    exams: [],
    classes: [],
    questions: [],
    showCreateModal: false,
    showEditModal: false,
    showGradeModal: false,
    showResultModal: false,
    showAnalysisModal: false,
    editingExam: null,
    error: '',
    success: '',
    loading: false,

    // Create/Edit form
    form: {
      title: '', duration: 120, classIds: [], questionIds: [],
      description: '', start_time: '', end_time: '',
    },
    createMode: 'manual', // 'manual' | 'ai'

    // AI generate form
    aiForm: { topic: '', difficulty: 'medium', questionCount: 10, classIds: [] },

    // Grading state
    gradingExam: null,
    gradingResults: [],
    gradingIndex: 0,
    gradingScores: {},

    // Result state
    resultExam: null,
    results: [],

    // Analysis state
    analysisExam: null,
    analysisData: null,
    analysisChart: null,

    // ---- Lifecycle ----
    async init() {
      await Auth.fetchMe();
      if (!Auth.isTeacher()) { window.location.href = '/login.html'; return; }
      await this.loadExams();
    },

    // ---- Exam Loading ----
    async loadExams() {
      try {
        const res = await fetch('/api/teacher/exams');
        const data = await res.json();
        this.exams = data.exams || [];
      } catch (_) { this.exams = []; }
    },

    // ---- Manual Create ----
    async openCreateModal() {
      this.createMode = 'manual';
      this.showCreateModal = true;
      this.error = '';
      this.form = { title: '', duration: 120, classIds: [], questionIds: [], description: '', start_time: '', end_time: '' };
      try {
        const [clsRes, qRes] = await Promise.all([
          fetch('/api/teacher/classes'),
          fetch('/api/teacher/questions'),
        ]);
        const clsData = await clsRes.json();
        const qData = await qRes.json();
        this.classes = clsData.classes || [];
        this.questions = qData.questions || [];
      } catch (_) { this.classes = []; this.questions = []; }
    },

    // ---- AI Auto-Generate ----
    openAiCreateModal() {
      this.createMode = 'ai';
      this.showCreateModal = true;
      this.error = '';
      this.aiForm = { topic: '', difficulty: 'medium', questionCount: 10, classIds: [] };
      // Also load classes for target selection
      fetch('/api/teacher/classes').then(r => r.json()).then(d => { this.classes = d.classes || []; }).catch(() => {});
    },

    async aiGenerateExam() {
      if (!this.aiForm.topic.trim()) { this.error = '请输入考试主题/知识点'; return; }
      this.loading = true; this.error = '';
      try {
        const res = await fetch('/api/teacher/exam', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            generate_mode: 'ai',
            topic: this.aiForm.topic,
            difficulty: this.aiForm.difficulty,
            question_count: this.aiForm.questionCount,
            class_ids: this.aiForm.classIds,
          }),
        });
        const data = await res.json();
        if (data.success) {
          this.showCreateModal = false;
          await this.loadExams();
          this.success = `AI自动组卷成功: ${data.title || ''}`;
          setTimeout(() => { this.success = ''; }, 3000);
        } else { this.error = data.detail || 'AI组卷失败'; }
      } catch (e) { this.error = 'AI组卷请求失败'; }
      finally { this.loading = false; }
    },

    // ---- Manual Create Submit ----
    async createExam() {
      if (!this.form.title.trim()) { this.error = '请输入考试标题'; return; }
      this.loading = true; this.error = '';
      try {
        const res = await fetch('/api/teacher/exam', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            title: this.form.title,
            description: this.form.description,
            question_ids: this.form.questionIds,
            class_ids: this.form.classIds,
            duration: this.form.duration,
            start_time: this.form.start_time || null,
            end_time: this.form.end_time || null,
          }),
        });
        const data = await res.json();
        if (data.success) { this.showCreateModal = false; await this.loadExams(); }
        else { this.error = data.detail || '创建失败'; }
      } catch (e) { this.error = '请求失败'; }
      finally { this.loading = false; }
    },

    // ---- Edit Exam ----
    async openEditModal(exam) {
      this.editingExam = exam;
      this.form = {
        title: exam.title || '',
        description: exam.description || '',
        duration: exam.duration || 120,
        classIds: exam.class_ids || [],
        questionIds: exam.question_ids || [],
        start_time: exam.start_time || '',
        end_time: exam.end_time || '',
      };
      try {
        const [clsRes, qRes] = await Promise.all([
          fetch('/api/teacher/classes'),
          fetch('/api/teacher/questions'),
        ]);
        this.classes = (await clsRes.json()).classes || [];
        this.questions = (await qRes.json()).questions || [];
      } catch (_) {}
      this.showEditModal = true;
      this.error = '';
    },

    async updateExam() {
      if (!this.form.title.trim()) { this.error = '请输入考试标题'; return; }
      this.loading = true; this.error = '';
      try {
        const res = await fetch(`/api/teacher/exam/${this.editingExam.id}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            title: this.form.title,
            description: this.form.description,
            question_ids: this.form.questionIds,
            class_ids: this.form.classIds,
            duration: this.form.duration,
            start_time: this.form.start_time || null,
            end_time: this.form.end_time || null,
          }),
        });
        const data = await res.json();
        if (data.success) { this.showEditModal = false; await this.loadExams(); }
        else { this.error = data.detail || '更新失败'; }
      } catch (e) { this.error = '请求失败'; }
      finally { this.loading = false; }
    },

    // ---- Status Actions ----
    async publishExam(id) {
      await fetch(`/api/teacher/exam/${id}/publish`, { method: 'POST' });
      await this.loadExams();
    },

    async archiveExam(id) {
      await fetch(`/api/teacher/exam/${id}/archive`, { method: 'POST' });
      await this.loadExams();
    },

    async deleteExam(id) {
      if (!confirm('确认删除此考试？')) return;
      await fetch(`/api/teacher/exam/${id}`, { method: 'DELETE' });
      await this.loadExams();
    },

    // ---- Proper Grading UI (NO alert()) ----
    async openGradeModal(exam) {
      this.gradingExam = exam;
      this.gradingIndex = 0;
      this.gradingScores = {};
      this.error = '';
      try {
        const res = await fetch(`/api/teacher/exam/${exam.id}/results`);
        const data = await res.json();
        this.gradingResults = (data.results || []).filter(r => r.graded_by === 'auto' || r.score === null);
      } catch (_) { this.gradingResults = []; }
      this.showGradeModal = true;
    },

    get currentGrading() {
      return this.gradingResults[this.gradingIndex] || null;
    },

    get gradingProgress() {
      return this.gradingResults.length
        ? `${this.gradingIndex + 1} / ${this.gradingResults.length}`
        : '0 / 0';
    },

    async aiPrescore() {
      const r = this.currentGrading;
      if (!r) return;
      this.loading = true;
      try {
        const res = await fetch(`/api/teacher/exam/${this.gradingExam.id}/grade`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ result_id: r.id }),
        });
        const data = await res.json();
        if (data.success) {
          this.gradingResults[this.gradingIndex] = { ...r, ai_score: data.ai_score, ai_comment: data.ai_comment };
        } else { this.error = data.detail || 'AI预批改失败'; }
      } catch (_) { this.error = 'AI预批改请求失败'; }
      finally { this.loading = false; }
    },

    async confirmGrade() {
      const r = this.currentGrading;
      if (!r) return;
      const score = this.gradingScores[r.id];
      if (score === undefined || score === '' || score === null) {
        this.error = '请输入最终分数';
        return;
      }
      this.loading = true; this.error = '';
      try {
        const res = await fetch(`/api/teacher/exam/${this.gradingExam.id}/grade`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ result_id: r.id, final_score: parseFloat(score) }),
        });
        const data = await res.json();
        if (data.success) {
          if (this.gradingIndex < this.gradingResults.length - 1) {
            this.gradingIndex++;
          } else {
            this.showGradeModal = false;
            this.success = '所有答卷批改完成';
            setTimeout(() => { this.success = ''; }, 3000);
          }
        } else { this.error = data.detail || '保存分数失败'; }
      } catch (_) { this.error = '保存失败'; }
      finally { this.loading = false; }
    },

    prevGrading() { if (this.gradingIndex > 0) this.gradingIndex--; },
    nextGrading() { if (this.gradingIndex < this.gradingResults.length - 1) this.gradingIndex++; },

    // ---- View Results (Proper table, NOT alert()) ----
    async openResultModal(exam) {
      this.resultExam = exam;
      this.error = '';
      try {
        const res = await fetch(`/api/teacher/exam/${exam.id}/results`);
        const data = await res.json();
        this.results = data.results || [];
      } catch (_) { this.results = []; }
      this.showResultModal = true;
    },

    // ---- Grade Analysis (ECharts, NOT alert()) ----
    async openAnalysisModal(exam) {
      this.analysisExam = exam;
      this.loading = true; this.error = '';
      try {
        const res = await fetch(`/api/teacher/exam/${exam.id}/analysis`);
        const data = await res.json();
        this.analysisData = data;
        this.showAnalysisModal = true;
        await this.$nextTick();
        this.initAnalysisChart();
      } catch (_) { this.error = '无法加载分析数据'; }
      finally { this.loading = false; }
    },

    initAnalysisChart() {
      const el = this.$refs.analysisChart;
      if (!el || !this.analysisData) return;
      if (this.analysisChart) this.analysisChart.dispose();
      this.analysisChart = echarts.init(el);

      const dist = this.analysisData.score_distribution || {};
      const ranges = ['0-59', '60-69', '70-79', '80-89', '90-100'];
      const counts = ranges.map(r => dist[r] || 0);

      this.analysisChart.setOption({
        title: { text: '成绩分布', left: 'center', textStyle: { fontSize: 14, color: '#64748b' } },
        tooltip: { trigger: 'axis' },
        xAxis: {
          type: 'category', data: ranges,
          axisLabel: { color: '#94a3b8', fontSize: 11 },
        },
        yAxis: {
          type: 'value', name: '人数',
          axisLabel: { color: '#94a3b8' },
          splitLine: { lineStyle: { color: '#f1f5f9' } },
        },
        series: [{
          data: counts, type: 'bar', barWidth: '50%',
          itemStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: '#6366f1' }, { offset: 1, color: '#a78bfa' },
            ]),
            borderRadius: [4, 4, 0, 0],
          },
          label: { show: true, position: 'top', fontSize: 12 },
        }],
        grid: { top: 40, right: 20, bottom: 30, left: 40 },
      });
    },

    // ---- Checkbox Helpers ----
    toggleClass(id) {
      const idx = this.form.classIds.indexOf(id);
      idx >= 0 ? this.form.classIds.splice(idx, 1) : this.form.classIds.push(id);
    },
    toggleQuestion(id) {
      const idx = this.form.questionIds.indexOf(id);
      idx >= 0 ? this.form.questionIds.splice(idx, 1) : this.form.questionIds.push(id);
    },
    toggleAiClass(id) {
      const idx = this.aiForm.classIds.indexOf(id);
      idx >= 0 ? this.aiForm.classIds.splice(idx, 1) : this.aiForm.classIds.push(id);
    },
    isChecked(arr, id) { return arr.includes(id); },

    // ---- Utilities ----
    formatDate(d) { return (d || '').slice(0, 10); },
    truncate(str, n) { if (!str) return ''; return str.length > n ? str.slice(0, n) + '...' : str; },
    statusLabel(s) {
      return { draft: '草稿', published: '已发布', closed: '已关闭', archived: '已归档' }[s] || s;
    },
    typeLabel(t) {
      return { choice: '选择', fill: '填空', code: '编程', essay: '简答' }[t] || t;
    },
  }));
});
