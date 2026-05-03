(function() {
    'use strict';

    var DEFAULT_VIEWPORT = 1000;
    var DEFAULT_RATIO = 0.5625;
    var EFFECT_CLEAR_MS = 5000;

    function OpenMAICSlidePlayer(options) {
        options = options || {};
        this.container = options.container;
        this.stage = options.stage || (this.container ? this.container.parentElement : null);
        this.overlay = options.overlay || null;
        this.audioElement = options.audioElement || null;
        this.speechText = options.speechText || null;
        this.syncElement = options.syncElement || null;
        this.teacherAvatar = options.teacherAvatar || null;
        this.onSlideEnd = options.onSlideEnd || null;
        this.getSpeed = options.getSpeed || (function() { return 1; });

        this.slide = null;
        this.queue = [];
        this.actionIndex = 0;
        this.mode = 'idle';
        this.timers = [];
        this.currentUtterance = null;
        this.pausedSpeech = null;
        this.syncTimers = [];
    }

    OpenMAICSlidePlayer.extractDeck = function(payload) {
        if (!payload || typeof payload !== 'object') return null;
        var candidates = [
            payload.data && payload.data.deck,
            payload.deck,
            payload.openmaic_deck,
            payload.openmaicDeck,
            payload.openmaic,
            payload
        ];
        for (var i = 0; i < candidates.length; i++) {
            var item = candidates[i];
            if (item && Array.isArray(item.slides)) {
                for (var j = 0; j < item.slides.length; j++) {
                    if (Array.isArray(item.slides[j].elements)) return item;
                }
            }
        }
        return null;
    };

    OpenMAICSlidePlayer.hasDeck = function(payload) {
        return !!OpenMAICSlidePlayer.extractDeck(payload);
    };

    OpenMAICSlidePlayer.prototype.render = function(slide) {
        if (!this.container || !slide) return;
        this.stop({ keepSlide: true });
        this.slide = slide;

        var viewport = this.getViewport(slide);
        var height = viewport.width * viewport.ratio;
        var bgStyle = this.buildSlideBackground(slide);
        var elementsHtml = (slide.elements || []).map(function(el, index) {
            return this.renderElement(el, index, viewport);
        }, this).join('');

        this.container.style.display = 'block';
        this.container.className = 'slide-container openmaic-slide-host';
        this.container.innerHTML =
            '<div class="openmaic-player" data-slide-id="' + this.escapeAttr(slide.id || '') + '">' +
                '<div class="openmaic-stage-shell">' +
                    '<div class="openmaic-slide-canvas" style="' + bgStyle + '" data-openmaic-canvas>' +
                        '<div class="openmaic-slide-accent"></div>' +
                        elementsHtml +
                        '<div class="openmaic-effect-layer" data-openmaic-effects></div>' +
                    '</div>' +
                '</div>' +
            '</div>';
    };

    OpenMAICSlidePlayer.prototype.start = function(actions) {
        if (!this.slide) return;
        this.stop({ keepSlide: true });
        this.queue = this.normalizeActions(actions, this.slide);
        this.actionIndex = 0;
        this.mode = 'playing';
        this.processNext();
    };

    OpenMAICSlidePlayer.prototype.pause = function() {
        if (this.mode !== 'playing') return;
        this.mode = 'paused';
        this.pauseAudio();
        this.clearTimers();
        this.clearSpeechVisualSync();
    };

    OpenMAICSlidePlayer.prototype.resume = function() {
        if (this.mode !== 'paused') return;
        this.mode = 'playing';
        if (this.pausedSpeech) {
            var text = this.pausedSpeech.text;
            this.pausedSpeech = null;
            var self = this;
            this.playBrowserSpeech(text).then(function() { self.processNext(); });
            return;
        }
        this.processNext();
    };

    OpenMAICSlidePlayer.prototype.stop = function(options) {
        options = options || {};
        this.mode = 'idle';
        this.queue = [];
        this.actionIndex = 0;
        this.clearTimers();
        this.clearEffects();
        this.clearSpeechVisualSync();
        this.stopAudio();
        if (!options.keepSlide) this.slide = null;
    };

    OpenMAICSlidePlayer.prototype.processNext = function() {
        if (this.mode !== 'playing') return;
        if (this.actionIndex >= this.queue.length) {
            this.mode = 'idle';
            this.clearEffects();
            if (this.onSlideEnd) this.onSlideEnd();
            return;
        }
        var action = this.queue[this.actionIndex];
        this.actionIndex++;
        this.executeAction(action);
    };

    OpenMAICSlidePlayer.prototype.executeAction = function(action) {
        if (!action) { this.processNext(); return; }
        var self = this;
        var delay = Number(action.delay) || 0;
        var timerId = setTimeout(function() {
            self.removeTimer(timerId);
            switch (action.type) {
                case 'spotlight':
                    self.showSpotlight(action.targetId, action.duration || 3000);
                    self.processNext();
                    break;
                case 'laser':
                    self.showLaser(action.x, action.y, action.duration || 2000);
                    self.processNext();
                    break;
                case 'speech':
                    self.playSpeech(action.text).then(function() { self.processNext(); });
                    break;
                default:
                    self.processNext();
            }
        }, delay);
        this.timers.push(timerId);
    };

    OpenMAICSlidePlayer.prototype.showSpotlight = function(targetId, duration) {
        if (!this.overlay) return;
        var target = targetId ? document.getElementById(targetId) : null;
        var rect = target ? target.getBoundingClientRect() : {left: 200, top: 150, width: 600, height: 300};
        var el = document.createElement('div');
        el.className = 'openmaic-spotlight';
        el.style.cssText = 'position:fixed;left:' + rect.left + 'px;top:' + rect.top + 'px;width:' + rect.width + 'px;height:' + rect.height + 'px;pointer-events:none;z-index:9999;border-radius:12px;box-shadow:0 0 0 9999px rgba(0,0,0,0.45),0 0 30px rgba(59,130,246,0.6);transition:opacity 0.5s;';
        this.overlay.appendChild(el);
        var self = this;
        var timerId = setTimeout(function() {
            el.style.opacity = '0';
            setTimeout(function() { if (el.parentNode) el.parentNode.removeChild(el); }, 500);
            self.removeTimer(timerId);
        }, duration);
        this.timers.push(timerId);
    };

    OpenMAICSlidePlayer.prototype.showLaser = function(x, y, duration) {
        if (!this.overlay) return;
        var dot = document.createElement('div');
        dot.className = 'openmaic-laser-dot';
        dot.style.cssText = 'position:fixed;left:' + (x || 500) + 'px;top:' + (y || 280) + 'px;width:12px;height:12px;border-radius:50%;background:rgba(239,68,68,0.9);box-shadow:0 0 16px rgba(239,68,68,0.7);pointer-events:none;z-index:10000;transition:opacity 0.3s;';
        this.overlay.appendChild(dot);
        var self = this;
        var timerId = setTimeout(function() {
            dot.style.opacity = '0';
            setTimeout(function() { if (dot.parentNode) dot.parentNode.removeChild(dot); }, 300);
            self.removeTimer(timerId);
        }, duration);
        this.timers.push(timerId);
    };

    OpenMAICSlidePlayer.prototype.playSpeech = function(text) {
        var self = this;
        if (this.audioElement && text) {
            return this.playBrowserSpeech(text);
        }
        return Promise.resolve();
    };

    OpenMAICSlidePlayer.prototype.playBrowserSpeech = function(text) {
        var self = this;
        return new Promise(function(resolve) {
            if (!window.speechSynthesis) { resolve(); return; }
            window.speechSynthesis.cancel();
            var utterance = new SpeechSynthesisUtterance(text);
            utterance.rate = self.getSpeed();
            utterance.lang = 'zh-CN';
            utterance.onend = function() { self.currentUtterance = null; resolve(); };
            utterance.onerror = function() { self.currentUtterance = null; resolve(); };
            self.currentUtterance = utterance;
            window.speechSynthesis.speak(utterance);
        });
    };

    OpenMAICSlidePlayer.prototype.pauseAudio = function() {
        if (window.speechSynthesis) {
            window.speechSynthesis.cancel();
        }
        if (this.audioElement) this.audioElement.pause();
    };

    OpenMAICSlidePlayer.prototype.stopAudio = function() {
        this.pauseAudio();
        this.currentUtterance = null;
        this.pausedSpeech = null;
    };

    OpenMAICSlidePlayer.prototype.clearTimers = function() {
        for (var i = 0; i < this.timers.length; i++) {
            clearTimeout(this.timers[i]);
        }
        this.timers = [];
    };

    OpenMAICSlidePlayer.prototype.removeTimer = function(id) {
        var idx = this.timers.indexOf(id);
        if (idx >= 0) this.timers.splice(idx, 1);
    };

    OpenMAICSlidePlayer.prototype.clearEffects = function() {
        if (this.overlay) this.overlay.innerHTML = '';
    };

    OpenMAICSlidePlayer.prototype.clearSpeechVisualSync = function() {
        for (var i = 0; i < this.syncTimers.length; i++) {
            clearInterval(this.syncTimers[i]);
        }
        this.syncTimers = [];
    };

    OpenMAICSlidePlayer.prototype.normalizeActions = function(actions, slide) {
        if (!Array.isArray(actions)) return [];
        return actions.filter(function(a) { return a && a.type; });
    };

    OpenMAICSlidePlayer.prototype.getViewport = function(slide) {
        var vs = (slide && slide.viewportSize) || {};
        return {
            width: vs.width || DEFAULT_VIEWPORT,
            ratio: (slide && slide.viewportRatio) || DEFAULT_RATIO
        };
    };

    OpenMAICSlidePlayer.prototype.buildSlideBackground = function(slide) {
        var bg = (slide && slide.background) || {};
        var style = '';
        if (bg.type === 'solid' && bg.color) {
            style += 'background-color:' + bg.color + ';';
        } else {
            style += 'background-color:#F8FAFC;';
        }
        return style;
    };

    // ---- Element Rendering ----

    OpenMAICSlidePlayer.prototype.renderElement = function(el, index, viewport) {
        if (!el || !el.type) return '';
        var style = this.buildElementStyle(el, viewport, index);
        var content = this.renderElementContent(el);
        var cls = 'openmaic-element openmaic-element-' + el.type;
        return '<div class="' + cls + '" id="' + this.escapeAttr(el.id || '') + '" style="' + style + '">' + content + '</div>';
    };

    OpenMAICSlidePlayer.prototype.renderElementContent = function(el) {
        switch (el.type) {
            case 'text':
                return this.sanitizeRichText(el.content || '');
            case 'image':
                return '<img src="' + this.escapeAttr(el.src || '') + '" alt="">';
            case 'shape':
                return this.renderShape(el);
            case 'line':
                return this.renderLine(el);
            case 'chart':
                return this.renderChart(el);
            case 'table':
                return this.renderTable(el);
            case 'latex':
                return '<div class="openmaic-latex">' + this.escapeHtml(el.html || el.latex || '') + '</div>';
            case 'video':
                return '<video src="' + this.escapeAttr(el.src || '') + '" ' + (el.autoplay ? 'autoplay' : '') + ' controls></video>';
            case 'code':
                return this.renderCode(el);
            default:
                return '';
        }
    };

    OpenMAICSlidePlayer.prototype.renderShape = function(el) {
        var vb = [0, 0, 100, 100];
        if (Array.isArray(el.viewBox)) {
            if (el.viewBox.length === 4) vb = el.viewBox;
            else vb = [0, 0, el.viewBox[0] || 100, el.viewBox[1] || 100];
        }
        var viewBox = vb.join(' ');
        var gradient = this.renderShapeGradient(el);
        var fill = gradient ? 'url(#' + gradient.id + ')' : this.escapeAttr(el.fill || '#5b9bd5');
        var textContent = '';
        if (el.text && el.text.content) {
            textContent = '<foreignObject x="0" y="0" width="100%" height="100%"><div class="openmaic-shape-text">' + this.sanitizeRichText(el.text.content) + '</div></foreignObject>';
        }
        return '<svg viewBox="' + viewBox + '" preserveAspectRatio="none">' + (gradient ? gradient.defs : '') + '<path d="' + this.escapeAttr(el.path || '') + '" fill="' + fill + '"></path>' + textContent + '</svg>';
    };

    OpenMAICSlidePlayer.prototype.renderShapeGradient = function(el) {
        if (!el.gradient || !Array.isArray(el.gradient.colors) || el.gradient.colors.length === 0) return null;
        var id = 'grad-' + this.escapeAttr(el.id || Date.now());
        var colors = el.gradient.colors.map(function(c) {
            return '<stop offset="' + (Number(c.pos || 0) * 100) + '%" stop-color="' + this.escapeAttr(c.color || '#5b9bd5') + '"></stop>';
        }, this).join('');
        var body = el.gradient.type === 'radial'
            ? '<radialGradient id="' + id + '">' + colors + '</radialGradient>'
            : '<linearGradient id="' + id + '" gradientTransform="rotate(' + (Number(el.gradient.rotate || 0)) + ')">' + colors + '</linearGradient>';
        return { id: id, defs: '<defs>' + body + '</defs>' };
    };

    OpenMAICSlidePlayer.prototype.renderLine = function(el) {
        var start = el.start || [0, 0];
        var end = el.end || [100, 0];
        var dash = el.style === 'dashed' ? 'stroke-dasharray="8 6"' : el.style === 'dotted' ? 'stroke-dasharray="2 6"' : '';
        return '<svg viewBox="0 0 1000 562.5" preserveAspectRatio="none"><line x1="' + (Number(start[0]) || 0) + '" y1="' + (Number(start[1]) || 0) + '" x2="' + (Number(end[0]) || 0) + '" y2="' + (Number(end[1]) || 0) + '" stroke="' + this.escapeAttr(el.color || '#333333') + '" stroke-width="' + (Number(el.width) || 2) + '" ' + dash + ' stroke-linecap="round"></line></svg>';
    };

    OpenMAICSlidePlayer.prototype.renderChart = function(el) {
        var data = el.data || {};
        var labels = data.labels || [];
        var values = (data.series && data.series[0]) || [];
        var max = Math.max.apply(null, values.concat([1]));
        var colors = el.themeColors || ['#6366f1', '#8b5cf6', '#06b6d4'];
        var bars = values.map(function(value, index) {
            return '<div class="openmaic-chart-bar"><span style="height:' + Math.max(8, (value / max) * 100) + '%;background:' + this.escapeAttr(colors[index % colors.length]) + '"></span><small>' + this.escapeHtml(labels[index] || '') + '</small></div>';
        }, this).join('');
        return '<div class="openmaic-chart">' + bars + '</div>';
    };

    OpenMAICSlidePlayer.prototype.renderTable = function(el) {
        var rows = el.data || [];
        return '<table>' + rows.map(function(row) {
            return '<tr>' + row.map(function(cell) {
                return '<td>' + this.escapeHtml((cell && cell.text) || '') + '</td>';
            }, this).join('') + '</tr>';
        }, this).join('') + '</table>';
    };

    OpenMAICSlidePlayer.prototype.renderCode = function(el) {
        var code;
        if (typeof el.content === 'string' && el.content.trim()) {
            code = this.escapeHtml(el.content);
        } else {
            code = (el.lines || []).map(function(line) {
                return this.escapeHtml((line && line.content) || '');
            }, this).join('\n');
        }
        var lang = el.language || el.lang || '';
        var langLabel = lang ? '<span class="openmaic-code-lang">' + this.escapeHtml(lang) + '</span>' : '';
        return langLabel + '<pre><code>' + code + '</code></pre>';
    };

    OpenMAICSlidePlayer.prototype.buildElementStyle = function(el, viewport, index) {
        var left = this.percent(el.left || 0, viewport.width);
        var top = this.percent(el.top || 0, viewport.height);
        var width = this.percent(el.width || 100, viewport.width);
        var height = this.percent(el.height || 100, viewport.height);
        var style = 'position:absolute;left:' + left + '%;top:' + top + '%;width:' + width + '%;height:' + height + '%;';
        if (el.fill && el.type !== 'shape') {
            style += 'background-color:' + el.fill + ';';
        }
        if (el.defaultColor) {
            style += 'color:' + el.defaultColor + ';';
        }
        if (el.defaultFontName) {
            style += 'font-family:"' + el.defaultFontName + '",sans-serif;';
        }
        if (el.opacity !== undefined && el.opacity !== 1) {
            style += 'opacity:' + el.opacity + ';';
        }
        if (el.rotate) {
            style += 'transform:rotate(' + el.rotate + 'deg);';
        }
        if (index !== undefined) {
            style += 'animation:openmaicElementIn 0.5s ease-out ' + (index * 0.1) + 's both;';
        }
        return style;
    };

    OpenMAICSlidePlayer.prototype.percent = function(value, total) {
        return total > 0 ? (Number(value) / total) * 100 : 0;
    };

    OpenMAICSlidePlayer.prototype.escapeHtml = function(str) {
        if (!str) return '';
        return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    };

    OpenMAICSlidePlayer.prototype.escapeAttr = function(str) {
        if (!str) return '';
        return String(str).replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    };

    OpenMAICSlidePlayer.prototype.sanitizeRichText = function(html) {
        if (!html) return '';
        return String(html);
    };

    window.OpenMAICSlidePlayer = OpenMAICSlidePlayer;
})();
