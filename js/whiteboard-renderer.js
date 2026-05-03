/**
 * WhiteboardRenderer — SVG 白板渲染器
 *
 * 支持: SVG图形、文本、LaTeX公式(KaTeX)、图表(Chart.js)、代码高亮
 * 移植自 OpenMAIC 的 ActionEngine 白板执行逻辑。
 */

class WhiteboardRenderer {
  /**
   * @param {Object} options
   * @param {string} options.containerId - 白板容器元素 ID
   * @param {number} options.width - 白板宽度 (默认 800)
   * @param {number} options.height - 白板高度 (默认 600)
   */
  constructor(options = {}) {
    this.containerId = options.containerId || 'whiteboard-container';
    this.width = options.width || 800;
    this.height = options.height || 600;
    this.elements = new Map(); // elementId -> DOM element

    /** @type {SVGSVGElement|null} */
    this.svgRoot = null;
    this._initContainer();
  }

  // ---- 初始化 ----

  _initContainer() {
    let container = document.getElementById(this.containerId);
    if (!container) {
      container = document.createElement('div');
      container.id = this.containerId;
      container.style.cssText = 'position:relative;overflow:hidden;background:#fff;border-radius:8px;';
      document.body.appendChild(container);
    }
    container.style.width = this.width + 'px';
    container.style.height = this.height + 'px';
    container.innerHTML = '';

    // SVG 层
    const svgNS = 'http://www.w3.org/2000/svg';
    const svg = document.createElementNS(svgNS, 'svg');
    svg.setAttribute('width', this.width);
    svg.setAttribute('height', this.height);
    svg.setAttribute('viewBox', `0 0 ${this.width} ${this.height}`);
    svg.style.cssText = 'position:absolute;top:0;left:0;width:100%;height:100%;';
    container.appendChild(svg);
    this.svgRoot = svg;
  }

  // ---- Action 分发 ----

  /**
   * 执行白板 Action
   * @param {Object} action - { type, params }
   */
  execute(action) {
    const name = action.type || action.name;
    const params = action.params || {};

    switch (name) {
      case 'wb_open':      this.open(); break;
      case 'wb_close':     this.close(); break;
      case 'wb_clear':     this.clear(); break;
      case 'wb_delete':    this.delete(params.elementId); break;
      case 'wb_draw_text':  this.drawText(params); break;
      case 'wb_draw_shape': this.drawShape(params); break;
      case 'wb_draw_svg':   this.drawSVG(params); break;
      case 'wb_draw_latex': this.drawLatex(params); break;
      case 'wb_draw_chart': this.drawChart(params); break;
      case 'wb_draw_table': this.drawTable(params); break;
      case 'wb_draw_line':  this.drawLine(params); break;
      case 'wb_draw_code':  this.drawCode(params); break;
      default:
        console.warn('[Whiteboard] Unknown action:', name);
    }
  }

  // ---- 基础操作 ----

  open() {
    const container = document.getElementById(this.containerId);
    if (container) {
      container.style.display = 'block';
      container.style.opacity = '1';
    }
  }

  close() {
    const container = document.getElementById(this.containerId);
    if (container) {
      container.style.opacity = '0';
      setTimeout(() => { container.style.display = 'none'; }, 300);
    }
  }

  clear() {
    this.elements.clear();
    this._initContainer();
  }

  delete(elementId) {
    if (!elementId) return;
    const el = this.elements.get(elementId);
    if (el) {
      el.remove();
      this.elements.delete(elementId);
    }
  }

  // ---- 绘制方法 ----

  drawText(params) {
    const { content, x = 100, y = 100, fontSize = 20, color = '#333333', elementId } = params;
    const textEl = document.createElementNS('http://www.w3.org/2000/svg', 'text');
    textEl.setAttribute('x', x);
    textEl.setAttribute('y', y);
    textEl.setAttribute('font-size', fontSize);
    textEl.setAttribute('fill', color);
    textEl.setAttribute('font-family', 'system-ui, sans-serif');
    textEl.textContent = content;
    this.svgRoot.appendChild(textEl);
    if (elementId) this.elements.set(elementId, textEl);
  }

  drawShape(params) {
    const { shape, x = 100, y = 100, width = 100, height = 100, fillColor, strokeColor = '#333', elementId } = params;
    const svgNS = 'http://www.w3.org/2000/svg';
    let shapeEl;

    switch (shape) {
      case 'rectangle':
      case 'rect':
        shapeEl = document.createElementNS(svgNS, 'rect');
        shapeEl.setAttribute('x', x);
        shapeEl.setAttribute('y', y);
        shapeEl.setAttribute('width', width);
        shapeEl.setAttribute('height', height);
        break;
      case 'circle':
        shapeEl = document.createElementNS(svgNS, 'circle');
        shapeEl.setAttribute('cx', x + width / 2);
        shapeEl.setAttribute('cy', y + height / 2);
        shapeEl.setAttribute('r', Math.min(width, height) / 2);
        break;
      case 'triangle':
        shapeEl = document.createElementNS(svgNS, 'polygon');
        shapeEl.setAttribute('points', `${x + width / 2},${y} ${x + width},${y + height} ${x},${y + height}`);
        break;
      default:
        shapeEl = document.createElementNS(svgNS, 'rect');
        shapeEl.setAttribute('x', x);
        shapeEl.setAttribute('y', y);
        shapeEl.setAttribute('width', width);
        shapeEl.setAttribute('height', height);
    }

    shapeEl.setAttribute('fill', fillColor || 'rgba(37, 99, 235, 0.1)');
    shapeEl.setAttribute('stroke', strokeColor);
    shapeEl.setAttribute('stroke-width', '2');
    this.svgRoot.appendChild(shapeEl);
    if (elementId) this.elements.set(elementId, shapeEl);
  }

  /**
   * 绘制SVG图形 — 带一笔一划渐进动画
   *
   * 对SVG中所有带stroke的元素，使用CSS stroke-dashoffset动画
   * 模拟"手绘"效果。fill元素先隐藏，描边完成后再显示填充。
   */
  drawSVG(params) {
    const { svg, x = 100, y = 100, width = 400, height = 300, elementId } = params;
    if (!svg) return;

    const container = document.createElementNS('http://www.w3.org/2000/svg', 'g');
    container.setAttribute('transform', `translate(${x}, ${y})`);

    // 直接解析SVG字符串并插入
    // 注意：innerHTML 在 SVG 中可用但不规范，这里使用 DOMParser 解析
    const parser = new DOMParser();
    const svgDoc = parser.parseFromString(
      `<svg xmlns="http://www.w3.org/2000/svg">${svg}</svg>`,
      'image/svg+xml'
    );
    const children = svgDoc.documentElement.children;

    // 收集所有带stroke的元素用于动画
    const strokeElements = [];
    const allElements = [];

    for (const child of children) {
      const imported = this.svgRoot.ownerDocument.importNode(child, true);
      container.appendChild(imported);
      allElements.push(imported);

      // 检测是否有 stroke 属性
      const stroke = child.getAttribute('stroke');
      const strokeWidth = child.getAttribute('stroke-width');
      if (stroke && stroke !== 'none' && strokeWidth && strokeWidth !== '0') {
        strokeElements.push(imported);
      }
    }

    this.svgRoot.appendChild(container);
    if (elementId) this.elements.set(elementId, container);

    // 启动一笔一划动画
    if (strokeElements.length > 0) {
      this._animateStrokeByStroke(strokeElements, allElements, container);
    }
  }

  /**
   * 一笔一划绘制动画
   *
   * 使用 CSS transition + stroke-dashoffset 模拟逐笔绘制：
   * 1. 获取每个 stroke 元素的总路径长度
   * 2. 设置 stroke-dasharray = 路径总长, stroke-dashoffset = 路径总长 (不可见)
   * 3. 逐个将 stroke-dashoffset 过渡到 0 (绘制完成)
   */
  _animateStrokeByStroke(strokeElements, allElements, container) {
    const DRAW_SPEED = 300; // 每笔绘制速度(ms) — 快速但可见

    // 首先隐藏所有 fill
    allElements.forEach(el => {
      const fill = el.getAttribute('fill') || '';
      const tag = el.tagName.toLowerCase();
      if (fill && fill !== 'none' && tag !== 'text') {
        el.setAttribute('data-original-fill', fill);
        el.setAttribute('fill', 'transparent');
      }
      // 文字元素先隐藏
      if (tag === 'text' && el.getAttribute('fill') !== 'transparent') {
        el.setAttribute('data-original-opacity', '1');
        el.setAttribute('opacity', '0');
      }
    });

    // 逐个绘制stroke元素
    let delay = 0;
    strokeElements.forEach((el, index) => {
      setTimeout(() => {
        this._drawSingleStroke(el);
      }, delay);

      // 估算该元素的绘制时间
      const pathLen = this._getPathLength(el);
      delay += Math.max(100, pathLen * 0.3); // ~0.3ms/单位长度
    });

    // 所有stroke绘制完成后，显示fill和文字
    setTimeout(() => {
      allElements.forEach(el => {
        const origFill = el.getAttribute('data-original-fill');
        if (origFill) {
          el.setAttribute('fill', origFill);
        }
        const origOpacity = el.getAttribute('data-original-opacity');
        if (origOpacity) {
          el.setAttribute('opacity', origOpacity);
          el.removeAttribute('data-original-opacity');
        }
        el.removeAttribute('data-original-fill');
      });
    }, delay + 200);
  }

  /** 对单个stroke元素应用绘制动画 */
  _drawSingleStroke(el) {
    const pathLen = this._getPathLength(el);
    if (pathLen === 0) return;

    // 使用CSS transition实现平滑描边
    el.style.strokeDasharray = pathLen;
    el.style.strokeDashoffset = pathLen;
    el.style.transition = `stroke-dashoffset ${pathLen * 0.3}ms linear`;

    // 触发动画
    requestAnimationFrame(() => {
      el.style.strokeDashoffset = '0';
    });
  }

  /** 获取元素的近似路径长度（用于动画） */
  _getPathLength(el) {
    try {
      // 对于 line/rect/circle/polygon 等无法直接获取长度的元素，估算
      const tag = el.tagName.toLowerCase();
      if (tag === 'line') {
        const x1 = parseFloat(el.getAttribute('x1') || 0);
        const y1 = parseFloat(el.getAttribute('y1') || 0);
        const x2 = parseFloat(el.getAttribute('x2') || 0);
        const y2 = parseFloat(el.getAttribute('y2') || 0);
        return Math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2);
      }
      if (tag === 'rect') {
        const w = parseFloat(el.getAttribute('width') || 0);
        const h = parseFloat(el.getAttribute('height') || 0);
        return (w + h) * 2;
      }
      if (tag === 'circle' || tag === 'ellipse') {
        const r = parseFloat(el.getAttribute('r') || 30);
        return 2 * Math.PI * r;
      }
      if (tag === 'polygon' || tag === 'polyline') {
        // 估算为周长
        const points = (el.getAttribute('points') || '').trim().split(/\s+/);
        return points.length * 20;
      }
      // path 或其他：估算值
      return 200;
    } catch {
      return 200;
    }
  }

  drawLatex(params) {
    const { latex, x = 100, y = 100, width = 400, color = '#333', elementId } = params;
    if (!latex) return;

    const foreign = document.createElementNS('http://www.w3.org/2000/svg', 'foreignObject');
    foreign.setAttribute('x', x);
    foreign.setAttribute('y', y);
    foreign.setAttribute('width', width);
    foreign.setAttribute('height', 100);

    const div = document.createElement('div');
    div.style.color = color;
    div.style.fontSize = '18px';

    // 使用 KaTeX 渲染（如果可用）
    if (typeof katex !== 'undefined') {
      try {
        katex.render(latex, div, { throwOnError: false, displayMode: true });
      } catch {
        div.textContent = latex;
      }
    } else {
      div.textContent = latex;
    }

    foreign.appendChild(div);
    this.svgRoot.appendChild(foreign);
    if (elementId) this.elements.set(elementId, foreign);
  }

  drawChart(params) {
    const { chartType = 'bar', data, x = 100, y = 100, width = 400, height = 300, elementId } = params;
    if (!data) return;

    // 使用简单的 SVG 柱状图（无需 Chart.js 依赖）
    const g = document.createElementNS('http://www.w3.org/2000/svg', 'g');
    g.setAttribute('transform', `translate(${x}, ${y})`);

    const { labels = [], legends = [], series = [[]] } = data;
    const values = series[0] || [];
    const maxVal = Math.max(...values, 1);
    const barWidth = width / values.length * 0.7;
    const gap = width / values.length * 0.3;

    // Y axis
    const yAxis = document.createElementNS('http://www.w3.org/2000/svg', 'line');
    yAxis.setAttribute('x1', '0'); yAxis.setAttribute('y1', '0');
    yAxis.setAttribute('x2', '0'); yAxis.setAttribute('y2', height);
    yAxis.setAttribute('stroke', '#ccc'); yAxis.setAttribute('stroke-width', '2');
    g.appendChild(yAxis);

    // X axis
    const xAxis = document.createElementNS('http://www.w3.org/2000/svg', 'line');
    xAxis.setAttribute('x1', '0'); xAxis.setAttribute('y1', height);
    xAxis.setAttribute('x2', width); xAxis.setAttribute('y2', height);
    xAxis.setAttribute('stroke', '#ccc'); xAxis.setAttribute('stroke-width', '2');
    g.appendChild(xAxis);

    // Bars
    const colors = ['#2563eb', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899'];
    for (let i = 0; i < values.length; i++) {
      const barHeight = (values[i] / maxVal) * (height - 30);
      const bar = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
      bar.setAttribute('x', i * (barWidth + gap) + gap / 2);
      bar.setAttribute('y', height - barHeight);
      bar.setAttribute('width', barWidth);
      bar.setAttribute('height', barHeight);
      bar.setAttribute('fill', colors[i % colors.length]);
      bar.setAttribute('rx', '2');
      g.appendChild(bar);

      // Label
      if (labels[i]) {
        const label = document.createElementNS('http://www.w3.org/2000/svg', 'text');
        label.setAttribute('x', i * (barWidth + gap) + gap / 2 + barWidth / 2);
        label.setAttribute('y', height + 18);
        label.setAttribute('text-anchor', 'middle');
        label.setAttribute('font-size', '11');
        label.setAttribute('fill', '#666');
        label.textContent = labels[i];
        g.appendChild(label);
      }
    }

    this.svgRoot.appendChild(g);
    if (elementId) this.elements.set(elementId, g);
  }

  drawTable(params) {
    const { data: tableData, x = 100, y = 100, width = 500, height = 300, elementId } = params;
    if (!tableData || tableData.length === 0) return;

    const g = document.createElementNS('http://www.w3.org/2000/svg', 'g');
    g.setAttribute('transform', `translate(${x}, ${y})`);

    const rows = tableData.length;
    const cols = tableData[0]?.length || 0;
    const rowH = height / rows;
    const colW = width / cols;

    for (let i = 0; i < rows; i++) {
      for (let j = 0; j < (tableData[i]?.length || 0); j++) {
        const isHeader = i === 0;
        const rect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
        rect.setAttribute('x', j * colW);
        rect.setAttribute('y', i * rowH);
        rect.setAttribute('width', colW);
        rect.setAttribute('height', rowH);
        rect.setAttribute('fill', isHeader ? '#e8f0fe' : '#fff');
        rect.setAttribute('stroke', '#d0d0d0');
        rect.setAttribute('stroke-width', '1');
        g.appendChild(rect);

        const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
        text.setAttribute('x', j * colW + colW / 2);
        text.setAttribute('y', i * rowH + rowH / 2 + 5);
        text.setAttribute('text-anchor', 'middle');
        text.setAttribute('font-size', isHeader ? '14' : '13');
        text.setAttribute('font-weight', isHeader ? 'bold' : 'normal');
        text.setAttribute('fill', '#333');
        text.setAttribute('font-family', 'system-ui, sans-serif');
        text.textContent = String(tableData[i][j] ?? '');
        g.appendChild(text);
      }
    }

    this.svgRoot.appendChild(g);
    if (elementId) this.elements.set(elementId, g);
  }

  drawLine(params) {
    const { startX, startY, endX, endY, color = '#333', width: lineWidth = 2, style: lineStyle = 'solid', points = [], elementId } = params;
    const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
    line.setAttribute('x1', startX);
    line.setAttribute('y1', startY);
    line.setAttribute('x2', endX);
    line.setAttribute('y2', endY);
    line.setAttribute('stroke', color);
    line.setAttribute('stroke-width', lineWidth);
    if (lineStyle === 'dashed') line.setAttribute('stroke-dasharray', '5,5');

    // Arrow markers
    if (points.length === 2 && points[1] === 'arrow') {
      const markerId = 'arrow-' + Date.now();
      const defs = this.svgRoot.querySelector('defs') || (() => {
        const d = document.createElementNS('http://www.w3.org/2000/svg', 'defs');
        this.svgRoot.insertBefore(d, this.svgRoot.firstChild);
        return d;
      })();
      const marker = document.createElementNS('http://www.w3.org/2000/svg', 'marker');
      marker.setAttribute('id', markerId);
      marker.setAttribute('markerWidth', '10');
      marker.setAttribute('markerHeight', '7');
      marker.setAttribute('refX', '10');
      marker.setAttribute('refY', '3.5');
      marker.setAttribute('orient', 'auto');
      marker.innerHTML = '<polygon points="0 0, 10 3.5, 0 7" fill="' + color + '"/>';
      defs.appendChild(marker);
      line.setAttribute('marker-end', `url(#${markerId})`);
    }

    this.svgRoot.appendChild(line);
    if (elementId) this.elements.set(elementId, line);
  }

  drawCode(params) {
    const { language = '', code = '', x = 100, y = 100, width = 500, height = 300, fileName = '', elementId } = params;
    if (!code) return;

    const foreign = document.createElementNS('http://www.w3.org/2000/svg', 'foreignObject');
    foreign.setAttribute('x', x);
    foreign.setAttribute('y', y);
    foreign.setAttribute('width', width);
    foreign.setAttribute('height', height);

    const div = document.createElement('div');
    div.style.cssText = 'background:#1e293b;color:#e2e8f0;border-radius:8px;overflow:hidden;font-family:monospace;font-size:13px;width:100%;height:100%;';

    // Header bar
    const header = document.createElement('div');
    header.style.cssText = 'background:#0f172a;padding:6px 12px;display:flex;align-items:center;gap:8px;height:32px;';
    header.innerHTML = `<span style="color:#94a3b8;font-size:11px;">${fileName || language || 'code'}</span><span style="color:#64748b;font-size:10px;">${language || ''}</span>`;
    div.appendChild(header);

    // Code content
    const pre = document.createElement('pre');
    pre.style.cssText = 'padding:12px;margin:0;overflow:auto;height:calc(100% - 32px);line-height:1.6;';
    pre.textContent = code;
    div.appendChild(pre);

    foreign.appendChild(div);
    this.svgRoot.appendChild(foreign);
    if (elementId) this.elements.set(elementId, foreign);
  }
}

// Browser-compatible global export
if (typeof window !== 'undefined') {
  window.WhiteboardRenderer = WhiteboardRenderer;
}
