/**
 * 看板娘 — 3D视差跟随 + 呼吸浮动
 * 用法：页面引入此JS后，放置 .app-kanban 结构即可自动生效
 */

(function() {
  'use strict';

  var kanban = document.querySelector('.app-kanban');
  var img = document.querySelector('.app-kanban-img');
  var closeBtn = document.querySelector('.app-kanban-close');
  if (!kanban || !img) return;

  // 呼吸浮动参数
  var breatheSpeed = 0.0015; // 浮动速度
  var breatheAmp = 10;       // 浮动幅度(px)
  var baseRotateY = 8;       // 基础Y轴旋转角度（面向中间）
  var baseRotateX = -2;      // 基础X轴旋转角度

  // 鼠标视差参数
  var maxMouseRotate = 12;   // 鼠标跟随最大旋转角度

  var mouseX = 0;
  var mouseY = 0;
  var targetRotateY = baseRotateY;
  var targetRotateX = baseRotateX;
  var currentRotateY = baseRotateY;
  var currentRotateX = baseRotateX;

  // 监听鼠标位置
  document.addEventListener('mousemove', function(e) {
    mouseX = e.clientX / window.innerWidth;  // 0 ~ 1
    mouseY = e.clientY / window.innerHeight; // 0 ~ 1
  });

  // 动画循环
  var startTime = Date.now();

  function animate() {
    var now = Date.now();
    var elapsed = now - startTime;

    // 呼吸浮动：正弦波
    var floatY = Math.sin(elapsed * breatheSpeed) * breatheAmp;

    // 鼠标视差目标值
    // 鼠标在左边 → 角色向右侧转（面向鼠标）
    var mouseOffsetX = (mouseX - 0.5) * maxMouseRotate * 2;
    var mouseOffsetY = (mouseY - 0.5) * maxMouseRotate;

    targetRotateY = baseRotateY - mouseOffsetX;
    targetRotateX = baseRotateX + mouseOffsetY;

    // 平滑插值（lerp）
    var lerpFactor = 0.08;
    currentRotateY += (targetRotateY - currentRotateY) * lerpFactor;
    currentRotateX += (targetRotateX - currentRotateX) * lerpFactor;

    // 应用3D变换
    var transform = 'perspective(800px) ' +
      'rotateY(' + currentRotateY.toFixed(2) + 'deg) ' +
      'rotateX(' + currentRotateX.toFixed(2) + 'deg) ' +
      'translateY(' + floatY.toFixed(2) + 'px)';

    img.style.transform = transform;

    requestAnimationFrame(animate);
  }

  requestAnimationFrame(animate);

  // 关闭按钮
  if (closeBtn) {
    closeBtn.addEventListener('click', function(e) {
      e.stopPropagation();
      kanban.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
      kanban.style.opacity = '0';
      kanban.style.transform = 'scale(0.8)';
      setTimeout(function() {
        kanban.style.display = 'none';
      }, 300);
    });
  }

  // 点击看板娘时的微反馈
  img.addEventListener('click', function() {
    img.style.transition = 'transform 0.15s ease';
    var current = img.style.transform;
    img.style.transform = current + ' scale(0.97)';
    setTimeout(function() {
      img.style.transition = 'transform 0.3s var(--ease-out)';
    }, 150);
  });

})();
