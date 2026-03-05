/**
 * 木鱼模块 — 敲击积功德
 */
var Woodfish = (function () {
  'use strict';

  var STORAGE_KEY_MERIT = 'fortune_merit';
  var STORAGE_KEY_TOTAL = 'fortune_wf_total';

  var merit = 0;
  var totalCount = 0;
  var todayCount = 0;
  var audioCtx = null;

  function init() {
    merit = parseInt(localStorage.getItem(STORAGE_KEY_MERIT) || '0', 10);
    totalCount = parseInt(localStorage.getItem(STORAGE_KEY_TOTAL) || '0', 10);
    todayCount = 0;
    _updateUI();

    var btn = document.getElementById('wf-btn');
    if (!btn) return;
    btn.addEventListener('click', _hit);
    btn.addEventListener('touchstart', function (e) {
      e.preventDefault();
      _hit();
    }, { passive: false });
  }

  function refresh() {
    _updateUI();
  }

  function _hit() {
    merit += 1;
    totalCount += 1;
    todayCount += 1;

    localStorage.setItem(STORAGE_KEY_MERIT, String(merit));
    localStorage.setItem(STORAGE_KEY_TOTAL, String(totalCount));

    _updateUI();
    _animateHit();
    _floatText();
    _playSound();
    _haptic();
  }

  function _updateUI() {
    var elMerit = document.getElementById('wf-merit');
    var elToday = document.getElementById('wf-today');
    var elTotal = document.getElementById('wf-total');
    if (elMerit) elMerit.textContent = merit;
    if (elToday) elToday.textContent = todayCount;
    if (elTotal) elTotal.textContent = totalCount;
  }

  function _animateHit() {
    var btn = document.getElementById('wf-btn');
    if (!btn) return;
    btn.classList.add('hit');
    setTimeout(function () { btn.classList.remove('hit'); }, 80);

    var ripple = document.getElementById('wf-ripple');
    if (ripple) {
      ripple.classList.remove('active');
      void ripple.offsetWidth;
      ripple.classList.add('active');
    }
  }

  function _floatText() {
    var container = document.getElementById('wf-floats');
    if (!container) return;
    var el = document.createElement('div');
    el.className = 'wf-float';
    el.textContent = '功德 +1';
    el.style.left = (50 + (Math.random() - 0.5) * 30) + '%';
    container.appendChild(el);
    setTimeout(function () { el.remove(); }, 1000);
  }

  function _playSound() {
    try {
      if (!audioCtx) {
        audioCtx = new (window.AudioContext || window.webkitAudioContext)();
      }
      var ctx = audioCtx;
      if (ctx.state === 'suspended') ctx.resume();
      var now = ctx.currentTime;

      var o1 = ctx.createOscillator();
      var g1 = ctx.createGain();
      o1.type = 'sine';
      o1.frequency.setValueAtTime(150, now);
      g1.gain.setValueAtTime(0.3, now);
      g1.gain.exponentialRampToValueAtTime(0.001, now + 0.25);
      o1.connect(g1);
      g1.connect(ctx.destination);
      o1.start(now);
      o1.stop(now + 0.25);

      var o2 = ctx.createOscillator();
      var g2 = ctx.createGain();
      o2.type = 'sine';
      o2.frequency.setValueAtTime(100, now + 0.02);
      g2.gain.setValueAtTime(0.2, now + 0.02);
      g2.gain.exponentialRampToValueAtTime(0.001, now + 0.4);
      o2.connect(g2);
      g2.connect(ctx.destination);
      o2.start(now + 0.02);
      o2.stop(now + 0.4);
    } catch (_) {}
  }

  function _haptic() {
    if (navigator.vibrate) {
      navigator.vibrate(30);
    }
  }

  return {
    init: init,
    refresh: refresh,
  };
})();
