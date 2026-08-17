document.addEventListener('alpine:init', () => {
  Alpine.data('teacherManage', () => ({
    // ---- State ----
    questions: [],
    showModal: false,
    showImportModal: false,
    editingQuestion: null,
    error: '',
    success: '',
    loading: false,
    filter: { type: '', difficulty: '', search: '' },
    form: {
      type: 'choice', content: '', options: '', answer: '',
      difficulty: 'medium', tags: '', course_id: null,
    },
    importFile: null,
    importFileName: '',

    // ---- Computed ----
    get typeCounts() {
      const counts = { choice: 0, fill: 0, code: 0, essay: 0 };
      this.questions.forEach(q => { if (counts[q.type] !== undefined) counts[q.type]++; });
      return counts;
    },

    // ---- Lifecycle ----
    async init() {
      await Auth.fetchMe();
      if (!Auth.isTeacher()) { window.location.href = '/login.html'; return; }
      await this.loadQuestions();
    },

    // ---- Question CRUD ----
    async loadQuestions() {
      const params = new URLSearchParams();
      if (this.filter.type) params.set('type', this.filter.type);
      if (this.filter.difficulty) params.set('difficulty', this.filter.difficulty);
      if (this.filter.search) params.set('search', this.filter.search);
      const qs = params.toString();
      try {
        const res = await fetch(`/api/teacher/questions${qs ? '?' + qs : ''}`);
        const data = await res.json();
        this.questions = data.questions || [];
      } catch (_) { this.questions = []; }
    },

    openCreateModal() {
      this.editingQuestion = null;
      this.form = { type: 'choice', content: '', options: '', answer: '', difficulty: 'medium', tags: '', course_id: null };
      this.showModal = true;
      this.error = '';
    },

    openEditModal(q) {
      this.editingQuestion = q;
      this.form = {
        type: q.type || 'choice',
        content: q.content || '',
        options: typeof q.options === 'string' ? q.options : JSON.stringify(q.options || []),
        answer: q.answer || '',
        difficulty: q.difficulty || 'medium',
        tags: typeof q.tags === 'string' ? q.tags : JSON.stringify(q.tags || []),
        course_id: q.course_id || null,
      };
      this.showModal = true;
      this.error = '';
    },

    async saveQuestion() {
      if (!this.form.content.trim()) { this.error = '请输入题目内容'; return; }
      if (!this.form.answer.trim()) { this.error = '请输入正确答案'; return; }
      this.loading = true; this.error = '';
      try {
        let options = null;
        const rawOpts = this.form.options.trim();
        if (rawOpts) {
          try { options = JSON.parse(rawOpts); }
          catch (e) { this.error = '选项JSON格式错误'; this.loading = false; return; }
        }
        let tags = null;
        const rawTags = this.form.tags.trim();
        if (rawTags) {
          try { tags = JSON.parse(rawTags); }
          catch (e) { this.error = '标签JSON格式错误'; this.loading = false; return; }
        }

        const url = this.editingQuestion
          ? `/api/teacher/question/${this.editingQuestion.id}`
          : '/api/teacher/question';
        const method = this.editingQuestion ? 'PUT' : 'POST';
        const res = await fetch(url, {
          method,
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            type: this.form.type,
            content: this.form.content,
            options,
            answer: this.form.answer,
            difficulty: this.form.difficulty,
            tags,
            course_id: this.form.course_id,
          }),
        });
        const data = await res.json();
        if (data.success) {
          this.showModal = false;
          await this.loadQuestions();
        } else { this.error = data.detail || '保存失败'; }
      } catch (e) { this.error = '请求失败: ' + e.message; }
      finally { this.loading = false; }
    },

    async deleteQuestion(id) {
      if (!confirm('确认删除此题？')) return;
      await fetch(`/api/teacher/question/${id}`, { method: 'DELETE' });
      await this.loadQuestions();
    },

    // ---- Batch Import (CSV/JSON file upload) ----
    openImportModal() {
      this.importFile = null;
      this.importFileName = '';
      this.showImportModal = true;
      this.error = '';
    },

    handleImportFileSelect(event) {
      const file = event.target.files[0];
      if (file) {
        this.importFile = file;
        this.importFileName = file.name;
      }
    },

    async importQuestions() {
      if (!this.importFile) { this.error = '请选择文件'; return; }
      const ext = this.importFile.name.split('.').pop().toLowerCase();
      if (!['csv', 'json'].includes(ext)) { this.error = '仅支持CSV或JSON文件'; return; }
      this.loading = true; this.error = '';
      try {
        const formData = new FormData();
        formData.append('file', this.importFile);
        formData.append('format', ext);
        const res = await fetch('/api/teacher/questions/import', {
          method: 'POST',
          body: formData,
        });
        const data = await res.json();
        if (data.success) {
          this.showImportModal = false;
          this.success = `成功导入 ${data.count || 0} 道题目`;
          await this.loadQuestions();
          setTimeout(() => { this.success = ''; }, 3000);
        } else { this.error = data.detail || '导入失败'; }
      } catch (e) { this.error = '导入请求失败'; }
      finally { this.loading = false; }
    },

    // ---- Helpers ----
    truncate(str, n) {
      if (!str) return '';
      return str.length > n ? str.slice(0, n) + '...' : str;
    },
    typeLabel(t) {
      return { choice: '选择', fill: '填空', code: '编程', essay: '简答' }[t] || t;
    },
    diffLabel(d) {
      return { easy: '简单', medium: '中等', hard: '困难' }[d] || d;
    },
  }));
});
