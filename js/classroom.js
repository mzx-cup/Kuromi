/**
 * Classroom Page JavaScript - ClassroomController
 * Handles multi-scene rendering (slide/quiz/exercise/interactive),
 * TTS audio sync, AI teacher chat, quiz grading, completion celebration
 */

(function() {
    'use strict';

    class ClassroomController {
        constructor() {
            this.courseData = null;
            this.currentIndex = 0;
            this.scenes = [];
            this.agentTeam = [];
            this.quizAnswers = {};
            this.visitedScenes = new Set();
            this.isPlaying = false;
            this.isChatLoading = false;
            this.chatHistory = [];
            this.sceneStartTime = Date.now();
            this.totalTimeSpent = 0;
            this.currentAudio = null;

            // Action system state
            this.actionQueue = [];
            this.currentAction = null;
            this.isProcessingActions = false;
            this.spotlightOverlay = null;
            this.laserOverlay = null;
            this.whiteboardVisible = false;

            // DOM refs
            this.courseTitle = document.getElementById('course-title')?.querySelector('span');
            this.outlineList = document.getElementById('outline-list');
            this.slideContainer = document.getElementById('slide-container');
            this.quizContainer = document.getElementById('quiz-container');
            this.exerciseContainer = document.getElementById('exercise-container');
            this.interactiveContainer = document.getElementById('interactive-container');
            this.teacherAvatar = document.getElementById('teacher-avatar');
            this.speechText = document.getElementById('speech-text');
            this.prevBtn = document.getElementById('prev-slide');
            this.nextBtn = document.getElementById('next-slide');
            this.currentSlideEl = document.getElementById('current-slide');
            this.totalSlidesEl = document.getElementById('total-slides');
            this.progressFill = document.getElementById('progress-fill');
            this.voiceBtn = document.getElementById('voice-btn');
            this.speechSync = document.getElementById('speech-sync');
            this.chatMessages = document.getElementById('chat-messages');
            this.chatInput = document.getElementById('chat-input');
            this.sendChat = document.getElementById('send-chat');
            this.chatAgentSelect = document.getElementById('chat-agent-select');
            this.sceneThumbnails = document.getElementById('scene-thumbnails');
            this.sceneSidebar = document.getElementById('scene-sidebar');
            this.completionOverlay = document.getElementById('completion-overlay');
            this.audioPlayer = document.getElementById('tts-audio-player');

            // Action overlays (create if not exist)
            this.actionOverlay = document.getElementById('action-overlay');
            if (!this.actionOverlay) {
                this.actionOverlay = document.createElement('div');
                this.actionOverlay.id = 'action-overlay';
                this.actionOverlay.style.cssText = 'position:fixed;top:0;left:0;width:100%;height:100%;pointer-events:none;z-index:9999;';
                document.body.appendChild(this.actionOverlay);
            }

            // Speech recognition for chat
            this.chatVoiceBtn = document.getElementById('chat-voice-btn');
            this.chatRecognition = null;
            this.chatIsRecording = false;
            this.chatInterimText = '';
        }

        // ---- Init ----

        async init() {
            this.loadData();
            if (!this.courseData) {
                alert('未找到课堂数据，正在返回首页...');
                window.location.href = '/index.html';
                return;
            }
            this.buildScenes();
            this.setupUI();
            this.bindEvents();
            this.renderSceneSidebar();
            this.renderScene(0);
            this.updateNav();
        }

        loadData() {
            const saved = sessionStorage.getItem('classroomData');
            if (saved) {
                try { this.courseData = JSON.parse(saved); } catch (e) {}
            }
            if (this.courseData) {
                this.agentTeam = this.courseData.agent_team || [];
                this.courseData.tts_audio_urls = this.courseData.tts_audio_urls || {};
            }
        }

        buildScenes() {
            const outlines = this.courseData.outlines || [];
            const slides = this.courseData.slides || [];
            const quizData = this.courseData.quiz_data || [];
            const exerciseData = this.courseData.exercise_data || [];

            this.scenes = outlines.map((outline, i) => ({
                id: outline.id || i + 1,
                title: outline.title || `场景 ${i + 1}`,
                type: outline.type || 'slide',
                description: outline.description || '',
                keyPoints: outline.key_points || [],
                slide: slides[i] || null,
                quiz: quizData.find(q => q.id === i + 1) || null,
                exercise: exerciseData.find(e => e.id === i + 1) || null,
                audioUrl: this.courseData.tts_audio_urls?.[String(i + 1)] || null,
                imageUrl: slides[i]?.content?.elements?.[0]?.image_url || null,
            }));
        }

        setupUI() {
            if (this.courseTitle && this.courseData.title) {
                this.courseTitle.textContent = this.courseData.title;
            }
            if (this.totalSlidesEl) {
                this.totalSlidesEl.textContent = this.scenes.length;
            }
            // Set teacher avatar - use image if available, otherwise gradient circle with initials
            if (this.courseData.teacher) {
                const teacher = this.courseData.teacher;
                if (teacher.avatar && teacher.avatar.startsWith('http')) {
                    this.teacherAvatar.innerHTML = `<img src="${teacher.avatar}" alt="教师" style="width:100%;height:100%;object-fit:cover;border-radius:50%;">`;
                } else if (teacher.name) {
                    // Generate initials from name
                    const initials = teacher.name.slice(0, 2).toUpperCase();
                    this.teacherAvatar.innerHTML = `<span style="font-size:1.5rem;font-weight:700;color:white;">${initials}</span>`;
                } else {
                    this.teacherAvatar.innerHTML = `<span style="font-size:1.5rem;">👩‍🏫</span>`;
                }
            }
            // Populate agent selector in chat
            if (this.chatAgentSelect && this.agentTeam.length > 0) {
                this.chatAgentSelect.innerHTML = this.agentTeam.map(a =>
                    `<option value="${a.id || ''}">${a.name || 'AI教师'} (${a.role || ''})</option>`
                ).join('');
            }
        }

        bindEvents() {
            document.getElementById('toggle-sidebar')?.addEventListener('click', () => {
                this.sceneSidebar.classList.toggle('collapsed');
            });
            this.prevBtn?.addEventListener('click', () => this.prevScene());
            this.nextBtn?.addEventListener('click', () => this.nextScene());
            this.voiceBtn?.addEventListener('click', () => this.toggleVoice());
            document.getElementById('replay-btn')?.addEventListener('click', () => this.replaySpeech());
            document.getElementById('pause-btn')?.addEventListener('click', () => this.pauseSpeech());
            this.sendChat?.addEventListener('click', () => this.sendMessage());
            this.chatInput?.addEventListener('keypress', e => { if (e.key === 'Enter') this.sendMessage(); });
            document.getElementById('exit-btn')?.addEventListener('click', () => this.showExitModal());
            document.getElementById('cancel-exit')?.addEventListener('click', () => this.hideExitModal());
            document.getElementById('confirm-exit')?.addEventListener('click', () => this.confirmExit());
            document.addEventListener('keydown', e => this.onKey(e));
            this.initChatVoiceInput();
        }

        onKey(e) {
            if (e.target === this.chatInput) return;
            switch (e.key) {
                case 'ArrowLeft': this.prevScene(); break;
                case 'ArrowRight': this.nextScene(); break;
                case ' ': e.preventDefault(); this.toggleVoice(); break;
            }
        }

        // ---- Scene Sidebar ----

        renderSceneSidebar() {
            if (!this.sceneThumbnails) return;
            const icons = { slide: '📖', quiz: '📝', exercise: '✏️', interactive: '🎮', pbl: '🔬', code: '💻' };
            this.sceneThumbnails.innerHTML = this.scenes.map((s, i) => `
                <div class="scene-thumb ${i === 0 ? 'active' : ''}" data-index="${i}" onclick="classroomController.goToScene(${i})">
                    <span class="scene-thumb-icon">${icons[s.type] || '📖'}</span>
                    <span class="scene-thumb-label">${s.title.slice(0, 8)}</span>
                    <span class="scene-thumb-badge">${s.type}</span>
                </div>
            `).join('');
        }

        updateSidebarActive(index) {
            this.sceneThumbnails?.querySelectorAll('.scene-thumb').forEach((t, i) =>
                t.classList.toggle('active', i === index));
        }

        // ---- Scene Rendering ----

        renderScene(index) {
            if (index < 0 || index >= this.scenes.length) return;
            this.visitedScenes.add(this.currentIndex);
            this.totalTimeSpent += Math.floor((Date.now() - this.sceneStartTime) / 1000);
            this.sceneStartTime = Date.now();
            this.currentIndex = index;

            const scene = this.scenes[index];
            this.hideAllSceneContainers();

            switch (scene.type) {
                case 'quiz': this.renderQuizScene(scene); break;
                case 'exercise': this.renderExerciseScene(scene); break;
                case 'interactive': case 'pbl': this.renderInteractiveScene(scene); break;
                default: this.renderSlideScene(scene);
            }

            this.updateTeacherSpeech(scene);
            this.updateSidebarActive(index);
            this.updateNav();
            if (this.isPlaying) this.playSceneAudio(scene);
            this.checkCompletion();
        }

        hideAllSceneContainers() {
            [this.slideContainer, this.quizContainer, this.exerciseContainer, this.interactiveContainer]
                .forEach(el => { if (el) el.style.display = 'none'; });
            const quizSubmit = document.getElementById('quiz-submit-btn');
            const quizResult = document.getElementById('quiz-result');
            if (quizSubmit) quizSubmit.style.display = 'none';
            if (quizResult) quizResult.style.display = 'none';
        }

        renderSlideScene(scene) {
            if (!this.slideContainer) return;
            this.slideContainer.style.display = 'block';
            const slide = scene.slide;
            if (!slide) {
                this.slideContainer.innerHTML = `<div class="slide-content"><h1>${scene.title}</h1><p>${scene.description}</p></div>`;
                return;
            }

            // Apply slide background
            if (slide.background && this.slideContainer) {
                const bg = slide.background;
                if (bg.type === 'gradient' && bg.gradient?.colors) {
                    const colors = bg.gradient.colors.map(c => typeof c === 'string' ? c : c.color).join(', ');
                    const angle = bg.gradient.rotate || 135;
                    this.slideContainer.style.background = `linear-gradient(${angle}deg, ${colors})`;
                } else if (bg.type === 'solid' && bg.color) {
                    this.slideContainer.style.backgroundColor = bg.color;
                }
            }

            let html = `<div class="slide-content slide-enter"><h1 class="slide-title animate-in">${slide.title || scene.title}</h1><div class="slide-body">`;
            if (slide.content?.elements) {
                slide.content.elements.forEach((el, idx) => {
                    const elemId = el.id ? `id="elem-${el.id}"` : '';
                    const animDelay = `animation-delay:${idx * 0.1}s`;
                    if (el.type === 'text') {
                        const style = this._buildElementStyle(el);
                        const textStyle = el.default_font_name ? `font-family:${el.default_font_name},sans-serif;` : '';
                        html += `<div class="slide-text animate-in" ${elemId} style="${style};${textStyle}${animDelay}">${(el.content || '').replace(/\n/g, '<br>')}</div>`;
                    } else if (el.type === 'code') {
                        const style = this._buildElementStyle(el);
                        html += `<pre class="slide-code animate-in" ${elemId} style="${style};${animDelay}"><code>${this.escapeHtml(el.content || '')}</code></pre>`;
                    } else if (el.type === 'image' && el.image_url) {
                        const style = this._buildElementStyle(el);
                        html += `<img class="slide-image animate-in" ${elemId} src="${el.image_url}" alt="" style="${style};${animDelay}">`;
                    } else if (el.type === 'shape') {
                        const style = this._buildShapeStyle(el);
                        html += `<div class="slide-shape animate-in" ${elemId} style="${style};${animDelay}">${this._renderShapeContent(el)}</div>`;
                    } else if (el.type === 'chart' && el.chart_type) {
                        html += `<div class="slide-chart animate-in" ${elemId} data-chart-type="${el.chart_type}" style="height:200px;${animDelay}">${this._renderChartPlaceholder(el)}</div>`;
                    } else if (el.type === 'latex' && el.latex) {
                        html += `<div class="slide-latex animate-in" ${elemId} style="font-size:18px;${animDelay}">${this._renderLatex(el.latex)}</div>`;
                    } else if (el.type === 'table' && el.table_data) {
                        html += `<div class="slide-table animate-in" ${elemId} style="${animDelay}">${this._renderTable(el.table_data)}</div>`;
                    } else if (el.type === 'line' && el.points) {
                        html += `<svg class="slide-line animate-in" ${elemId} style="${animDelay}" ${this._buildLineStyle(el)}><line ${this._buildLineAttrs(el)}/></svg>`;
                    }
                });
            }
            if (scene.imageUrl && !html.includes('slide-image')) {
                html += `<img class="slide-image animate-in" src="${scene.imageUrl}" alt="" style="max-width:60%;margin:1rem auto;display:block;">`;
            }
            html += '</div></div>';
            this.slideContainer.innerHTML = html;

            // Load scene actions and process them
            this.loadSceneActions(scene);
        }

        _renderShapeContent(el) {
            // Render SVG shape if path is provided
            if (el.path && el.view_box) {
                const vb = el.view_box;
                const vbStr = Array.isArray(vb) ? vb.join(' ') : vb;
                return `<svg viewBox="${vbStr}" style="width:100%;height:100%;overflow:visible;"><path d="${el.path}" fill="${el.fill || '#6366f1'}"/></svg>`;
            }
            // Fallback to CSS shapes
            const shapeName = (el.shape_name || 'rectangle').toLowerCase();
            if (shapeName === 'circle') return '';
            if (shapeName === 'triangle') return '';
            return '';
        }

        _renderChartPlaceholder(el) {
            const chartType = el.chart_type || 'bar';
            const chartData = el.chart_data || { labels: ['A', 'B', 'C'], series: [[100, 200, 150]] };
            const colors = ['#6366f1', '#8b5cf6', '#a78bfa', '#c4b5fd'];
            let barsHtml = '';
            if (chartData.series && chartData.series[0]) {
                const max = Math.max(...chartData.series[0]);
                chartData.series[0].forEach((val, i) => {
                    const pct = (val / max) * 100;
                    const color = colors[i % colors.length];
                    barsHtml += `<div style="flex:1;display:flex;flex-direction:column;align-items:center;gap:4px;">
                        <div style="width:100%;max-width:40px;height:${pct}%;background:${color};border-radius:4px 4px 0 0;"></div>
                        <span style="font-size:10px;color:#94a3b8;">${chartData.labels?.[i] || ''}</span>
                    </div>`;
                });
            }
            return `<div style="display:flex;align-items:flex-end;justify-content:center;gap:16px;height:100%;padding:16px;">${barsHtml}</div>`;
        }

        _renderLatex(latex) {
            // Simple LaTeX rendering - in production would use KaTeX or MathJax
            return `<span style="font-family:'Cambria Math','STIX Two Math',serif;font-size:1.2em;color:#e2e8f0;background:rgba(99,102,241,0.1);padding:8px 16px;border-radius:8px;display:inline-block;">${this.escapeHtml(latex)}</span>`;
        }

        _renderTable(tableData) {
            if (!tableData || !tableData.rows) return '<table class="data-table"><tr><td>No data</td></tr></table>';
            let html = '<table class="data-table" style="width:100%;border-collapse:collapse;">';
            tableData.rows.forEach((row, ri) => {
                html += '<tr>';
                row.forEach((cell, ci) => {
                    const isHeader = ri === 0;
                    html += `<td style="padding:12px;border:1px solid rgba(255,255,255,0.1);${isHeader ? 'background:rgba(99,102,241,0.2);font-weight:600;' : ''}">${this.escapeHtml(cell)}</td>`;
                });
                html += '</tr>';
            });
            html += '</table>';
            return html;
        }

        _buildLineStyle(el) {
            const styles = [];
            if (el.width) styles.push(`width:${el.width * 0.1}px`);
            if (el.height) styles.push(`height:${el.height * 0.1}px`);
            return styles.join(';');
        }

        _buildLineAttrs(el) {
            const attrs = [];
            if (el.start) attrs.push(`x1="${el.start[0] * 0.1}" y1="${el.start[1] * 0.1}"`);
            if (el.end) attrs.push(`x2="${el.end[0] * 0.1}" y2="${el.end[1] * 0.1}"`);
            if (el.color) attrs.push(`stroke="${el.color}"`);
            if (el.line_width || el.stroke_width) attrs.push(`stroke-width="${el.line_width || el.stroke_width || 2}"`);
            attrs.push(`vector-effect="non-scaling-stroke"`);
            return attrs.join(' ');
        }

        _buildElementStyle(el) {
            const styles = [];
            // Position and size (scaled for CSS)
            if (el.left !== undefined) styles.push(`left:${el.left * 0.1}px`);
            if (el.top !== undefined) styles.push(`top:${el.top * 0.1}px`);
            if (el.width !== undefined) styles.push(`width:${el.width * 0.1}px`);
            if (el.height !== undefined) styles.push(`height:${el.height * 0.1}px`);
            if (el.min_width) styles.push(`min-width:${el.min_width * 0.1}px`);
            if (el.min_height) styles.push(`min-height:${el.min_height * 0.1}px`);

            // Background fill (solid color)
            if (el.fill) styles.push(`background:${el.fill}`);

            // Gradient fill
            if (el.gradient && el.gradient.colors) {
                const gradType = el.gradient.type === 'radial' ? 'radial-gradient' : 'linear-gradient';
                const angle = el.gradient.rotate || 0;
                const colors = el.gradient.colors.map(c => {
                    if (typeof c === 'string') return c;
                    return `${c.color} ${c.pos !== undefined ? c.pos + '%' : ''}`;
                }).join(', ');
                if (gradType === 'linear-gradient') {
                    styles.push(`background:${gradType}(${angle}deg, ${colors})`);
                } else {
                    styles.push(`background:${gradType}(circle at center, ${colors})`);
                }
            }

            // Text styling
            if (el.default_color) styles.push(`color:${el.default_color}`);
            if (el.default_font_name) styles.push(`font-family:${el.default_font_name}`);
            if (el.font_size) styles.push(`font-size:${el.font_size * 0.1}px`);
            if (el.font_weight) styles.push(`font-weight:${el.font_weight}`);
            if (el.line_height) styles.push(`line-height:${el.line_height}`);
            if (el.word_space) styles.push(`letter-spacing:${el.word_space}px`);
            if (el.text_align) styles.push(`text-align:${el.text_align}`);

            // Opacity
            if (el.opacity !== undefined && el.opacity < 1) styles.push(`opacity:${el.opacity}`);

            // Rotation
            if (el.rotate) styles.push(`transform:rotate(${el.rotate}deg)`);

            // Shadow - OpenMAIC style shadow
            if (el.shadow) {
                const { h = 0, v = 0, blur = 0, color = 'rgba(0,0,0,0.3)' } = el.shadow;
                styles.push(`filter:drop-shadow(${h * 0.1}px ${v * 0.1}px ${blur * 0.1}px ${color})`);
            }

            // Outline/border
            if (el.outline) {
                const ow = el.outline.width || 1;
                const oc = el.outline.color || '#6366f1';
                const os = el.outline.style || 'solid';
                if (os === 'dashed') {
                    styles.push(`border:${ow}px dashed ${oc}`);
                } else if (os === 'dotted') {
                    styles.push(`border:${ow}px dotted ${oc}`);
                } else {
                    styles.push(`border:${ow}px solid ${oc}`);
                }
            }

            // Border radius
            if (el.border_radius !== undefined) styles.push(`border-radius:${el.border_radius * 0.1}px`);

            // Vertical text
            if (el.vertical) styles.push(`writing-mode:vertical-rl`);

            // Paragraph spacing
            if (el.paragraph_space !== undefined) {
                styles.push(`margin-bottom:${el.paragraph_space * 0.1}px`);
            }

            return styles.join(';');
        }

        _buildShapeStyle(el) {
            const styles = [];
            // Position
            if (el.left !== undefined) styles.push(`position:absolute;left:${el.left * 0.1}px`);
            if (el.top !== undefined) styles.push(`top:${el.top * 0.1}px`);
            // Size
            if (el.width !== undefined) styles.push(`width:${el.width * 0.1}px`);
            if (el.height !== undefined) styles.push(`height:${el.height * 0.1}px`);
            // Opacity
            if (el.opacity !== undefined && el.opacity < 1) styles.push(`opacity:${el.opacity}`);
            // Rotation
            if (el.rotate) styles.push(`transform:rotate(${el.rotate}deg)`);
            // Shadow
            if (el.shadow) {
                const { h = 0, v = 0, blur = 0, color = 'rgba(0,0,0,0.3)' } = el.shadow;
                styles.push(`filter:drop-shadow(${h * 0.1}px ${v * 0.1}px ${blur * 0.1}px ${color})`);
            }
            // For CSS-only shapes (no SVG path)
            const shapeName = (el.shape_name || 'rectangle').toLowerCase();
            if (shapeName === 'circle' || shapeName === 'ellipse') {
                styles.push('border-radius:50%');
            } else if (shapeName === 'triangle') {
                styles.push('width:0;height:0;border-left:50px solid transparent;border-right:50px solid transparent;border-bottom:100px solid #6366f1;');
            }
            return styles.join(';');
        }

        loadSceneActions(scene) {
            const sceneActions = this.courseData.scene_actions || [];
            const actionData = sceneActions.find(a => a.scene_id === scene.id || a.scene_id === scene.slide?.id);
            if (actionData?.actions?.length > 0) {
                this.actionQueue = [...actionData.actions];
                this.processActionQueue();
            }
        }

        async processActionQueue() {
            if (this.isProcessingActions || this.actionQueue.length === 0) return;
            this.isProcessingActions = true;

            while (this.actionQueue.length > 0) {
                const action = this.actionQueue.shift();
                await this.processAction(action);
            }

            this.isProcessingActions = false;
        }

        async processAction(action) {
            const delay = action.delay || 0;
            const duration = action.duration || 1;

            if (delay > 0) {
                await this._sleep(delay * 1000);
            }

            switch (action.type) {
                case 'spotlight':
                    this.renderSpotlight(action.element_id);
                    await this._sleep(duration * 1000);
                    this.clearSpotlight();
                    break;

                case 'laser':
                    this.renderLaser(action.element_id, action.color || '#ff6b6b');
                    await this._sleep(duration * 1000);
                    this.clearLaser();
                    break;

                case 'speech':
                    await this.playSpeechAction(action.text);
                    break;

                case 'wb_open':
                    this.showWhiteboard();
                    break;

                case 'wb_close':
                    this.hideWhiteboard();
                    break;

                case 'wb_draw_text':
                    this.drawOnWhiteboard(action.wb_content);
                    break;

                case 'wb_draw_shape':
                    this.drawShapeOnWhiteboard(action.wb_shape || 'rectangle');
                    break;

                default:
                    console.warn('Unknown action type:', action.type);
            }
        }

        renderSpotlight(elementId) {
            this.clearSpotlight();
            const elem = elementId ? document.getElementById(`elem-${elementId}`) : null;
            if (!elem || !this.actionOverlay) return;

            const rect = elem.getBoundingClientRect();
            const overlay = document.createElement('div');
            overlay.id = 'spotlight-overlay';
            overlay.style.cssText = `
                position:fixed;
                top:0;left:0;width:100%;height:100%;
                background:rgba(0,0,0,0.6);
                z-index:9998;
                pointer-events:none;
            `;

            // Create a "hole" in the overlay for the target element
            const hole = document.createElement('div');
            hole.style.cssText = `
                position:absolute;
                left:${rect.left - 10}px;
                top:${rect.top - 10}px;
                width:${rect.width + 20}px;
                height:${rect.height + 20}px;
                box-shadow:0 0 0 9999px rgba(0,0,0,0.6);
                border-radius:8px;
            `;
            overlay.appendChild(hole);
            this.actionOverlay.appendChild(overlay);
            this.spotlightOverlay = overlay;

            // Highlight the element itself
            elem.style.transition = 'filter 0.3s, transform 0.3s';
            elem.style.filter = 'brightness(1.2)';
            elem.style.transform = 'scale(1.02)';
        }

        clearSpotlight() {
            if (this.spotlightOverlay) {
                this.spotlightOverlay.remove();
                this.spotlightOverlay = null;
            }
            // Restore all elements
            document.querySelectorAll('.slide-text, .slide-code, .slide-image, .slide-shape, .slide-latex').forEach(el => {
                el.style.filter = '';
                el.style.transform = '';
            });
        }

        renderLaser(elementId, color) {
            this.clearLaser();
            const elem = elementId ? document.getElementById(`elem-${elementId}`) : null;
            if (!elem || !this.actionOverlay) return;

            const rect = elem.getBoundingClientRect();
            const laser = document.createElement('div');
            laser.id = 'laser-overlay';
            laser.innerHTML = `
                <svg width="${window.innerWidth}" height="${window.innerHeight}" style="position:fixed;top:0;left:0;pointer-events:none;z-index:9999;">
                    <circle cx="${rect.left + rect.width / 2}" cy="${rect.top + rect.height / 2}" r="8" fill="${color}" opacity="0.8">
                        <animate attributeName="r" values="8;12;8" dur="0.5s" repeatCount="indefinite"/>
                        <animate attributeName="opacity" values="0.8;0.4;0.8" dur="0.5s" repeatCount="indefinite"/>
                    </circle>
                    <circle cx="${rect.left + rect.width / 2}" cy="${rect.top + rect.height / 2}" r="20" fill="none" stroke="${color}" stroke-width="2" opacity="0.5">
                        <animate attributeName="r" values="20;30;20" dur="0.8s" repeatCount="indefinite"/>
                        <animate attributeName="opacity" values="0.5;0.2;0.5" dur="0.8s" repeatCount="indefinite"/>
                    </circle>
                </svg>
            `;
            this.actionOverlay.appendChild(laser);
            this.laserOverlay = laser;
        }

        clearLaser() {
            if (this.laserOverlay) {
                this.laserOverlay.remove();
                this.laserOverlay = null;
            }
        }

        async playSpeechAction(text) {
            if (!text) return;
            this.speechText.textContent = text;

            // Show speaking indicator
            if (this.speechSync) this.speechSync.style.display = 'flex';

            // Try MiniMax TTS API first
            try {
                const voiceId = this.courseData.teacher?.voice_id || 0;
                const response = await fetch('/api/socratic/tts', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ text, voice_id: voiceId })
                });
                const data = await response.json();
                if (data.success && data.audio_url) {
                    // Play generated audio
                    if (this.audioPlayer) {
                        this.audioPlayer.src = data.audio_url;
                        await this.audioPlayer.play().catch(() => this._speakText(text));
                        this.audioPlayer.onended = () => {
                            if (this.speechSync) this.speechSync.style.display = 'none';
                        };
                    } else {
                        await this._speakText(text);
                    }
                } else {
                    await this._speakText(text);
                }
            } catch (e) {
                // Fallback to browser TTS
                await this._speakText(text);
            }
        }

        _speakText(text) {
            return new Promise((resolve) => {
                if (!window.speechSynthesis) {
                    resolve();
                    return;
                }
                const utterance = new SpeechSynthesisUtterance(text);
                utterance.lang = 'zh-CN';
                utterance.rate = 1.0;
                utterance.onend = () => resolve();
                utterance.onerror = () => resolve();
                window.speechSynthesis.speak(utterance);
            });
        }

        showWhiteboard() {
            let wb = document.getElementById('whiteboard-overlay');
            if (!wb) {
                wb = document.createElement('div');
                wb.id = 'whiteboard-overlay';
                wb.style.cssText = `
                    position:fixed;top:0;left:0;width:100%;height:100%;
                    background:rgba(255,255,255,0.95);z-index:10000;
                    display:flex;align-items:center;justify-content:center;
                `;
                wb.innerHTML = `
                    <div style="width:90%;max-width:800px;height:80%;background:#fff;border-radius:16px;box-shadow:0 20px 60px rgba(0,0,0,0.3);padding:24px;position:relative;">
                        <button onclick="classroomController.hideWhiteboard()" style="position:absolute;top:12px;right:12px;background:#ff6b6b;color:#fff;border:none;border-radius:50%;width:36px;height:36px;cursor:pointer;font-size:18px;">×</button>
                        <canvas id="whiteboard-canvas" width="700" height="450" style="border:2px solid #e0e0e0;border-radius:8px;cursor:crosshair;"></canvas>
                    </div>
                `;
                document.body.appendChild(wb);

                // Initialize canvas drawing
                const canvas = document.getElementById('whiteboard-canvas');
                if (canvas) {
                    const ctx = canvas.getContext('2d');
                    ctx.strokeStyle = '#6366f1';
                    ctx.lineWidth = 3;
                    ctx.lineCap = 'round';

                    let drawing = false;
                    let lastX = 0, lastY = 0;

                    canvas.addEventListener('mousedown', (e) => {
                        drawing = true;
                        const rect = canvas.getBoundingClientRect();
                        lastX = e.clientX - rect.left;
                        lastY = e.clientY - rect.top;
                    });
                    canvas.addEventListener('mousemove', (e) => {
                        if (!drawing) return;
                        const rect = canvas.getBoundingClientRect();
                        const x = e.clientX - rect.left;
                        const y = e.clientY - rect.top;
                        ctx.beginPath();
                        ctx.moveTo(lastX, lastY);
                        ctx.lineTo(x, y);
                        ctx.stroke();
                        lastX = x; lastY = y;
                    });
                    canvas.addEventListener('mouseup', () => drawing = false);
                    canvas.addEventListener('mouseleave', () => drawing = false);
                }
            }
            wb.style.display = 'flex';
            this.whiteboardVisible = true;
        }

        hideWhiteboard() {
            const wb = document.getElementById('whiteboard-overlay');
            if (wb) wb.style.display = 'none';
            this.whiteboardVisible = false;
        }

        drawOnWhiteboard(content) {
            const canvas = document.getElementById('whiteboard-canvas');
            if (!canvas) return;
            const ctx = canvas.getContext('2d');
            ctx.font = '20px Microsoft YaHei';
            ctx.fillStyle = '#333';
            ctx.fillText(content, 50, 50);
        }

        drawShapeOnWhiteboard(shapeType) {
            const canvas = document.getElementById('whiteboard-canvas');
            if (!canvas) return;
            const ctx = canvas.getContext('2d');
            ctx.strokeStyle = '#8b5cf6';
            ctx.lineWidth = 3;

            const cx = 350, cy = 225, r = 60;
            ctx.beginPath();
            if (shapeType === 'circle') {
                ctx.arc(cx, cy, r, 0, Math.PI * 2);
            } else if (shapeType === 'triangle') {
                ctx.moveTo(cx, cy - r);
                ctx.lineTo(cx - r, cy + r);
                ctx.lineTo(cx + r, cy + r);
                ctx.closePath();
            } else {
                ctx.rect(cx - r, cy - r, r * 2, r * 2);
            }
            ctx.stroke();
        }

        _sleep(ms) {
            return new Promise(resolve => setTimeout(resolve, ms));
        }

        renderQuizScene(scene) {
            if (!this.quizContainer) return;
            this.quizContainer.style.display = 'block';
            const quiz = scene.quiz;
            const header = document.getElementById('quiz-header');
            const questions = document.getElementById('quiz-questions');
            const submitBtn = document.getElementById('quiz-submit-btn');
            const result = document.getElementById('quiz-result');

            if (header) header.innerHTML = `<i class="fas fa-pencil-alt"></i> ${quiz?.title || scene.title}`;
            if (result) result.style.display = 'none';

            if (!quiz?.questions?.length) {
                if (questions) questions.innerHTML = '<p class="text-muted">此测验暂无题目</p>';
                return;
            }

            if (questions) {
                questions.innerHTML = quiz.questions.map((q, qi) => `
                    <div class="quiz-question">
                        <div class="quiz-question-text">${qi + 1}. ${q.question || ''}</div>
                        <div class="quiz-options">
                            ${(q.options || []).map((opt, oi) => `
                                <label class="quiz-option" data-q="${qi}" data-opt="${oi}">
                                    <input type="radio" name="q_${qi}" value="${oi}">
                                    <span>${String.fromCharCode(65 + oi)}. ${opt.label || opt}</span>
                                </label>
                            `).join('')}
                        </div>
                    </div>
                `).join('');
            }
            if (submitBtn) {
                submitBtn.style.display = 'block';
                submitBtn.textContent = '提交答案';
                submitBtn.onclick = () => this.submitQuiz(scene);
            }
        }

        renderExerciseScene(scene) {
            if (!this.exerciseContainer) return;
            this.exerciseContainer.style.display = 'block';
            const data = scene.exercise;
            const content = document.getElementById('exercise-content');
            const hints = document.getElementById('exercise-hints');
            const answer = document.getElementById('exercise-answer');
            const submitBtn = document.getElementById('exercise-submit-btn');

            if (content) {
                const exercises = data?.exercises || [];
                content.innerHTML = exercises.length > 0
                    ? exercises.map((ex, i) => `<div class="exercise-item"><h4>练习 ${i+1}</h4><p>${ex.instruction || ''}</p></div>`).join('')
                    : `<h3>${scene.title}</h3><p>${scene.description}</p>`;
            }
            if (hints && data?.exercises?.[0]?.hints) {
                hints.innerHTML = '<strong>提示：</strong>' + data.exercises[0].hints.map(h => `<span class="hint-badge">${h}</span>`).join('');
                hints.style.display = 'block';
            }
            if (answer) answer.value = '';
            if (submitBtn) submitBtn.onclick = () => {
                const ans = answer?.value.trim();
                if (ans) {
                    this.addChatMessage('user', `练习答案：${ans}`);
                    this.sendExerciseAnswer(scene, ans);
                }
            };
        }

        renderInteractiveScene(scene) {
            if (!this.interactiveContainer) return;
            this.interactiveContainer.style.display = 'block';
            const iframe = document.getElementById('interactive-iframe');

            // Check for enhanced interactive data with widget_type
            const interactiveData = this.courseData.interactive_data?.find(i => i.id === scene.id);
            const widgetType = interactiveData?.widget_type;
            const htmlContent = interactiveData?.html_content || interactiveData?.html;

            if (iframe) {
                if (htmlContent) {
                    // Render actual interactive HTML content
                    iframe.srcdoc = htmlContent;
                } else if (widgetType) {
                    // Render placeholder with widget type
                    iframe.srcdoc = `<html><body style="font-family:sans-serif;display:flex;align-items:center;justify-content:center;height:100vh;background:#1a1a2e;color:#e0e7ff;margin:0;">
                        <div style="text-align:center;padding:2rem;">
                            <div style="font-size:4rem;margin-bottom:1rem;">${widgetType === 'simulation' ? '🔬' : widgetType === 'diagram' ? '📊' : widgetType === 'code' ? '💻' : widgetType === 'game' ? '🎮' : widgetType === 'visualization3d' ? '🌐' : '🎯'}</div>
                            <h2>${scene.title}</h2>
                            <p style="color:#a0aec0;">${scene.description || '交互式学习内容'}</p>
                            <p style="color:#6366f1;font-size:0.9rem;margin-top:1rem;">Widget类型: ${widgetType}</p>
                        </div></body></html>`;
                } else {
                    // Basic placeholder
                    iframe.srcdoc = `<html><body style="font-family:sans-serif;display:flex;align-items:center;justify-content:center;height:100vh;background:#1a1a2e;color:#e0e7ff;">
                        <div style="text-align:center;"><h2>${scene.title}</h2><p>${scene.description}</p></div></body></html>`;
                }
            }
        }

        updateTeacherSpeech(scene) {
            if (!this.speechText) return;
            const speech = scene.slide?.speech || scene.quiz?.speech || scene.description || '';
            this.speechText.textContent = speech || `现在讲解：${scene.title}`;

            // Update avatar if agent team has different teachers per scene
            const teacherIdx = scene.teacher_index || 0;
            const agent = this.agentTeam[teacherIdx];
            if (agent && this.teacherAvatar) {
                if (agent.avatar && agent.avatar.startsWith('http')) {
                    this.teacherAvatar.innerHTML = `<img src="${agent.avatar}" alt="${agent.name}" style="width:100%;height:100%;object-fit:cover;border-radius:50%;">`;
                } else if (agent.name) {
                    const initials = agent.name.slice(0, 2).toUpperCase();
                    this.teacherAvatar.innerHTML = `<span style="font-size:1.5rem;font-weight:700;color:white;">${initials}</span>`;
                } else {
                    this.teacherAvatar.innerHTML = `<span style="font-size:1.5rem;">👩‍🏫</span>`;
                }
            }
        }

        // ---- Audio / TTS ----

        playSceneAudio(scene) {
            this.stopAudio();
            const url = scene.audioUrl
                || scene.slide?.content?.elements?.find(el => el.audio_url)?.audio_url
                || scene.slide?.content?.elements?.[0]?.audio_url;

            if (url && this.audioPlayer) {
                this.speechSync.style.display = 'flex';
                this.audioPlayer.src = url;
                this.audioPlayer.play().catch(() => this.fallbackTTS(scene));
                this.audioPlayer.onended = () => {
                    this.speechSync.style.display = 'none';
                    if (this.isPlaying && this.currentIndex < this.scenes.length - 1) {
                        setTimeout(() => this.nextScene(), 800);
                    }
                };
            } else if (scene.slide?.speech) {
                this.fallbackTTS(scene);
            }
        }

        fallbackTTS(scene) {
            const text = scene.slide?.speech || scene.quiz?.speech || '';
            if (!text || !window.speechSynthesis) return;
            const utterance = new SpeechSynthesisUtterance(text);
            utterance.lang = 'zh-CN';
            utterance.rate = 1.0;
            this.speechSync.style.display = 'flex';
            utterance.onend = () => {
                this.speechSync.style.display = 'none';
                if (this.isPlaying && this.currentIndex < this.scenes.length - 1) {
                    setTimeout(() => this.nextScene(), 800);
                }
            };
            window.speechSynthesis.speak(utterance);
        }

        toggleVoice() {
            this.isPlaying = !this.isPlaying;
            this.voiceBtn?.classList.toggle('playing', this.isPlaying);
            const icon = this.voiceBtn?.querySelector('i');
            if (icon) icon.className = this.isPlaying ? 'fas fa-volume-mute' : 'fas fa-volume-up';
            if (this.isPlaying) this.playSceneAudio(this.scenes[this.currentIndex]);
            else this.stopAudio();
        }

        stopAudio() {
            if (this.audioPlayer) { this.audioPlayer.pause(); this.audioPlayer.src = ''; }
            if (window.speechSynthesis) window.speechSynthesis.cancel();
            if (this.speechSync) this.speechSync.style.display = 'none';
        }

        replaySpeech() { this.playSceneAudio(this.scenes[this.currentIndex]); }
        pauseSpeech() {
            if (this.audioPlayer?.paused === false) this.audioPlayer.pause();
            else this.audioPlayer?.play().catch(() => {});
            if (window.speechSynthesis.paused) window.speechSynthesis.resume();
            else if (window.speechSynthesis.speaking) window.speechSynthesis.pause();
        }

        // ---- Quiz ----

        async submitQuiz(scene) {
            const quiz = scene.quiz;
            if (!quiz?.questions) return;
            const answers = [];
            quiz.questions.forEach((q, qi) => {
                const sel = document.querySelector(`input[name="q_${qi}"]:checked`);
                answers.push({ question_index: qi, selected_option: sel ? parseInt(sel.value) : -1 });
            });

            // Highlight correct/wrong locally first
            quiz.questions.forEach((q, qi) => {
                const options = document.querySelectorAll(`.quiz-option[data-q="${qi}"]`);
                options.forEach((opt, oi) => {
                    opt.classList.remove('correct', 'wrong');
                    if (oi === q.correct_answer) opt.classList.add('correct');
                });
                const sel = document.querySelector(`input[name="q_${qi}"]:checked`);
                if (sel && parseInt(sel.value) !== q.correct_answer) {
                    options[parseInt(sel.value)]?.classList.add('wrong');
                }
            });

            // Try server grading
            let result;
            try {
                const resp = await fetch('/api/v2/course/quiz/grade', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ questions: quiz.questions, student_answers: answers })
                });
                result = await resp.json();
            } catch (e) {
                // Local grading fallback
                const correct = answers.filter((a, i) => a.selected_option === (quiz.questions[i]?.correct_answer || 0)).length;
                result = {
                    total: Math.round(correct / quiz.questions.length * 100),
                    passed: correct / quiz.questions.length >= 0.6,
                    correct_count: correct,
                    total_count: quiz.questions.length,
                };
            }

            const resultEl = document.getElementById('quiz-result');
            const submitBtn = document.getElementById('quiz-submit-btn');
            if (resultEl) {
                resultEl.style.display = 'block';
                resultEl.innerHTML = `
                    <div class="quiz-score ${result.passed ? 'passed' : 'failed'}">${result.total}%</div>
                    <div class="quiz-score-label">答对 ${result.correct_count}/${result.total_count} 题 ${result.passed ? '通过' : '未通过'}</div>
                `;
            }
            if (submitBtn) {
                submitBtn.textContent = result.passed ? '继续学习' : '重新答题';
                submitBtn.onclick = result.passed ? () => this.nextScene() : () => this.renderScene(this.currentIndex);
            }

            this.quizAnswers[scene.id] = answers;
            this.checkCompletion();
        }

        // ---- Exercise ----

        async sendExerciseAnswer(scene, answer) {
            try {
                const resp = await fetch('/api/v2/course/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        student_id: this.courseData.metadata?.student_id || '',
                        course_id: this.courseData.courseId || '',
                        slide_index: this.currentIndex,
                        slide_title: scene.title,
                        slide_content: JSON.stringify(scene.exercise || {}),
                        speech: scene.description || '',
                        user_input: `我的练习答案是：${answer}。请评估并给出反馈。`,
                        history: []
                    })
                });
                const data = await resp.json();
                this.addChatMessage('teacher', data.content || '收到你的答案，做得不错！');
            } catch (e) {
                this.addChatMessage('teacher', '收到你的答案！请继续下一场景。');
            }
        }

        // ---- Chat ----

        async sendMessage() {
            const text = this.chatInput?.value.trim();
            if (!text || this.isChatLoading) return;

            this.addChatMessage('user', text);
            if (this.chatInput) this.chatInput.value = '';

            const loadingDiv = document.createElement('div');
            loadingDiv.className = 'message teacher';
            loadingDiv.id = 'chat-loading';
            const teacher = this.courseData?.teacher;
            let teacherAvatarHtml;
            if (teacher?.avatar && teacher.avatar.startsWith('http')) {
                teacherAvatarHtml = `<img src="${teacher.avatar}" alt="教师" style="width:100%;height:100%;object-fit:cover;border-radius:50%;">`;
            } else if (teacher?.name) {
                const initials = teacher.name.slice(0, 2).toUpperCase();
                teacherAvatarHtml = `<span style="font-size:0.8rem;font-weight:700;color:white;">${initials}</span>`;
            } else {
                teacherAvatarHtml = `<i class="fas fa-chalkboard-teacher" style="color:white;"></i>`;
            }
            loadingDiv.innerHTML = `<div class="message-avatar">${teacherAvatarHtml}</div><div class="message-bubble"><p>思考中...</p></div>`;
            this.chatMessages?.appendChild(loadingDiv);
            this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
            this.isChatLoading = true;

            const scene = this.scenes[this.currentIndex];
            const agentId = this.chatAgentSelect?.value || '';

            try {
                const resp = await fetch('/api/v2/course/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        student_id: this.courseData.metadata?.student_id || '',
                        course_id: this.courseData.courseId || '',
                        slide_index: this.currentIndex,
                        slide_title: scene?.title || '',
                        slide_content: scene?.slide?.content?.elements?.map(e => e.content).join('\n') || '',
                        speech: scene?.slide?.speech || scene?.quiz?.speech || '',
                        user_input: text,
                        history: this.chatHistory.slice(-10),
                        agent_role: agentId ? (this.agentTeam.find(a => a.id === agentId)?.role || 'AI助教') : 'AI助教',
                    })
                });
                const data = await resp.json();
                document.getElementById('chat-loading')?.remove();
                this.addChatMessage('teacher', data.content || '抱歉，暂时无法回答。');
                if (data.success) {
                    this.chatHistory.push({ role: 'user', content: text });
                    this.chatHistory.push({ role: 'assistant', content: data.content });
                }
            } catch (e) {
                document.getElementById('chat-loading')?.remove();
                this.addChatMessage('teacher', '网络异常，请稍后重试。');
            } finally {
                this.isChatLoading = false;
            }
        }

        addChatMessage(type, text) {
            if (!this.chatMessages) return;
            const div = document.createElement('div');
            div.className = `message ${type}`;

            let avatarHtml;
            if (type === 'teacher') {
                const teacher = this.courseData?.teacher;
                if (teacher?.avatar && teacher.avatar.startsWith('http')) {
                    avatarHtml = `<img src="${teacher.avatar}" alt="教师" style="width:100%;height:100%;object-fit:cover;border-radius:50%;">`;
                } else if (teacher?.name) {
                    const initials = teacher.name.slice(0, 2).toUpperCase();
                    avatarHtml = `<span style="font-size:0.8rem;font-weight:700;color:white;">${initials}</span>`;
                } else {
                    avatarHtml = `<i class="fas fa-chalkboard-teacher" style="color:white;"></i>`;
                }
            } else {
                avatarHtml = `<i class="fas fa-user" style="color:var(--accent-light);"></i>`;
            }

            div.innerHTML = `<div class="message-avatar">${avatarHtml}</div><div class="message-bubble"><p>${this.escapeHtml(text)}</p></div>`;
            this.chatMessages.appendChild(div);
            this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
        }

        // ---- Navigation ----

        goToScene(index) { this.renderScene(index); }
        prevScene() { if (this.currentIndex > 0) this.renderScene(this.currentIndex - 1); }
        nextScene() { if (this.currentIndex < this.scenes.length - 1) this.renderScene(this.currentIndex + 1); }

        updateNav() {
            const total = this.scenes.length;
            if (this.currentSlideEl) this.currentSlideEl.textContent = this.currentIndex + 1;
            if (this.totalSlidesEl) this.totalSlidesEl.textContent = total;
            if (this.prevBtn) this.prevBtn.disabled = this.currentIndex === 0;
            if (this.nextBtn) this.nextBtn.disabled = this.currentIndex === total - 1;
            if (this.progressFill) this.progressFill.style.width = `${((this.currentIndex + 1) / total) * 100}%`;
        }

        // ---- Completion ----

        checkCompletion() {
            const allVisited = this.scenes.every((_, i) => this.visitedScenes.has(i) || i === this.currentIndex);
            const quizScenes = this.scenes.filter(s => s.type === 'quiz');
            const allQuizzesDone = quizScenes.every(s => this.quizAnswers[s.id]);
            if (allVisited && (quizScenes.length === 0 || allQuizzesDone)) {
                this.showCompletion();
            }
        }

        async showCompletion() {
            if (this.completionOverlay.style.display === 'flex') return;
            this.stopAudio();
            this.completionOverlay.style.display = 'flex';
            this.startConfetti();

            // Compute quiz score
            let totalScore = 0;
            let quizCount = 0;
            Object.values(this.quizAnswers).forEach(answers => {
                if (Array.isArray(answers)) {
                    answers.forEach(a => { if (a.selected_option >= 0) quizCount++; });
                }
            });
            const completedScenes = this.visitedScenes.size + 1;

            try {
                const resp = await fetch('/api/v2/course/complete', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        course_id: this.courseData.courseId || '',
                        student_id: this.courseData.metadata?.student_id || '',
                        quiz_score: totalScore,
                        time_spent: this.totalTimeSpent,
                        scenes_visited: [...this.visitedScenes, this.currentIndex],
                        total_scenes: this.scenes.length,
                    })
                });
                const data = await resp.json();
                this.renderCompletionStats(data, completedScenes);
            } catch (e) {
                this.renderCompletionStats({ badges: ['课堂参与者'], next_steps: ['回顾重点内容'], summary: '恭喜完成课程！' }, completedScenes);
            }
        }

        renderCompletionStats(data, completed) {
            const subtitle = document.getElementById('completion-subtitle');
            const stats = document.getElementById('completion-stats');
            const badges = document.getElementById('completion-badges');
            const next = document.getElementById('completion-next');

            if (subtitle) subtitle.textContent = data.summary || `完成了 ${completed} 个学习场景`;
            if (stats) stats.innerHTML = `
                <div class="completion-stat"><span class="stat-value">${completed}</span><span class="stat-label">完成场景</span></div>
                <div class="completion-stat"><span class="stat-value">${data.quiz_score || '-'}%</span><span class="stat-label">测验成绩</span></div>
                <div class="completion-stat"><span class="stat-value">${Math.floor(this.totalTimeSpent / 60)}分钟</span><span class="stat-label">学习时长</span></div>
            `;
            if (badges) badges.innerHTML = (data.badges || []).map(b =>
                `<span class="completion-badge">${b}</span>`).join('');
            if (next) next.innerHTML = '<h4>下一步建议</h4>' + (data.next_steps || []).map(s =>
                `<p class="next-step-item">${s}</p>`).join('');
        }

        startConfetti() {
            const canvas = document.getElementById('confetti-canvas');
            if (!canvas) return;
            const ctx = canvas.getContext('2d');
            canvas.width = window.innerWidth;
            canvas.height = window.innerHeight;

            const particles = Array.from({ length: 80 }, () => ({
                x: Math.random() * canvas.width,
                y: -20 - Math.random() * 100,
                w: Math.random() * 8 + 4,
                h: Math.random() * 5 + 2,
                color: `hsl(${Math.random() * 360}, 80%, ${50 + Math.random() * 20}%)`,
                vy: Math.random() * 2 + 1.5,
                vx: (Math.random() - 0.5) * 2,
                rot: Math.random() * 360,
                rv: (Math.random() - 0.5) * 4,
            }));

            const animate = () => {
                ctx.clearRect(0, 0, canvas.width, canvas.height);
                let done = true;
                particles.forEach(p => {
                    if (p.y < canvas.height + 20) {
                        p.y += p.vy;
                        p.x += p.vx;
                        p.rot += p.rv;
                        done = false;
                    }
                    ctx.save();
                    ctx.translate(p.x, p.y);
                    ctx.rotate(p.rot * Math.PI / 180);
                    ctx.fillStyle = p.color;
                    ctx.fillRect(-p.w / 2, -p.h / 2, p.w, p.h);
                    ctx.restore();
                });
                if (!done) requestAnimationFrame(animate);
            };
            animate();
        }

        // ---- Exit ----

        showExitModal() { const el = document.getElementById('exit-modal'); if (el) el.style.display = 'flex'; }
        hideExitModal() { const el = document.getElementById('exit-modal'); if (el) el.style.display = 'none'; }
        confirmExit() {
            this.stopAudio();
            sessionStorage.removeItem('generationSession');
            window.location.href = '/index.html';
        }

        // ---- Chat Voice Input (Speech Recognition) ----

        initChatVoiceInput() {
            const btn = this.chatVoiceBtn;
            const input = this.chatInput;
            if (!btn || !input) return;

            if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
                const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
                this.chatRecognition = new SpeechRecognition();
                this.chatRecognition.continuous = true;
                this.chatRecognition.interimResults = true;
                this.chatRecognition.lang = 'zh-CN';

                this.chatRecognition.onstart = () => {
                    this.chatIsRecording = true;
                    btn.classList.add('recording');
                    btn.querySelector('i')?.classList.replace('fa-microphone', 'fa-stop');
                };

                this.chatRecognition.onresult = (event) => {
                    let finalTranscript = '';
                    let newInterim = '';
                    for (let i = event.resultIndex; i < event.results.length; i++) {
                        const transcript = event.results[i][0].transcript;
                        if (event.results[i].isFinal) {
                            finalTranscript += transcript;
                        } else {
                            newInterim += transcript;
                        }
                    }
                    if (this.chatInterimText) {
                        input.value = input.value.slice(0, input.value.length - this.chatInterimText.length);
                    }
                    if (finalTranscript) {
                        input.value += finalTranscript;
                        this.chatInterimText = '';
                    } else if (newInterim) {
                        input.value += newInterim;
                        this.chatInterimText = newInterim;
                    }
                    input.focus();
                };

                this.chatRecognition.onerror = (event) => {
                    console.error('Speech recognition error:', event.error);
                    this.stopChatRecording();
                };

                this.chatRecognition.onend = () => {
                    this.stopChatRecording();
                };

                btn.addEventListener('click', () => {
                    if (this.chatIsRecording) {
                        this.chatRecognition?.stop();
                    } else {
                        this.chatRecognition?.start();
                    }
                });
            } else {
                btn.style.opacity = '0.5';
                btn.style.pointerEvents = 'none';
                btn.title = '浏览器不支持语音识别';
            }
        }

        stopChatRecording() {
            this.chatIsRecording = false;
            const input = this.chatInput;
            if (input && this.chatInterimText) {
                input.value = input.value.slice(0, input.value.length - this.chatInterimText.length);
                this.chatInterimText = '';
            }
            const btn = this.chatVoiceBtn;
            if (btn) {
                btn.classList.remove('recording');
                btn.querySelector('i')?.classList.replace('fa-stop', 'fa-microphone');
            }
        }

        // ---- Utils ----

        escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }
    }

    // Global instance
    let classroomController;
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => {
            classroomController = new ClassroomController();
            classroomController.init();
        });
    } else {
        classroomController = new ClassroomController();
        classroomController.init();
    }
})();
