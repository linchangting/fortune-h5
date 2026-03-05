/**
 * 工具函数 + localStorage 持久化管理
 */
var FortuneUtils = (function () {
  'use strict';

  var KEYS = {
    USER: 'fortune_user',
    HISTORY: 'fortune_history',
    DISCLAIMER: 'fortune_disclaimer',
  };

  function $(sel) { return document.querySelector(sel); }
  function $$(sel) { return Array.prototype.slice.call(document.querySelectorAll(sel)); }

  // ── localStorage 封装 ──

  function saveUser(data) {
    try { localStorage.setItem(KEYS.USER, JSON.stringify(data)); } catch (e) {}
  }

  function getUser() {
    try { return JSON.parse(localStorage.getItem(KEYS.USER)); } catch (e) { return null; }
  }

  function saveHistory(date, result) {
    try {
      var history = getHistory();
      history[date] = result;
      var keys = Object.keys(history).sort().reverse();
      if (keys.length > 30) {
        keys.slice(30).forEach(function (k) { delete history[k]; });
      }
      localStorage.setItem(KEYS.HISTORY, JSON.stringify(history));
    } catch (e) {}
  }

  function getHistory() {
    try { return JSON.parse(localStorage.getItem(KEYS.HISTORY)) || {}; } catch (e) { return {}; }
  }

  function getTodayCache() {
    var today = new Date().toISOString().slice(0, 10);
    var h = getHistory();
    return h[today] || null;
  }

  function setDisclaimer(val) {
    try { localStorage.setItem(KEYS.DISCLAIMER, val ? '1' : ''); } catch (e) {}
  }

  function getDisclaimer() {
    try { return localStorage.getItem(KEYS.DISCLAIMER) === '1'; } catch (e) { return false; }
  }

  // ── 格式化 ──

  function scoreToStars(score) {
    var full = Math.round(score / 20);
    full = Math.max(1, Math.min(5, full));
    var html = '';
    for (var i = 0; i < 5; i++) {
      html += i < full
        ? '<span class="star-full">★</span>'
        : '<span class="star-empty">☆</span>';
    }
    return html;
  }

  function today() {
    return new Date().toISOString().slice(0, 10);
  }

  var COLOR_MAP = {
    '红色': '#C41E3A', '紫色': '#8B3A8B', '绿色': '#5BA85A',
    '青色': '#2E8B57', '黄色': '#D4A84B', '棕色': '#8B6914',
    '白色': '#E8E8E8', '金色': '#D4A84B', '黑色': '#333',
    '蓝色': '#4A90C4',
  };

  function colorToHex(name) {
    return COLOR_MAP[name] || '#999';
  }

  return {
    $: $, $$: $$,
    saveUser: saveUser, getUser: getUser,
    saveHistory: saveHistory, getHistory: getHistory,
    getTodayCache: getTodayCache,
    setDisclaimer: setDisclaimer, getDisclaimer: getDisclaimer,
    scoreToStars: scoreToStars, today: today,
    colorToHex: colorToHex,
  };
})();
