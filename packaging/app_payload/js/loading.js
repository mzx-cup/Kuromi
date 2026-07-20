/**
 * Global Loading System
 * Three-layer architecture:
 *   Layer 1 - State control: isLoading flag + preload queue
 *   Layer 2 - 3D CSS Spinner: dual pseudo-element rotation
 *   Layer 3 - Fade-out: opacity transition on complete
 */

(function () {
  'use strict';

  const TIMEOUT_MS = 2500;
  const FINISH_DELAY_MS = 500;
  const FADE_DURATION_MS = 800;
  // Hard upper bound: overlay MUST die even if transitionend never fires.
  const HARD_KILL_MS = 6000;
  // Fallback in case transitionend never fires (e.g. display:none parent).
  const TRANSITION_FALLBACK_MS = 2000;

  let isLoading = true;
  let overlayEl = null;
  let spinnerEl = null;
  let _hardKillTimer = null;

  function createOverlay() {
    if (document.querySelector('.loading-overlay')) return;

    overlayEl = document.createElement('div');
    overlayEl.className = 'loading-overlay';
    overlayEl.innerHTML = `
      <div class="loading-spinner"></div>
      <p class="loading-text">LOADING</p>
    `;
    document.body.prepend(overlayEl);
    spinnerEl = overlayEl.querySelector('.loading-spinner');
  }

  function collectImages() {
    const urls = [];
    // All <img> elements already in DOM
    document.querySelectorAll('img[src]').forEach(function (img) {
      if (img.src && !img.src.startsWith('data:')) urls.push(img.src);
    });
    // Background wallpaper image (CSS custom property)
    var bg = getComputedStyle(document.documentElement).getPropertyValue('--leleo-bg-image');
    if (bg && bg !== 'none') {
      var match = bg.match(/url\(["']?([^"')]+)["']?\)/);
      if (match) urls.push(match[1]);
    }
    // Background wallpaper video (CSS custom property)
    var bgVideo = getComputedStyle(document.documentElement).getPropertyValue('--leleo-bg-video');
    if (bgVideo && bgVideo !== 'none') {
      var match2 = bgVideo.match(/url\(["']?([^"')]+)["']?\)/);
      if (match2) urls.push(match2[1]);
    }
    // User avatar
    var avatar = document.querySelector('.user-avatar');
    if (avatar && avatar.src && !avatar.src.startsWith('data:')) {
      urls.push(avatar.src);
    }
    // Global background video element
    var videoEl = document.getElementById('global-bg-video');
    if (videoEl && videoEl.src && !videoEl.src.startsWith('data:')) {
      urls.push(videoEl.src);
    }
    return urls;
  }

  function preloadImages() {
    var urls = collectImages();
    if (urls.length === 0) return Promise.resolve();

    var loads = urls.map(function (url) {
      return new Promise(function (resolve) {
        var img = new Image();
        img.onload = function () { resolve(); };
        img.onerror = function () { resolve(); }; // Don't block on errors
        img.src = url;
      });
    });

    // Race: all images loaded OR timeout
    return Promise.race([
      Promise.all(loads),
      new Promise(function (resolve) { setTimeout(resolve, TIMEOUT_MS); })
    ]);
  }

  function _forceRemoveOverlay() {
    try {
      var el = document.querySelector('.loading-overlay');
      if (el && el.parentNode) el.parentNode.removeChild(el);
    } catch (e) { /* swallow */ }
    overlayEl = null;
    spinnerEl = null;
    isLoading = false;
    if (_hardKillTimer) {
      clearTimeout(_hardKillTimer);
      _hardKillTimer = null;
    }
  }

  function finish() {
    if (!overlayEl) {
      // Defensive: also remove any orphan overlay in DOM.
      _forceRemoveOverlay();
      return;
    }

    try {
      // Star dive animation
      if (spinnerEl) {
        spinnerEl.classList.add('star-dive');
      }

      // Hard kill — last-resort safety net.
      if (_hardKillTimer) clearTimeout(_hardKillTimer);
      _hardKillTimer = setTimeout(_forceRemoveOverlay, HARD_KILL_MS);

      // Wait for dive animation, then fade out overlay
      setTimeout(function () {
        var ov = overlayEl;
        if (!ov) { _forceRemoveOverlay(); return; }
        ov.classList.add('fade-out');

        var removed = false;
        var onEnd = function (ev) {
          if (ev && ev.target !== ov) return;
          if (removed) return;
          removed = true;
          try { ov.removeEventListener('transitionend', onEnd); } catch (e) {}
          if (ov.parentNode) ov.parentNode.removeChild(ov);
          overlayEl = null;
          spinnerEl = null;
          isLoading = false;
          if (_hardKillTimer) { clearTimeout(_hardKillTimer); _hardKillTimer = null; }
        };
        ov.addEventListener('transitionend', onEnd);

        // Fallback if transitionend never fires.
        setTimeout(onEnd, TRANSITION_FALLBACK_MS);
      }, 700); // star dive duration
    } catch (err) {
      // Last-resort: never let finish() throw.
      console.error('[loading] finish() error', err);
      _forceRemoveOverlay();
    }
  }

  function showSimple() {
    try {
      // Re-show the overlay with simple spinner (no star dive on finish)
      createOverlay();
      if (spinnerEl) spinnerEl.classList.add('simple');
      if (overlayEl) overlayEl.classList.remove('fade-out');
      isLoading = true;

      // Hard kill in case transitionend never fires.
      if (_hardKillTimer) clearTimeout(_hardKillTimer);
      _hardKillTimer = setTimeout(_forceRemoveOverlay, HARD_KILL_MS);

      // Auto-hide after a brief delay
      setTimeout(function () {
        isLoading = false;
        if (overlayEl) {
          overlayEl.classList.add('fade-out');
          var ov = overlayEl;
          var removed = false;
          var handler = function () {
            if (removed) return;
            removed = true;
            try { ov.removeEventListener('transitionend', handler); } catch (e) {}
            if (ov.parentNode) ov.parentNode.removeChild(ov);
            overlayEl = null;
            spinnerEl = null;
          };
          ov.addEventListener('transitionend', handler);
          setTimeout(handler, TRANSITION_FALLBACK_MS);
        }
      }, 600);
    } catch (err) {
      console.error('[loading] showSimple() error', err);
      _forceRemoveOverlay();
    }
  }

  function finishSimple() {
    try {
      if (!overlayEl) { _forceRemoveOverlay(); return; }
      // Hard kill in case transitionend never fires.
      if (_hardKillTimer) clearTimeout(_hardKillTimer);
      _hardKillTimer = setTimeout(_forceRemoveOverlay, HARD_KILL_MS);

      overlayEl.classList.add('fade-out');
      var ov = overlayEl;
      var removed = false;
      var handler = function () {
        if (removed) return;
        removed = true;
        try { ov.removeEventListener('transitionend', handler); } catch (e) {}
        if (ov.parentNode) ov.parentNode.removeChild(ov);
        overlayEl = null;
        spinnerEl = null;
      };
      ov.addEventListener('transitionend', handler);
      setTimeout(handler, TRANSITION_FALLBACK_MS);
    } catch (err) {
      console.error('[loading] finishSimple() error', err);
      _forceRemoveOverlay();
    }
  }

  function init() {
    // Don't show loading if page is already loaded (BFCache)
    if (document.readyState === 'complete') {
      isLoading = false;
      return;
    }

    createOverlay();

    preloadImages().then(function () {
      return new Promise(function (resolve) { setTimeout(resolve, FINISH_DELAY_MS); });
    }).then(function () {
      isLoading = false;
      finish();
    });
  }

  // Start loading
  try {
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', init);
    } else {
      init();
    }
  } catch (err) {
    console.error('[loading] init() failed; removing overlay', err);
    _forceRemoveOverlay();
  }

  // Expose for external use
  window.LoadingSystem = {
    get isLoading() { return isLoading; },
    finish: finish,
    showSimple: showSimple,
    finishSimple: finishSimple
  };
})();
