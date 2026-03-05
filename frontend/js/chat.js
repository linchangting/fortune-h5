/**
 * 对话模块 — SSE 流式接收 + 智能状态管理
 * 实现「知命先生」AI 命理师对话交互
 */
var FortuneChat = (function () {
  'use strict';

  var state = {
    messages: [],
    birthInfo: null,
    fortuneData: null,
    isStreaming: false,
    phase: 'greeting',
  };

  var WELCOME_MSG =
    '您好，我是**知命先生**，一位融合四大命理流派的命理师。\n\n' +
    '我精通《子平真诠》《穷通宝鉴》《滴天髓》等经典，能从**格局、调候、象法、心理**四重视角为您深度解读命盘。\n\n' +
    '请告诉我您的**出生年月日和时辰**，我来为您排盘解读。\n' +
    '（例如："我是1990年5月15日下午3点出生的"）';

  var QUICK_QUESTIONS = [
    '我什么时候财运最旺？',
    '我适合什么行业？',
    '今年运势如何？',
    '我的婚姻运怎样？',
  ];

  function init() {
    state.messages = [];
    state.birthInfo = null;
    state.fortuneData = null;
    state.isStreaming = false;
    state.phase = 'greeting';

    var container = document.getElementById('chat-messages');
    if (container) container.innerHTML = '';

    _addAIMessage(WELCOME_MSG);
  }

  function sendMessage(text) {
    if (!text || !text.trim() || state.isStreaming) return;
    text = text.trim();

    _addUserMessage(text);

    state.messages.push({ role: 'user', content: text });

    if (state.phase === 'greeting' || state.phase === 'collecting') {
      _tryExtractBirth();
    } else {
      _streamChat();
    }
  }

  function sendQuickAction(text) {
    sendMessage(text);
  }

  function setFortuneData(data) {
    state.fortuneData = data;
    state.phase = 'ready';
  }

  function _tryExtractBirth() {
    state.phase = 'collecting';
    _showTyping();

    FortuneAPI.extractBirth(state.messages)
      .then(function (resp) {
        var info = resp.birth_info;
        if (!info) {
          _removeTyping();
          _streamChat();
          return;
        }

        var year = info.year;
        var month = info.month;
        var day = info.day;
        var hour = info.hour;
        var gender = info.gender;
        var calendar = info.calendar;
        var needs = info.needs_clarify || [];

        if (year && month && day && hour !== null && hour !== undefined && gender && calendar) {
          state.birthInfo = info;
          _removeTyping();
          _doPaipan(info);
        } else if (needs.length > 0) {
          _removeTyping();
          _streamChat();
        } else {
          _removeTyping();
          _streamChat();
        }
      })
      .catch(function () {
        _removeTyping();
        _streamChat();
      });
  }

  function _doPaipan(info) {
    var dateStr = info.year + '-' +
      String(info.month).padStart(2, '0') + '-' +
      String(info.day).padStart(2, '0');

    var req = {
      birth_date: dateStr,
      calendar_type: info.calendar || 'solar',
      birth_hour: info.hour,
      gender: info.gender,
      is_leap_month: info.is_leap || false,
    };

    _addAIMessage('收到！正在为您排盘分析…\n\n四位专家正在协作分析您的命盘');

    FortuneAPI.fortune(req)
      .then(function (data) {
        state.fortuneData = data;
        state.phase = 'ready';

        FortuneUtils.saveUser(req);
        FortuneUtils.saveHistory(FortuneUtils.today(), data);

        _renderFortuneCard(data);

        state.messages.push({
          role: 'assistant',
          content: '已完成排盘：' + JSON.stringify({
            bazi: data.bazi, wuxing: data.wuxing,
            daily: { scores: data.daily.scores },
          }),
        });

        setTimeout(function () {
          _streamAnalysis(data, req);
        }, 500);
      })
      .catch(function (err) {
        _addAIMessage('排盘过程中遇到了问题：' + (err.message || '请检查出生信息是否正确') + '\n\n请重新告诉我您的出生信息。');
        state.phase = 'collecting';
      });
  }

  function _streamAnalysis(data, req) {
    state.isStreaming = true;
    _updateSendBtn();

    var bubbleEl = _createAIBubble();
    var textEl = bubbleEl.querySelector('.ai-text');

    var fullText = '';

    FortuneAPI.chatStream(
      state.messages.concat([{
        role: 'user',
        content: '请基于以上命盘数据，用多专家协作视角为我做一个全面的命盘解读。先给一句话总结，再展开详细分析。',
      }]),
      state.fortuneData
    ).then(function (reader) {
      function pump() {
        return reader.read().then(function (result) {
          if (result.done) {
            state.isStreaming = false;
            _updateSendBtn();
            state.messages.push({ role: 'assistant', content: fullText });
            _addQuickActions(bubbleEl);
            _scrollToBottom();
            return;
          }
          var text = result.value;
          if (text) {
            fullText += text;
            textEl.innerHTML = _renderMarkdown(fullText);
            _scrollToBottom();
          }
          return pump();
        });
      }
      return pump();
    }).catch(function (err) {
      state.isStreaming = false;
      _updateSendBtn();
      textEl.innerHTML = '分析过程中出现了问题，请重新提问。';
    });
  }

  function _streamChat() {
    state.isStreaming = true;
    _updateSendBtn();

    var bubbleEl = _createAIBubble();
    var textEl = bubbleEl.querySelector('.ai-text');

    var fullText = '';

    FortuneAPI.chatStream(state.messages, state.fortuneData)
      .then(function (reader) {
        function pump() {
          return reader.read().then(function (result) {
            if (result.done) {
              state.isStreaming = false;
              _updateSendBtn();
              state.messages.push({ role: 'assistant', content: fullText });
              if (state.phase === 'ready') {
                _addQuickActions(bubbleEl);
              }
              _scrollToBottom();
              return;
            }
            var text = result.value;
            if (text) {
              fullText += text;
              textEl.innerHTML = _renderMarkdown(fullText);
              _scrollToBottom();
            }
            return pump();
          });
        }
        return pump();
      })
      .catch(function () {
        state.isStreaming = false;
        _updateSendBtn();
        textEl.innerHTML = '对话出现了问题，请重试。';
      });
  }

  function _addUserMessage(text) {
    var container = document.getElementById('chat-messages');
    var div = document.createElement('div');
    div.className = 'chat-bubble user';
    div.textContent = text;
    container.appendChild(div);
    _scrollToBottom();
  }

  function _addAIMessage(text) {
    var container = document.getElementById('chat-messages');
    var div = document.createElement('div');
    div.className = 'chat-bubble ai';
    div.innerHTML =
      '<div class="ai-name">知命先生</div>' +
      '<div class="ai-text">' + _renderMarkdown(text) + '</div>';
    container.appendChild(div);
    state.messages.push({ role: 'assistant', content: text });
    _scrollToBottom();
  }

  function _createAIBubble() {
    var container = document.getElementById('chat-messages');
    _removeTyping();
    var div = document.createElement('div');
    div.className = 'chat-bubble ai';
    div.innerHTML =
      '<div class="ai-name">知命先生</div>' +
      '<div class="ai-text"><div class="typing-indicator"><span></span><span></span><span></span></div></div>';
    container.appendChild(div);
    _scrollToBottom();
    return div;
  }

  function _renderFortuneCard(data) {
    var container = document.getElementById('chat-messages');
    var div = document.createElement('div');
    div.className = 'chat-bubble ai';

    var bazi = data.bazi || {};
    var pillars = bazi.pillars || {};
    var wuxing = data.wuxing || {};
    var scores = (data.daily && data.daily.scores) || {};

    var pillarsHtml = '';
    var names = { year: '年柱', month: '月柱', day: '日柱', hour: '时柱' };
    ['year', 'month', 'day', 'hour'].forEach(function (k) {
      var p = pillars[k];
      if (p) {
        pillarsHtml +=
          '<div class="cfc-pillar">' +
          '<div class="p-label">' + names[k] + '</div>' +
          '<div class="p-gan">' + p.gan + '</div>' +
          '<div class="p-zhi">' + p.zhi + '</div>' +
          '</div>';
      }
    });

    var infoLines = [];
    if (wuxing.day_master) infoLines.push('日主：' + wuxing.day_master + '（' + (wuxing.strength || '') + '）');
    if (wuxing.favorable) infoLines.push('喜用神：' + wuxing.favorable.join('、'));
    if (scores.overall) infoLines.push('今日综合：' + scores.overall + '分');

    div.innerHTML =
      '<div class="ai-name">知命先生</div>' +
      '<div class="chat-fortune-card">' +
      '<div class="cfc-title">您的八字排盘</div>' +
      '<div class="cfc-pillars">' + pillarsHtml + '</div>' +
      '<div style="font-size:12px;color:var(--ink-light);line-height:1.6;">' +
      infoLines.join('<br/>') +
      '</div></div>';

    container.appendChild(div);
    _scrollToBottom();
  }

  function _addQuickActions(bubbleEl) {
    var wrap = document.createElement('div');
    wrap.className = 'quick-actions';
    QUICK_QUESTIONS.forEach(function (q) {
      var btn = document.createElement('button');
      btn.className = 'quick-action-btn';
      btn.textContent = q;
      btn.addEventListener('click', function () {
        sendQuickAction(q);
      });
      wrap.appendChild(btn);
    });
    bubbleEl.appendChild(wrap);
    _scrollToBottom();
  }

  function _showTyping() {
    var container = document.getElementById('chat-messages');
    var existing = container.querySelector('.typing-bubble');
    if (existing) return;
    var div = document.createElement('div');
    div.className = 'chat-bubble ai typing-bubble';
    div.innerHTML =
      '<div class="ai-name">知命先生</div>' +
      '<div class="typing-indicator"><span></span><span></span><span></span></div>';
    container.appendChild(div);
    _scrollToBottom();
  }

  function _removeTyping() {
    var container = document.getElementById('chat-messages');
    var el = container.querySelector('.typing-bubble');
    if (el) el.remove();
  }

  function _scrollToBottom() {
    var container = document.getElementById('chat-container');
    if (container) {
      requestAnimationFrame(function () {
        container.scrollTop = container.scrollHeight;
      });
    }
  }

  function _updateSendBtn() {
    var btn = document.getElementById('chat-send');
    if (btn) btn.disabled = state.isStreaming;
  }

  function _renderMarkdown(text) {
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

  function isStreaming() {
    return state.isStreaming;
  }

  return {
    init: init,
    sendMessage: sendMessage,
    sendQuickAction: sendQuickAction,
    setFortuneData: setFortuneData,
    isStreaming: isStreaming,
  };
})();
