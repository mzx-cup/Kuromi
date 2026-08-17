document.addEventListener('alpine:init', () => {
  Alpine.data('teacherClass', () => ({
    // ---- State ----
    classes: [],
    groups: [],
    selectedClass: null,
    students: [],
    studentProfile: null,
    showCreateModal: false,
    showEditModal: false,
    showImportModal: false,
    showGroupModal: false,
    showProfileModal: false,
    editingClass: null,
    error: '',
    success: '',
    loading: false,
    form: { name: '', subject: '', description: '' },
    importForm: { classId: null, csvFile: null, csvFileName: '' },
    groupForm: { name: '', classId: null },

    // ---- Lifecycle ----
    async init() {
      await Auth.fetchMe();
      if (!Auth.isTeacher()) { window.location.href = '/login.html'; return; }
      const urlParams = new URLSearchParams(window.location.search);
      const classId = urlParams.get('id');
      await this.loadClasses();
      if (classId) {
        const found = this.classes.find(c => c.id === parseInt(classId));
        if (found) await this.openStudents(found);
      }
    },

    // ---- Class CRUD ----
    async loadClasses() {
      try {
        const res = await fetch('/api/teacher/classes');
        const data = await res.json();
        this.classes = data.classes || [];
      } catch (_) { this.classes = []; }
    },

    openCreateModal() {
      this.editingClass = null;
      this.form = { name: '', subject: '', description: '' };
      this.showCreateModal = true;
      this.error = '';
    },

    openEditModal(cls) {
      this.editingClass = cls;
      this.form = { name: cls.name || '', subject: cls.subject || '', description: cls.description || '' };
      this.showEditModal = true;
      this.error = '';
    },

    async saveClass() {
      if (!this.form.name.trim()) { this.error = '请输入班级名称'; return; }
      this.loading = true; this.error = '';
      try {
        const url = this.editingClass ? `/api/teacher/class/${this.editingClass.id}` : '/api/teacher/class';
        const method = this.editingClass ? 'PUT' : 'POST';
        const res = await fetch(url, {
          method,
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(this.form),
        });
        const data = await res.json();
        if (data.success) {
          this.showCreateModal = false;
          this.showEditModal = false;
          this.form = { name: '', subject: '', description: '' };
          await this.loadClasses();
        } else { this.error = data.detail || '保存失败'; }
      } catch (e) { this.error = '请求失败'; }
      finally { this.loading = false; }
    },

    async deleteClass(id) {
      if (!confirm('确认删除班级及所有学生关联？此操作不可恢复。')) return;
      await fetch(`/api/teacher/class/${id}`, { method: 'DELETE' });
      await this.loadClasses();
      if (this.selectedClass && this.selectedClass.id === id) {
        this.selectedClass = null;
        this.students = [];
      }
    },

    // ---- Student Management ----
    async openStudents(cls) {
      this.selectedClass = cls;
      try {
        const res = await fetch(`/api/teacher/class/${cls.id}/students`);
        const data = await res.json();
        this.students = data.students || [];
      } catch (_) { this.students = []; }
    },

    // ---- CSV File Upload (NOT textarea) ----
    openImportModal(cls) {
      this.importForm = { classId: cls.id, csvFile: null, csvFileName: '' };
      this.showImportModal = true;
      this.error = '';
      this.success = '';
    },

    handleFileSelect(event) {
      const file = event.target.files[0];
      if (file) {
        this.importForm.csvFile = file;
        this.importForm.csvFileName = file.name;
      }
    },

    async importStudentsFromCSV() {
      if (!this.importForm.csvFile) { this.error = '请选择CSV文件'; return; }
      this.loading = true; this.error = '';
      try {
        const formData = new FormData();
        formData.append('file', this.importForm.csvFile);
        formData.append('class_id', this.importForm.classId);
        const res = await fetch('/api/teacher/students/import', {
          method: 'POST',
          body: formData,  // No Content-Type header — browser sets multipart/form-data
        });
        const data = await res.json();
        if (data.success) {
          this.showImportModal = false;
          this.success = `成功导入 ${data.count} 名学生`;
          if (this.selectedClass) await this.openStudents(this.selectedClass);
          setTimeout(() => { this.success = ''; }, 3000);
        } else { this.error = data.detail || '导入失败'; }
      } catch (e) { this.error = '导入请求失败'; }
      finally { this.loading = false; }
    },

    // ---- Class Grouping ----
    async openGroupModal(cls) {
      this.selectedClass = cls;
      this.groupForm = { name: '', classId: cls.id };
      try {
        const res = await fetch(`/api/teacher/class/${cls.id}/groups`);
        const data = await res.json();
        this.groups = data.groups || [];
      } catch (_) { this.groups = []; }
      this.showGroupModal = true;
      this.error = '';
    },

    async createGroup() {
      if (!this.groupForm.name.trim()) { this.error = '请输入分组名称'; return; }
      this.loading = true; this.error = '';
      try {
        const res = await fetch('/api/teacher/class/group', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(this.groupForm),
        });
        const data = await res.json();
        if (data.success) {
          this.groupForm.name = '';
          await this.openGroupModal(this.selectedClass);
        } else { this.error = data.detail || '创建分组失败'; }
      } catch (e) { this.error = '请求失败'; }
      finally { this.loading = false; }
    },

    async deleteGroup(groupId) {
      await fetch(`/api/teacher/class/group/${groupId}`, { method: 'DELETE' });
      await this.openGroupModal(this.selectedClass);
    },

    async addStudentToGroup(groupId, studentId) {
      await fetch(`/api/teacher/class/group/${groupId}/student`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ student_id: studentId }),
      });
      await this.openGroupModal(this.selectedClass);
    },

    // ---- Student Learning Profile ----
    async openStudentProfile(student) {
      this.loading = true;
      try {
        const res = await fetch(`/api/teacher/student/${student.id}/profile`);
        const data = await res.json();
        this.studentProfile = data.profile || data;
        this.showProfileModal = true;
      } catch (e) {
        this.studentProfile = {
          username: student.username,
          display_name: student.display_name,
          completed_courses: 0,
          total_study_hours: 0,
          avg_score: 0,
          recent_activities: [],
        };
        this.showProfileModal = true;
      }
      finally { this.loading = false; }
    },

    // ---- Helpers ----
    formatDate(d) { return (d || '').slice(0, 10); },
  }));
});
