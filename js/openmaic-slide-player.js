(function() {
    'use strict';

    var DEFAULT_VIEWPORT = 1000;
    var DEFAULT_RATIO = 0.5625;

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

    // ---- Action Pipeline ----

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
                    self.showSpotlight(action.targetId, action.duration || 4000);
                    self.processNext();
                    break;
                case 'laser':
                    self.showLaser(action.x, action.y, action.duration || 3000);
                    self.processNext();
                    break;
                case 'speech':
                    self.showSpeechText(action.text);
                    self.playSpeech(action.text).then(function() { self.processNext(); });
                    break;
                default:
                    self.processNext();
            }
        }, delay);
        this.timers.push(timerId);
    };

    // ---- Spotlight: SVG Mask Implementation ----
    // Full-screen dim overlay with a "hole" punched at the target element position,
    // plus a glowing border. Matches OpenMAIC SpotlightOverlay.tsx behavior.

    OpenMAICSlidePlayer.prototype.showSpotlight = function(targetId, duration) {
        if (!this.overlay) return;
        duration = duration || 4000;
        var target = targetId ? document.getElementById(targetId) : null;
        var rect = target ? target.getBoundingClientRect() : {left: 200, top: 150, width: 600, height: 300};
        var pad = 10;

        if (target) {
            target.classList.add('spotlight-target');
        }

        var svgNS = 'http://www.w3.org/2000/svg';
        var svg = document.createElementNS(svgNS, 'svg');
        svg.setAttribute('class', 'openmaic-spotlight-svg');
        svg.style.cssText = 'position:fixed;top:0;left:0;width:100%;height:100%;pointer-events:none;z-index:9999;';

        var maskId = 'spotlight-mask-' + Date.now();
        var defs = document.createElementNS(svgNS, 'defs');
        var mask = document.createElementNS(svgNS, 'mask');
        mask.setAttribute('id', maskId);

        // White = show dim overlay (visible through mask)
        var whiteRect = document.createElementNS(svgNS, 'rect');
        whiteRect.setAttribute('width', '100%');
        whiteRect.setAttribute('height', '100%');
        whiteRect.setAttribute('fill', 'white');
        mask.appendChild(whiteRect);

        // Black = punch hole at target (hidden through mask → transparent)
        var hole = document.createElementNS(svgNS, 'rect');
        hole.setAttribute('x', Math.max(0, rect.left - pad));
        hole.setAttribute('y', Math.max(0, rect.top - pad));
        hole.setAttribute('width', rect.width + pad * 2);
        hole.setAttribute('height', rect.height + pad * 2);
        hole.setAttribute('fill', 'black');
        hole.setAttribute('rx', '14');
        mask.appendChild(hole);

        defs.appendChild(mask);
        svg.appendChild(defs);

        // Dim overlay with mask applied
        var dimRect = document.createElementNS(svgNS, 'rect');
        dimRect.setAttribute('width', '100%');
        dimRect.setAttribute('height', '100%');
        dimRect.setAttribute('fill', 'rgba(15, 23, 42, 0.6)');
        dimRect.setAttribute('mask', 'url(#' + maskId + ')');
        svg.appendChild(dimRect);

        // Glow border around the hole
        var glow = document.createElementNS(svgNS, 'rect');
        glow.setAttribute('x', Math.max(0, rect.left - pad));
        glow.setAttribute('y', Math.max(0, rect.top - pad));
        glow.setAttribute('width', rect.width + pad * 2);
        glow.setAttribute('height', rect.height + pad * 2);
        glow.setAttribute('fill', 'none');
        glow.setAttribute('stroke', 'rgba(99, 102, 241, 0.7)');
        glow.setAttribute('stroke-width', '2.5');
        glow.setAttribute('rx', '14');
        glow.setAttribute('class', 'openmaic-spotlight-glow');
        svg.appendChild(glow);

        this.overlay.appendChild(svg);

        var self = this;
        var timerId = setTimeout(function() {
            svg.style.opacity = '0';
            svg.style.transition = 'opacity 0.4s ease';
            if (target) target.classList.remove('spotlight-target');
            setTimeout(function() {
                if (svg.parentNode) svg.parentNode.removeChild(svg);
            }, 400);
            self.removeTimer(timerId);
        }, duration);
        this.timers.push(timerId);
    };

    // ---- Laser: Animated Fly-in + Pulse Ring ----
    // Red dot flies in from the nearest viewport corner to the target position,
    // with a pulsing ring. Matches OpenMAIC LaserOverlay.tsx behavior.

    OpenMAICSlidePlayer.prototype.showLaser = function(x, y, duration) {
        if (!this.overlay) return;
        duration = duration || 3000;
        x = x || 500;
        y = y || 280;
        var vw = window.innerWidth;
        var vh = window.innerHeight;

        // Fly-in from nearest corner
        var startX = x < vw / 2 ? -20 : vw + 20;
        var startY = y < vh / 2 ? -20 : vh + 20;

        var container = document.createElement('div');
        container.className = 'openmaic-laser-container';
        container.style.cssText = 'position:fixed;top:0;left:0;width:100%;height:100%;pointer-events:none;z-index:10000;';

        // Pulsing ring around the target
        var ring = document.createElement('div');
        ring.className = 'openmaic-laser-ring';
        ring.style.cssText = 'position:fixed;left:' + (x - 20) + 'px;top:' + (y - 20) + 'px;width:40px;height:40px;';
        container.appendChild(ring);

        // Animated dot with CSS custom properties for fly-in trajectory
        var dot = document.createElement('div');
        dot.className = 'openmaic-laser-dot';
        dot.style.setProperty('--laser-start-x', startX + 'px');
        dot.style.setProperty('--laser-start-y', startY + 'px');
        dot.style.setProperty('--laser-end-x', x + 'px');
        dot.style.setProperty('--laser-end-y', y + 'px');
        container.appendChild(dot);

        this.overlay.appendChild(container);

        var self = this;
        var timerId = setTimeout(function() {
            container.style.opacity = '0';
            container.style.transition = 'opacity 0.3s ease';
            setTimeout(function() {
                if (container.parentNode) container.parentNode.removeChild(container);
            }, 300);
            self.removeTimer(timerId);
        }, duration);
        this.timers.push(timerId);
    };

    // ---- Speech ----

    OpenMAICSlidePlayer.prototype.showSpeechText = function(text) {
        if (this.speechText && text) {
            this.speechText.textContent = text;
        }
        if (this.syncElement) {
            this.syncElement.style.display = 'flex';
        }
        if (this.teacherAvatar) {
            this.teacherAvatar.classList.add('speaking');
        }
    };

    OpenMAICSlidePlayer.prototype.hideSpeechText = function() {
        if (this.syncElement) {
            this.syncElement.style.display = 'none';
        }
        if (this.teacherAvatar) {
            this.teacherAvatar.classList.remove('speaking');
        }
    };

    OpenMAICSlidePlayer.prototype.playSpeech = function(text) {
        if (text) {
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
            utterance.onend = function() {
                self.currentUtterance = null;
                self.hideSpeechText();
                resolve();
            };
            utterance.onerror = function() {
                self.currentUtterance = null;
                self.hideSpeechText();
                resolve();
            };
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
        this.hideSpeechText();
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
        // Remove spotlight-target class from any elements
        var targets = document.querySelectorAll('.spotlight-target');
        for (var i = 0; i < targets.length; i++) {
            targets[i].classList.remove('spotlight-target');
        }
    };

    OpenMAICSlidePlayer.prototype.clearSpeechVisualSync = function() {
        for (var i = 0; i < this.syncTimers.length; i++) {
            clearInterval(this.syncTimers[i]);
        }
        this.syncTimers = [];
    };

    OpenMAICSlidePlayer.prototype.normalizeActions = function(actions, slide) {
        if (!Array.isArray(actions)) return [];
        // Resolve elementId-based spotlight/laser to pixel coordinates if needed
        return actions.filter(function(a) { return a && a.type; }).map(function(a) {
            if (a.type === 'spotlight' && a.elementId && !a.targetId) {
                a.targetId = a.elementId;
            }
            if (a.type === 'laser' && a.elementId && (a.x === undefined)) {
                var el = document.getElementById(a.elementId);
                if (el) {
                    var r = el.getBoundingClientRect();
                    a.x = r.left + r.width / 2;
                    a.y = r.top + r.height / 2;
                }
            }
            return a;
        });
    };

    // ---- Viewport & Background ----

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
            textContent = '<foreignObject x="0" y="0" width="100%" height="100%"><div xmlns="http://www.w3.org/1999/xhtml" class="openmaic-shape-text">' + this.sanitizeRichText(el.text.content) + '</div></foreignObject>';
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
