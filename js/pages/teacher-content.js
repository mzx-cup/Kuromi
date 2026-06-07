document.addEventListener('alpine:init', () => {
  Alpine.data('teacherContent', () => ({
    activeTab: 'courses', courses: [], resources: [], selectedCourse: null,
    editingNode: null, showCourseModal: false, showResourceModal: false, showAiReviewModal: false,
    error: '', success: '', loading: false,
    form: { title: '', description: '', parent_id: null },
    resourceForm: { title: '', type: 'document', file: null, fileName: '', course_id: null },
    aiReview: { content: '', result: null, loading: false },

    async init() {
      await Auth.fetchMe();
      if (!Auth.isTeacher()) { window.location.href = '/login.html'; return; }
      await this.loadCourses();
    },

    async loadCourses() {
      try { const res = await fetch('/api/teacher/courses'); const data = await res.json(); this.courses = data.courses || []; }
      catch (_) { this.courses = []; }
    },

    get courseTree() {
      const map = {}, roots = [];
      this.courses.forEach(c => { map[c.id] = { ...c, children: [] }; });
      this.courses.forEach(c => { if (c.parent_id && map[c.parent_id]) map[c.parent_id].children.push(map[c.id]); else roots.push(map[c.id]); });
      return roots;
    },

    openCourseModal(parentId = null) { this.form = { title: '', description: '', parent_id: parentId }; this.editingNode = null; this.showCourseModal = true; this.error = ''; },
    openEditCourseModal(course) { this.editingNode = course; this.form = { title: course.title || '', description: course.description || '', parent_id: course.parent_id || null }; this.showCourseModal = true; this.error = ''; },

    async saveCourse() {
      if (!this.form.title.trim()) { this.error = '请输入课程/章节标题'; return; }
      this.loading = true; this.error = '';
      try {
        const url = this.editingNode ? `/api/teacher/course/${this.editingNode.id}` : '/api/teacher/course';
        const method = this.editingNode ? 'PUT' : 'POST';
        const res = await fetch(url, { method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(this.form) });
        const data = await res.json();
        if (data.success) { this.showCourseModal = false; await this.loadCourses(); }
        else { this.error = data.detail || '保存失败'; }
      } catch (_) { this.error = '请求失败'; }
      finally { this.loading = false; }
    },

    async deleteCourse(id) { if (!confirm('确认删除此节点及其子节点？')) return; await fetch(`/api/teacher/course/${id}`, { method: 'DELETE' }); await this.loadCourses(); },

    async loadResources(courseId) { this.selectedCourse = courseId; try { const res = await fetch(`/api/teacher/course/${courseId}/resources`); const data = await res.json(); this.resources = data.resources || []; } catch (_) { this.resources = []; } },
    openResourceModal(courseId) { this.resourceForm = { title: '', type: 'document', file: null, fileName: '', course_id: courseId }; this.showResourceModal = true; this.error = ''; },
    handleResourceFile(event) { const file = event.target.files[0]; if (file) { this.resourceForm.file = file; this.resourceForm.fileName = file.name; } },

    async uploadResource() {
      if (!this.resourceForm.title.trim()) { this.error = '请输入资源标题'; return; }
      if (!this.resourceForm.file) { this.error = '请选择文件'; return; }
      this.loading = true; this.error = '';
      try {
        const fd = new FormData(); fd.append('file', this.resourceForm.file); fd.append('title', this.resourceForm.title); fd.append('type', this.resourceForm.type); fd.append('course_id', this.resourceForm.course_id);
        const res = await fetch('/api/teacher/resources/upload', { method: 'POST', body: fd });
        const data = await res.json();
        if (data.success) { this.showResourceModal = false; await this.loadResources(this.resourceForm.course_id); }
        else { this.error = data.detail || '上传失败'; }
      } catch (_) { this.error = '上传请求失败'; }
      finally { this.loading = false; }
    },

    async deleteResource(id) { await fetch(`/api/teacher/resource/${id}`, { method: 'DELETE' }); await this.loadResources(this.selectedCourse); },
    openAiReviewModal() { this.aiReview = { content: '', result: null, loading: false }; this.showAiReviewModal = true; this.error = ''; },

    async runAiReview() {
      if (!this.aiReview.content.trim()) { this.error = '请输入需要审核的内容'; return; }
      this.aiReview.loading = true; this.error = '';
      try {
        const res = await fetch('/api/teacher/ai/review', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ content: this.aiReview.content }) });
        const data = await res.json();
        if (data.success) { this.aiReview.result = data.result || data; }
        else { this.error = data.detail || 'AI审核失败'; }
      } catch (_) { this.error = '请求失败'; }
      finally { this.aiReview.loading = false; }
    },

    formatBytes(b) { if (!b) return '-'; return b < 1024 ? b + 'B' : b < 1048576 ? (b/1024).toFixed(1)+'KB' : (b/1048576).toFixed(1)+'MB'; },
    formatDate(d) { return (d || '').slice(0, 10); },
  }));
});
