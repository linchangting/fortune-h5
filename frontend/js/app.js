/**
 * 应用主入口 — 状态管理 + 事件绑定 + 双模式（对话 / 表单）
 */
(function () {
  'use strict';

  var $ = FortuneUtils.$;
  var $$ = FortuneUtils.$$;

  var state = {
    calendarType: 'solar',
    solarDate: '1990-01-01',
    lunarYear: 1990, lunarMonth: 1, lunarDay: 1, isLeap: false,
    birthHour: -1,
    gender: '',
    disclaimerAccepted: false,
    currentResult: null,
    mode: 'chat',
  };

  var TAB_SCREENS = ['home', 'woodfish', 'history'];

  function navigate(screenId) {
    FortuneUI.showScreen(screenId);

    var tabBar = document.getElementById('tab-bar');
    if (tabBar) {
      var isTab = TAB_SCREENS.indexOf(screenId) !== -1;
      tabBar.classList.toggle('hidden', !isTab);
    }

    if (screenId === 'result' && state.currentResult) {
      FortuneUI.renderResult(state.currentResult);
    }
    if (screenId === 'dayun' && state.currentResult) {
      FortuneUI.renderDayun(state.currentResult);
    }
    if (screenId === 'yearly' && state.currentResult) {
      FortuneUI.renderYearly(state.currentResult);
    }
    if (screenId === 'home') {
      _setActiveTab('home');
    }
    if (screenId === 'history') {
      FortuneUI.renderHistory('history-full-list');
      _setActiveTab('history');
    }
    if (screenId === 'woodfish') {
      Woodfish.refresh();
      _setActiveTab('woodfish');
    }
    if (screenId === 'chat') {
      setTimeout(function () {
        var input = $('#chat-input');
        if (input) input.focus();
      }, 400);
    }
  }

  function _setActiveTab(tab) {
    $$('.tab-bar .tab').forEach(function (el) {
      el.classList.toggle('active', el.getAttribute('data-tab') === tab);
    });
  }

  function _updateLunarDisplay() {
    var MONTH_CN = ['', '正月', '二月', '三月', '四月', '五月', '六月',
                    '七月', '八月', '九月', '十月', '冬月', '腊月'];
    var DAY_CN = ['', '初一', '初二', '初三', '初四', '初五', '初六', '初七',
                  '初八', '初九', '初十', '十一', '十二', '十三', '十四', '十五',
                  '十六', '十七', '十八', '十九', '二十', '廿一', '廿二', '廿三',
                  '廿四', '廿五', '廿六', '廿七', '廿八', '廿九', '三十'];
    var text = state.lunarYear + '年 ' +
      (state.isLeap ? '闰' : '') + (MONTH_CN[state.lunarMonth] || '') + ' ' +
      (DAY_CN[state.lunarDay] || '');
    var display = $('#lunar-display');
    display.textContent = text;
    display.className = 'value';
  }

  function _checkSubmitReady() {
    var ready = state.birthHour >= 0 && state.gender !== '';
    if (state.calendarType === 'solar') {
      ready = ready && !!state.solarDate;
    } else {
      ready = ready && state.lunarYear > 0;
    }
    $('#btn-submit').disabled = !ready;
  }

  function _buildRequest() {
    var date, calType, isLeap;
    if (state.calendarType === 'solar') {
      date = state.solarDate;
      calType = 'solar';
      isLeap = false;
    } else {
      date = state.lunarYear + '-' +
        String(state.lunarMonth).padStart(2, '0') + '-' +
        String(state.lunarDay).padStart(2, '0');
      calType = 'lunar';
      isLeap = state.isLeap;
    }
    return {
      birth_date: date,
      calendar_type: calType,
      birth_hour: state.birthHour,
      gender: state.gender,
      is_leap_month: isLeap,
    };
  }

  function _doFortune() {
    navigate('loading');
    FortuneUI.setLoadingStep('paipan');

    var req = _buildRequest();

    setTimeout(function () { FortuneUI.setLoadingStep('wuxing'); }, 800);
    setTimeout(function () { FortuneUI.setLoadingStep('fortune'); }, 1800);

    FortuneAPI.fortune(req)
      .then(function (data) {
        state.currentResult = data;
        FortuneUtils.saveUser(req);
        FortuneUtils.saveHistory(FortuneUtils.today(), data);
        FortuneUI.setLoadingStep('reading');
        setTimeout(function () { navigate('result'); }, 500);
      })
      .catch(function (err) {
        alert('推算失败: ' + (err.message || '请检查网络连接'));
        navigate('input');
      });
  }

  function _doDailyFortune() {
    var user = FortuneUtils.getUser();
    if (!user) return;

    navigate('loading');
    FortuneUI.setLoadingStep('paipan');
    setTimeout(function () { FortuneUI.setLoadingStep('fortune'); }, 600);

    FortuneAPI.fortuneDaily(user)
      .then(function (data) {
        state.currentResult = data;
        FortuneUtils.saveHistory(FortuneUtils.today(), data);
        FortuneUI.setLoadingStep('reading');
        setTimeout(function () { navigate('result'); }, 500);
      })
      .catch(function (err) {
        navigate('home');
      });
  }

  function _doDeepAnalysis() {
    if (!state.currentResult) return;
    navigate('deep');

    var el = document.getElementById('deep-content');
    if (!el) return;

    el.innerHTML =
      '<div class="deep-loading">' +
      '<div class="typing-indicator"><span></span><span></span><span></span></div>' +
      '<p>多专家协作分析中…</p></div>';

    var user = FortuneUtils.getUser();
    if (!user) return;

    FortuneAPI.deepAnalysisStream(user)
      .then(function (reader) {
        var fullText = '';
        el.innerHTML = '';

        function pump() {
          return reader.read().then(function (result) {
            if (result.done) return;
            if (result.value) {
              fullText += result.value;
              el.innerHTML = _renderDeepMarkdown(fullText);
              el.scrollIntoView({ behavior: 'smooth', block: 'end' });
            }
            return pump();
          });
        }
        return pump();
      })
      .catch(function (err) {
        el.innerHTML = '<p style="color:var(--muted);text-align:center;">分析过程中出现了问题，请返回重试。</p>';
      });
  }

  function _renderDeepMarkdown(text) {
    return text
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.+?)\*/g, '<em>$1</em>')
      .replace(/「(.+?)」/g, '<em style="color:var(--gold)">「$1」</em>')
      .replace(/###\s*(.+)/g, '<h3>$1</h3>')
      .replace(/##\s*(.+)/g, '<h2>$1</h2>')
      .replace(/\n/g, '<br/>');
  }

  function init() {
    state.disclaimerAccepted = FortuneUtils.getDisclaimer();

    // ── 首页：对话模式 ──
    $('#btn-chat').addEventListener('click', function () {
      if (!state.disclaimerAccepted) {
        state.mode = 'chat';
        FortuneUI.showOverlay('disclaimer');
        return;
      }
      FortuneChat.init();
      navigate('chat');
    });

    // ── 首页：表单模式 ──
    $('#btn-form').addEventListener('click', function () {
      var cached = FortuneUtils.getTodayCache();
      if (cached) {
        state.currentResult = cached;
        navigate('result');
        return;
      }

      var user = FortuneUtils.getUser();
      if (user && state.disclaimerAccepted) {
        _doDailyFortune();
        return;
      }

      if (!state.disclaimerAccepted) {
        state.mode = 'form';
        FortuneUI.showOverlay('disclaimer');
        return;
      }
      navigate('input');
    });

    // ── 免责 ──
    $('#disclaimer-check').addEventListener('change', function () {
      $('#btn-disclaimer-ok').disabled = !this.checked;
    });
    $('#btn-disclaimer-ok').addEventListener('click', function () {
      state.disclaimerAccepted = true;
      FortuneUtils.setDisclaimer(true);
      FortuneUI.hideOverlay('disclaimer');
      if (state.mode === 'chat') {
        FortuneChat.init();
        navigate('chat');
      } else {
        navigate('input');
      }
    });

    // ── 对话输入 ──
    var chatInput = $('#chat-input');
    var chatSend = $('#chat-send');

    chatInput.addEventListener('input', function () {
      this.style.height = 'auto';
      this.style.height = Math.min(this.scrollHeight, 120) + 'px';
      chatSend.disabled = !this.value.trim() || FortuneChat.isStreaming();
    });

    chatInput.addEventListener('keydown', function (e) {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        if (!chatSend.disabled) _sendChatMessage();
      }
    });

    chatSend.addEventListener('click', function () {
      if (!this.disabled) _sendChatMessage();
    });

    function _sendChatMessage() {
      var text = chatInput.value;
      chatInput.value = '';
      chatInput.style.height = 'auto';
      chatSend.disabled = true;
      FortuneChat.sendMessage(text);
    }

    // ── 新对话 ──
    $('#btn-new-chat').addEventListener('click', function () {
      FortuneChat.init();
    });

    // ── 日历类型切换 ──
    $$('#calendar-switch button').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var prevType = state.calendarType;
        $$('#calendar-switch button').forEach(function (b) { b.classList.remove('active'); });
        this.classList.add('active');
        state.calendarType = this.getAttribute('data-type');

        if (state.calendarType === 'solar') {
          $('#solar-date-wrap').style.display = '';
          $('#lunar-date-wrap').style.display = 'none';
        } else {
          $('#solar-date-wrap').style.display = 'none';
          $('#lunar-date-wrap').style.display = '';
        }

        if (prevType === 'solar' && state.calendarType === 'lunar' && state.solarDate) {
          FortuneAPI.calendarConvert(state.solarDate, 'solar_to_lunar', false)
            .then(function (data) {
              var r = data.result;
              if (r) {
                state.lunarYear = r.year; state.lunarMonth = r.month;
                state.lunarDay = r.day; state.isLeap = r.is_leap || false;
                _updateLunarDisplay();
              }
            }).catch(function () {});
        } else if (prevType === 'lunar' && state.calendarType === 'solar' && state.lunarYear > 0) {
          var lunarDate = state.lunarYear + '-' +
            String(state.lunarMonth).padStart(2, '0') + '-' +
            String(state.lunarDay).padStart(2, '0');
          FortuneAPI.calendarConvert(lunarDate, 'lunar_to_solar', state.isLeap)
            .then(function (data) {
              var r = data.result;
              if (r) {
                var converted = r.year + '-' + String(r.month).padStart(2, '0') + '-' + String(r.day).padStart(2, '0');
                state.solarDate = converted;
                $('#solar-date').value = converted;
              }
            }).catch(function () {});
        }
        _checkSubmitReady();
      });
    });

    // ── 阳历日期 ──
    $('#solar-date').addEventListener('change', function () {
      state.solarDate = this.value;
      _checkSubmitReady();
    });

    // ── 农历选择器 ──
    LunarPicker.init(function (result) {
      state.lunarYear = result.year;
      state.lunarMonth = result.month;
      state.lunarDay = result.day;
      state.isLeap = result.isLeap;
      _updateLunarDisplay();
      _checkSubmitReady();
    });

    $('#lunar-trigger').addEventListener('click', function () {
      LunarPicker.show(state.lunarYear, state.lunarMonth, state.lunarDay, state.isLeap);
    });

    // ── 时辰 ──
    $$('.shichen-btn').forEach(function (btn) {
      btn.addEventListener('click', function () {
        $$('.shichen-btn').forEach(function (b) { b.classList.remove('selected'); });
        this.classList.add('selected');
        state.birthHour = parseInt(this.getAttribute('data-hour'), 10);
        _checkSubmitReady();
      });
    });

    // ── 性别 ──
    $$('.gender-btn').forEach(function (btn) {
      btn.addEventListener('click', function () {
        $$('.gender-btn').forEach(function (b) { b.classList.remove('selected'); });
        this.classList.add('selected');
        state.gender = this.getAttribute('data-gender');
        _checkSubmitReady();
      });
    });

    // ── 提交 ──
    $('#btn-submit').addEventListener('click', function () {
      if (!this.disabled) _doFortune();
    });

    // ── 通用导航 ──
    $$('[data-goto]').forEach(function (el) {
      el.addEventListener('click', function (e) {
        e.preventDefault();
        navigate(this.getAttribute('data-goto'));
      });
    });

    // ── 结果页操作 ──
    $('#btn-yearly').addEventListener('click', function () { navigate('yearly'); });
    $('#btn-dayun').addEventListener('click', function () { navigate('dayun'); });
    $('#btn-deep-analysis').addEventListener('click', function () { _doDeepAnalysis(); });

    $('#btn-ask-ai').addEventListener('click', function () {
      if (state.currentResult) {
        FortuneChat.init();
        FortuneChat.setFortuneData(state.currentResult);
        navigate('chat');
      }
    });

    // ── 海报 ──
    $('#btn-poster').addEventListener('click', function () {
      if (state.currentResult) {
        FortunePoster.generate(state.currentResult);
        FortuneUI.showOverlay('poster');
      }
    });
    $('#btn-close-poster').addEventListener('click', function () {
      FortuneUI.hideOverlay('poster');
    });
    $('#btn-save-poster').addEventListener('click', function () {
      FortunePoster.save();
    });

    // ── 历史点击 ──
    document.addEventListener('click', function (e) {
      var item = e.target.closest('.history-item');
      if (!item) return;
      var date = item.getAttribute('data-date');
      var history = FortuneUtils.getHistory();
      if (history[date]) {
        state.currentResult = history[date];
        navigate('result');
      }
    });

    // ── 快捷操作按钮 ──
    document.addEventListener('click', function (e) {
      var btn = e.target.closest('.quick-action-btn');
      if (btn && document.getElementById('screen-chat').classList.contains('active')) {
        FortuneChat.sendQuickAction(btn.textContent);
      }
    });

    // ── Tab 栏 ──
    $$('.tab-bar .tab').forEach(function (tab) {
      tab.addEventListener('click', function () {
        var target = this.getAttribute('data-tab');
        navigate(target);
      });
    });

    // ── 木鱼初始化 ──
    Woodfish.init();

    // ── 自动每日推送 ──
    var user = FortuneUtils.getUser();
    var todayCache = FortuneUtils.getTodayCache();
    if (todayCache) {
      state.currentResult = todayCache;
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
