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

  let isLoading = true;
  let overlayEl = null;
  let spinnerEl = null;

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

  function finish() {
    if (!overlayEl) return;

    // Step 1: Star dive animation
    if (spinnerEl) {
      spinnerEl.classList.add('star-dive');
    }

    // Step 2: Wait for dive animation, then fade out overlay
    setTimeout(function () {
      overlayEl.classList.add('fade-out');

      // Step 3: Remove overlay after transition
      overlayEl.addEventListener('transitionend', function handler() {
        overlayEl.removeEventListener('transitionend', handler);
        if (overlayEl && overlayEl.parentNode) {
          overlayEl.parentNode.removeChild(overlayEl);
        }
        overlayEl = null;
        spinnerEl = null;
      });
    }, 700); // star dive duration
  }

  function showSimple() {
    // Re-show the overlay with simple spinner (no star dive on finish)
    createOverlay();
    if (spinnerEl) spinnerEl.classList.add('simple');
    if (overlayEl) overlayEl.classList.remove('fade-out');
    isLoading = true;

    // Auto-hide after a brief delay
    setTimeout(function () {
      isLoading = false;
      if (overlayEl) {
        overlayEl.classList.add('fade-out');
        overlayEl.addEventListener('transitionend', function handler() {
          overlayEl.removeEventListener('transitionend', handler);
          if (overlayEl && overlayEl.parentNode) {
            overlayEl.parentNode.removeChild(overlayEl);
          }
          overlayEl = null;
          spinnerEl = null;
        });
      }
    }, 600);
  }

  function finishSimple() {
    // Clean finish without dive animation — for simple spinner
    if (!overlayEl) return;
    overlayEl.classList.add('fade-out');
    overlayEl.addEventListener('transitionend', function handler() {
      overlayEl.removeEventListener('transitionend', handler);
      if (overlayEl && overlayEl.parentNode) {
        overlayEl.parentNode.removeChild(overlayEl);
      }
      overlayEl = null;
      spinnerEl = null;
    });
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
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  // Expose for external use
  window.LoadingSystem = {
    get isLoading() { return isLoading; },
    finish: finish,
    showSimple: showSimple,
    finishSimple: finishSimple
  };
})();
