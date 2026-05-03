(function() {
    'use strict';

    var VIEWPORT_W = 1000;
    var VIEWPORT_H = 562.5;
    var MARGIN = 30;
    var GAP = 16;
    var TITLE_H = 56;
    var CARD_RADIUS = 10;

    var ICON_MAP = {
        book: '📖',
        lightbulb: '💡',
        code: '💻',
        check: '✅',
        star: '⭐',
        question: '❓',
        warning: '⚠',
        info: 'ℹ'
    };

    var THEME_COLORS = {
        blue:   { bg: '#DBEAFE', text: '#1E40AF', accent: '#3B82F6', hex: '#DBEAFE' },
        yellow: { bg: '#FEF3C7', text: '#92400E', accent: '#F59E0B', hex: '#FEF3C7' },
        green:  { bg: '#D1FAE5', text: '#065F46', accent: '#10B981', hex: '#D1FAE5' },
        purple: { bg: '#EDE9FE', text: '#5B21B6', accent: '#8B5CF6', hex: '#EDE9FE' },
        orange: { bg: '#FFF7ED', text: '#9A3412', accent: '#F97316', hex: '#FFF7ED' }
    };

    function escapeHtml(str) {
        if (!str) return '';
        return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    }

    function parseMarkdown(text) {
        if (!text) return '';
        var html = String(text);
        html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
        html = html.replace(/`([^`\n]+)`/g, '<code>$1</code>');
        html = html.replace(/\n/g, '<br>');
        return html;
    }

    function clampCoord(val, min, max) {
        return Math.max(min, Math.min(max, Number(val) || 0));
    }

    function validateElement(el) {
        if (!el || typeof el !== 'object') return false;
        if (!el.type) return false;
        el.left = clampCoord(el.left, 0, VIEWPORT_W - 1);
        el.top = clampCoord(el.top, 0, VIEWPORT_H - 1);
        el.width = clampCoord(el.width, 1, VIEWPORT_W);
        el.height = clampCoord(el.height, 1, VIEWPORT_H);
        if (el.left + el.width > VIEWPORT_W) el.width = VIEWPORT_W - el.left;
        if (el.top + el.height > VIEWPORT_H) el.height = VIEWPORT_H - el.top;
        return true;
    }

    function makeRoundedRectPath(w, h, r) {
        var wr = Math.min(r, w / 2);
        var hr = Math.min(r, h / 2);
        return ['M', wr, 0,
                'L', w - wr, 0,
                'Q', w, 0, w, hr,
                'L', w, h - hr,
                'Q', w, h, w - wr, h,
                'L', wr, h,
                'Q', 0, h, 0, h - hr,
                'L', 0, hr,
                'Q', 0, 0, wr, 0,
                'Z'].join(' ');
    }

    // ---- Element Builders ----

    function makeTitleBar(title, sceneId) {
        return {
            type: 'text',
            id: 'el-' + sceneId + '-title',
            left: 0, top: 0, width: VIEWPORT_W, height: TITLE_H,
            content: '<h1 style="margin:0;font-size:22px;font-weight:700;text-align:center;line-height:' + TITLE_H + 'px;">' + escapeHtml(title) + '</h1>',
            defaultColor: '#FFFFFF',
            fill: '#1E40AF',
            defaultFontName: 'Microsoft YaHei'
        };
    }

    function makeCardBackground(left, top, width, height, colorTheme, cardIdx, sceneId) {
        var theme = THEME_COLORS[colorTheme] || THEME_COLORS.blue;
        return {
            type: 'shape',
            id: 'el-' + sceneId + '-card-' + cardIdx + '-bg',
            left: left, top: top, width: width, height: height,
            fill: theme.hex,
            shape_name: 'rectangle',
            viewBox: [0, 0, width, height],
            path: makeRoundedRectPath(width, height, CARD_RADIUS)
        };
    }

    function makeCardTitle(subTitle, icon, colorTheme, left, top, width, cardIdx, sceneId) {
        var theme = THEME_COLORS[colorTheme] || THEME_COLORS.blue;
        var iconChar = ICON_MAP[icon] || ICON_MAP.book;
        return {
            type: 'text',
            id: 'el-' + sceneId + '-card-' + cardIdx + '-title',
            left: left + 10, top: top + 8, width: width - 20, height: 24,
            content: '<strong style="color:' + theme.text + ';font-size:14px;">' + iconChar + ' ' + escapeHtml(subTitle) + '</strong>',
            defaultColor: theme.text,
            defaultFontName: 'Microsoft YaHei'
        };
    }

    function makeCardBody(text, colorTheme, left, top, width, height, cardIdx, sceneId) {
        var theme = THEME_COLORS[colorTheme] || THEME_COLORS.blue;
        return {
            type: 'text',
            id: 'el-' + sceneId + '-card-' + cardIdx + '-body',
            left: left + 10, top: top, width: width - 20, height: height,
            content: '<div style="color:' + theme.text + ';font-size:13px;line-height:1.5;">' + parseMarkdown(text) + '</div>',
            defaultColor: theme.text,
            defaultFontName: 'Microsoft YaHei'
        };
    }

    function makeCardCode(codeSnippet, colorTheme, left, top, width, height, cardIdx, sceneId) {
        return {
            type: 'code',
            id: 'el-' + sceneId + '-card-' + cardIdx + '-code',
            left: left + 8, top: top, width: width - 16, height: height,
            content: codeSnippet,
            language: ''
        };
    }

    function makeCardImage(imageUrl, left, top, width, height, cardIdx, sceneId) {
        return {
            type: 'image',
            id: 'el-' + sceneId + '-card-' + cardIdx + '-img',
            left: left, top: top, width: width, height: height,
            src: imageUrl
        };
    }

    // ---- Layout Templates ----

    function layoutTitleOnly(normalized, sceneId) {
        var elements = [];
        elements.push(makeTitleBar(normalized.title, sceneId));
        var items = normalized.content;
        if (items.length > 0) {
            var cardLeft = MARGIN;
            var cardTop = TITLE_H + GAP * 2;
            var cardW = VIEWPORT_W - MARGIN * 2;
            var cardH = VIEWPORT_H - cardTop - GAP;
            elements = elements.concat(buildCard(items[0], cardLeft, cardTop, cardW, cardH, 0, sceneId));
        }
        return elements;
    }

    function layoutTwoColumn(normalized, sceneId) {
        var elements = [];
        elements.push(makeTitleBar(normalized.title, sceneId));
        var items = normalized.content;
        if (items.length === 0) return elements;
        var bodyTop = TITLE_H + GAP * 2;
        var colW = (VIEWPORT_W - MARGIN * 2 - GAP) / 2;
        if (items.length === 1) {
            return elements.concat(buildCard(items[0], MARGIN, bodyTop,
                VIEWPORT_W - MARGIN * 2, VIEWPORT_H - bodyTop - GAP, 0, sceneId));
        }
        var row1H = (VIEWPORT_H - bodyTop - GAP * 3) * 0.55;
        elements = elements.concat(buildCard(items[0], MARGIN, bodyTop, colW, row1H, 0, sceneId));
        elements = elements.concat(buildCard(items[1], MARGIN + colW + GAP, bodyTop, colW, row1H, 1, sceneId));
        var row2Top = bodyTop + row1H + GAP;
        var row2H = VIEWPORT_H - row2Top - GAP;
        var remaining = items.slice(2);
        if (remaining.length === 0) return elements;
        if (remaining.length === 1) {
            elements = elements.concat(buildCard(remaining[0], MARGIN, row2Top,
                VIEWPORT_W - MARGIN * 2, row2H, 2, sceneId));
        } else {
            var subColW = (VIEWPORT_W - MARGIN * 2 - GAP * (remaining.length - 1)) / remaining.length;
            for (var i = 0; i < remaining.length; i++) {
                elements = elements.concat(buildCard(remaining[i],
                    MARGIN + i * (subColW + GAP), row2Top, subColW, row2H, 2 + i, sceneId));
            }
        }
        return elements;
    }

    function layoutGridCards(normalized, sceneId) {
        var elements = [];
        elements.push(makeTitleBar(normalized.title, sceneId));
        var items = normalized.content;
        if (items.length === 0) return elements;
        var bodyTop = TITLE_H + GAP * 2;
        var bodyH = VIEWPORT_H - bodyTop - GAP;
        var cols = Math.min(3, items.length);
        var rows = Math.ceil(items.length / cols);
        var cardW = (VIEWPORT_W - MARGIN * 2 - GAP * (cols - 1)) / cols;
        var cardH = (bodyH - GAP * (rows - 1)) / rows;
        for (var i = 0; i < items.length; i++) {
            var col = i % cols;
            var row = Math.floor(i / cols);
            elements = elements.concat(buildCard(items[i],
                MARGIN + col * (cardW + GAP),
                bodyTop + row * (cardH + GAP),
                cardW, cardH, i, sceneId));
        }
        return elements;
    }

    function layoutHeaderContent(normalized, sceneId) {
        var elements = [];
        elements.push(makeTitleBar(normalized.title, sceneId));
        var items = normalized.content;
        if (items.length === 0) return elements;
        var bodyTop = TITLE_H + GAP * 2;
        var headerH = 76;
        elements = elements.concat(buildCard(items[0], MARGIN, bodyTop,
            VIEWPORT_W - MARGIN * 2, headerH, 0, sceneId));
        var contentTop = bodyTop + headerH + GAP;
        var remaining = items.slice(1);
        if (remaining.length === 0) return elements;
        var colW = (VIEWPORT_W - MARGIN * 2 - GAP) / 2;
        var remainingH = VIEWPORT_H - contentTop - GAP;
        var rowsRemaining = Math.ceil(remaining.length / 2);
        var rowH = rowsRemaining > 0 ? (remainingH - GAP * (rowsRemaining - 1)) / rowsRemaining : remainingH;
        for (var i = 0; i < remaining.length; i++) {
            var col = i % 2;
            var row = Math.floor(i / 2);
            elements = elements.concat(buildCard(remaining[i],
                MARGIN + col * (colW + GAP),
                contentTop + row * (rowH + GAP),
                colW, rowH, 1 + i, sceneId));
        }
        return elements;
    }

    function layoutQuoteHighlight(normalized, sceneId) {
        var elements = [];
        elements.push(makeTitleBar(normalized.title, sceneId));
        var items = normalized.content;
        if (items.length === 0) return elements;
        var bodyTop = TITLE_H + GAP * 2;
        var quoteH = 100;
        if (items.length >= 1) {
            var theme = THEME_COLORS[items[0].color_theme] || THEME_COLORS.purple;
            elements.push({
                type: 'text',
                id: 'el-' + sceneId + '-card-0-body',
                left: MARGIN, top: bodyTop, width: VIEWPORT_W - MARGIN * 2, height: quoteH,
                content: '<blockquote style="margin:0;font-size:18px;color:' + theme.text + ';border-left:4px solid ' + theme.accent + ';padding-left:16px;">' + escapeHtml(items[0].text || items[0].sub_title) + '</blockquote>',
                defaultColor: theme.text,
                fill: theme.hex,
                defaultFontName: 'Microsoft YaHei'
            });
            elements.push(makeCardBackground(MARGIN, bodyTop, VIEWPORT_W - MARGIN * 2, quoteH, items[0].color_theme, 0, sceneId));
        }
        var contentTop = bodyTop + quoteH + GAP;
        var remaining = items.slice(1);
        if (remaining.length === 0) return elements;
        var colW = (VIEWPORT_W - MARGIN * 2 - GAP) / 2;
        var remainingH = VIEWPORT_H - contentTop - GAP;
        var rowsRemaining = Math.ceil(remaining.length / 2);
        var rowH = rowsRemaining > 0 ? (remainingH - GAP * (rowsRemaining - 1)) / rowsRemaining : remainingH;
        for (var i = 0; i < remaining.length; i++) {
            var col = i % 2;
            var row = Math.floor(i / 2);
            elements = elements.concat(buildCard(remaining[i],
                MARGIN + col * (colW + GAP),
                contentTop + row * (rowH + GAP),
                colW, rowH, 1 + i, sceneId));
        }
        return elements;
    }

    var LAYOUT_TEMPLATES = {
        'title-only': layoutTitleOnly,
        'two-column': layoutTwoColumn,
        'grid-cards': layoutGridCards,
        'header-content': layoutHeaderContent,
        'quote-highlight': layoutQuoteHighlight
    };

    // ---- Card Builder ----

    function buildCard(item, left, top, width, height, cardIdx, sceneId) {
        var elements = [];
        var theme = item.color_theme || 'blue';
        elements.push(makeCardBackground(left, top, width, height, theme, cardIdx, sceneId));
        var titleText = item.sub_title || '';
        var iconName = item.icon || 'book';
        var titleH = 28;
        elements.push(makeCardTitle(titleText, iconName, theme, left, top, width, cardIdx, sceneId));
        var bodyTop = top + titleH + 4;
        var bodyH = height - titleH - 12;
        var hasCode = !!(item.code_snippet && String(item.code_snippet).trim());
        var hasImage = !!(item.image_url && String(item.image_url).trim());
        if (hasCode && hasImage) {
            var codeW = width * 0.55;
            var imgW = width - codeW - 20;
            elements.push(makeCardBody(item.text, theme, left + 10, bodyTop, codeW, bodyH, cardIdx, sceneId));
            elements.push(makeCardCode(item.code_snippet, theme, left + 10, bodyTop + bodyH * 0.55, codeW, bodyH * 0.45, cardIdx, sceneId));
            elements.push(makeCardImage(item.image_url, left + codeW + 20, bodyTop, imgW, bodyH, cardIdx, sceneId));
        } else if (hasCode) {
            var textH = bodyH * 0.45;
            elements.push(makeCardBody(item.text, theme, left + 10, bodyTop, width, textH, cardIdx, sceneId));
            elements.push(makeCardCode(item.code_snippet, theme, left + 10, bodyTop + textH + 4, width, bodyH - textH - 4, cardIdx, sceneId));
        } else if (hasImage) {
            var txtW = width * 0.6;
            elements.push(makeCardBody(item.text, theme, left + 10, bodyTop, txtW, bodyH, cardIdx, sceneId));
            elements.push(makeCardImage(item.image_url, left + txtW + 10, bodyTop, width - txtW - 20, bodyH, cardIdx, sceneId));
        } else {
            elements.push(makeCardBody(item.text, theme, left + 10, bodyTop, width, bodyH, cardIdx, sceneId));
        }
        return elements;
    }

    // ---- Normalization ----

    function normalizeSlide(slide) {
        if (!slide || typeof slide !== 'object') return null;
        var layoutType = slide.layout_type || slide.layoutType || 'two-column';
        var content = slide.content || [];
        if (!Array.isArray(content)) content = [];
        var items = content.map(function(item) {
            if (!item || typeof item !== 'object') {
                return { sub_title: '', text: '', icon: 'book', color_theme: 'blue', code_snippet: '', image_url: '' };
            }
            return {
                sub_title: item.sub_title || item.subTitle || '',
                text: item.text || '',
                icon: item.icon || 'book',
                color_theme: item.color_theme || item.colorTheme || 'blue',
                code_snippet: item.code_snippet || item.codeSnippet || '',
                image_url: item.image_url || item.imageUrl || ''
            };
        });
        return {
            layout_type: layoutType,
            title: slide.title || '',
            content: items
        };
    }

    // ---- Public API ----

    function convertImpl(slideV2, sceneId) {
        var normalized = normalizeSlide(slideV2);
        if (!normalized) {
            console.warn('[SlideV2ToOpenMAICAdapter] Invalid slideV2 input:', slideV2);
            return null;
        }
        if (!normalized.layout_type) {
            normalized.layout_type = 'two-column';
        }
        var templateFn = LAYOUT_TEMPLATES[normalized.layout_type] || LAYOUT_TEMPLATES['two-column'];
        var elements = templateFn(normalized, sceneId || 0);
        var flatElements = [];
        for (var i = 0; i < elements.length; i++) {
            if (Array.isArray(elements[i])) {
                for (var j = 0; j < elements[i].length; j++) {
                    flatElements.push(elements[i][j]);
                }
            } else {
                flatElements.push(elements[i]);
            }
        }
        elements = flatElements.filter(function(el) { return validateElement(el); });
        if (elements.length === 0) {
            console.warn('[SlideV2ToOpenMAICAdapter] No valid elements generated for sceneId=' + sceneId);
            return null;
        }
        var themeColors = [];
        var seenColors = {};
        (normalized.content || []).forEach(function(item) {
            var ct = item.color_theme || 'blue';
            if (!seenColors[ct]) {
                seenColors[ct] = true;
                themeColors.push((THEME_COLORS[ct] || THEME_COLORS.blue).accent);
            }
        });
        return {
            id: 'slide-v2-' + sceneId,
            viewportSize: { width: VIEWPORT_W, height: VIEWPORT_H },
            viewportRatio: VIEWPORT_H / VIEWPORT_W,
            elements: elements,
            background: { type: 'solid', color: '#F8FAFC' },
            theme: {
                themeColors: themeColors.length > 0 ? themeColors : ['#1E40AF', '#DBEAFE', '#FEF3C7', '#D1FAE5'],
                fontColor: '#1E293B',
                backgroundColor: '#F8FAFC',
                fontName: 'Microsoft YaHei'
            },
            remark: ''
        };
    }

    function convert(slideV2, sceneId) {
        try {
            return convertImpl(slideV2, sceneId);
        } catch (err) {
            console.warn('[SlideV2ToOpenMAICAdapter] Conversion failed, returning null:', err.message);
            return null;
        }
    }

    function convertDeck(slidesV2) {
        if (!Array.isArray(slidesV2) || slidesV2.length === 0) return null;
        try {
            var slides = slidesV2.map(function(s, i) {
                return convert(s, i);
            }).filter(function(s) { return s !== null; });
            if (slides.length === 0) return null;
            return { slides: slides, currentIndex: 0 };
        } catch (err) {
            console.warn('[SlideV2ToOpenMAICAdapter] convertDeck failed:', err.message);
            return null;
        }
    }

    window.SlideV2ToOpenMAICAdapter = {
        VIEWPORT_W: VIEWPORT_W,
        VIEWPORT_H: VIEWPORT_H,
        convert: convert,
        convertDeck: convertDeck
    };
})();
