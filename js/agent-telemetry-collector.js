// js/agent-telemetry-collector.js
// 滚动/停留/鼠标 → POST /api/telemetry 每 10s 批量
// 用于 portrait_aggregator 推导情绪状态(frustrated/anxious/engaged/calm)
//
// 用法:
//   agentTelemetry.start('user_123');
//   // ...
//   agentTelemetry.stop();
(function (global) {
  const BATCH_INTERVAL_MS = 10000;
  const buffer = [];
  let studentId = null;
  let timer = null;
  let idleInterval = null;

  function setStudentId(id) { studentId = id; }

  function push(event) { buffer.push(event); }

  function recordScroll() {
    if (typeof window === 'undefined') return;
    let lastY = window.scrollY;
    let lastT = Date.now();
    window.addEventListener('scroll', () => {
      const now = Date.now();
      const dy = Math.abs(window.scrollY - lastY);
      const dt = (now - lastT) / 1000;
      if (dt > 0) {
        const depth = document.body.scrollHeight > 0
          ? window.scrollY / document.body.scrollHeight
          : 0;
        push({
          type: 'scroll',
          metrics: { speed: dy / dt, depth },
          ts: now,
        });
      }
      lastY = window.scrollY;
      lastT = now;
    }, { passive: true });
  }

  function recordZoneDwell() {
    if (typeof document === 'undefined') return;
    document.addEventListener('mouseover', (e) => {
      const zone = e.target && e.target.closest ? e.target.closest('[data-zone]') : null;
      if (!zone) return;
      const start = Date.now();
      const off = () => {
        push({
          type: 'zone_dwell',
          zone: zone.dataset.zone,
          ms: Date.now() - start,
          ts: Date.now(),
        });
        zone.removeEventListener('mouseleave', off);
      };
      zone.addEventListener('mouseleave', off);
    });
  }

  function recordMouseIdle() {
    if (typeof window === 'undefined') return;
    let lastMove = Date.now();
    window.addEventListener('mousemove', () => { lastMove = Date.now(); });
    idleInterval = setInterval(() => {
      push({
        type: 'mouse',
        metrics: { idle_ms: Date.now() - lastMove, movement_count: 0 },
        ts: Date.now(),
      });
    }, BATCH_INTERVAL_MS);
  }

  async function flush() {
    if (!buffer.length || !studentId) return;
    const batch = buffer.splice(0, buffer.length);
    try {
      const r = await fetch('/api/telemetry', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ student_id: studentId, batch }),
      });
      if (!r.ok) console.warn('[telemetry] flush non-2xx', r.status);
    } catch (e) {
      console.warn('[telemetry] flush failed', e);
    }
  }

  function start(id) {
    setStudentId(id);
    recordScroll();
    recordZoneDwell();
    recordMouseIdle();
    if (timer) clearInterval(timer);
    timer = setInterval(flush, BATCH_INTERVAL_MS);
  }

  function stop() {
    if (timer) { clearInterval(timer); timer = null; }
    if (idleInterval) { clearInterval(idleInterval); idleInterval = null; }
  }

  const api = { start, stop, flush, push, setStudentId, BATCH_INTERVAL_MS };

  if (typeof window !== 'undefined') {
    global.agentTelemetry = api;
  }
  if (typeof module !== 'undefined' && module.exports) {
    module.exports = api;
  }
})(typeof window !== 'undefined' ? window : globalThis);
