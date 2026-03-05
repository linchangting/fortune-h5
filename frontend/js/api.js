/**
 * API 交互层 — 支持传统 REST + SSE 流式
 */
var FortuneAPI = (function () {
  'use strict';

  var BASE = location.port === '8080'
    ? 'http://' + location.hostname + ':8000'
    : '';

  function fortune(data) {
    return _post('/api/fortune', data);
  }

  function fortuneDaily(data) {
    return _post('/api/fortune/daily', data);
  }

  function calendarConvert(date, type, isLeap) {
    var qs = '?date=' + encodeURIComponent(date) + '&type=' + type;
    if (isLeap) qs += '&is_leap=true';
    return _get('/api/calendar/convert' + qs);
  }

  function lunarMonths(year) {
    return _get('/api/calendar/lunar-months?year=' + year);
  }

  function health() {
    return _get('/api/health');
  }

  function extractBirth(messages) {
    return _post('/api/chat/extract-birth', { messages: messages });
  }

  /**
   * SSE 流式对话 — 返回 { read() } 可读流接口
   * reader.read() 返回 { done: bool, value: string }
   */
  function chatStream(messages, fortuneData) {
    var body = { messages: messages };
    if (fortuneData) {
      body.fortune_data = fortuneData;
    }

    return fetch(BASE + '/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }).then(function (response) {
      if (!response.ok) {
        return response.text().then(function (text) {
          throw new Error(text || response.statusText);
        });
      }

      var reader = response.body.getReader();
      var decoder = new TextDecoder();
      var buffer = '';

      return {
        read: function () {
          return reader.read().then(function process(result) {
            if (result.done) {
              return { done: true, value: null };
            }

            buffer += decoder.decode(result.value, { stream: true });
            var lines = buffer.split('\n');
            buffer = lines.pop() || '';

            var text = '';
            for (var i = 0; i < lines.length; i++) {
              var line = lines[i].trim();
              if (!line.startsWith('data: ')) continue;
              var payload = line.substring(6);
              if (payload === '[DONE]') {
                return { done: true, value: text || null };
              }
              try {
                var parsed = JSON.parse(payload);
                if (parsed.text) text += parsed.text;
              } catch (e) {
                // skip malformed
              }
            }

            if (text) {
              return { done: false, value: text };
            }

            return reader.read().then(process);
          });
        },
      };
    });
  }

  /**
   * SSE 流式深度分析
   */
  function deepAnalysisStream(data) {
    return fetch(BASE + '/api/fortune/deep-analysis', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    }).then(function (response) {
      if (!response.ok) {
        return response.text().then(function (text) {
          throw new Error(text || response.statusText);
        });
      }

      var reader = response.body.getReader();
      var decoder = new TextDecoder();
      var buffer = '';

      return {
        read: function () {
          return reader.read().then(function process(result) {
            if (result.done) {
              return { done: true, value: null };
            }

            buffer += decoder.decode(result.value, { stream: true });
            var lines = buffer.split('\n');
            buffer = lines.pop() || '';

            var text = '';
            for (var i = 0; i < lines.length; i++) {
              var line = lines[i].trim();
              if (!line.startsWith('data: ')) continue;
              var payload = line.substring(6);
              if (payload === '[DONE]') {
                return { done: true, value: text || null };
              }
              try {
                var parsed = JSON.parse(payload);
                if (parsed.text) text += parsed.text;
              } catch (e) {}
            }

            if (text) {
              return { done: false, value: text };
            }

            return reader.read().then(process);
          });
        },
      };
    });
  }

  function _parseError(r) {
    return r.text().then(function (text) {
      try {
        var json = JSON.parse(text);
        throw new Error(json.detail || r.statusText);
      } catch (e) {
        if (e instanceof SyntaxError) throw new Error(r.statusText || '请求失败');
        throw e;
      }
    });
  }

  function _post(path, body) {
    return fetch(BASE + path, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }).then(function (r) {
      if (!r.ok) return _parseError(r);
      return r.json();
    });
  }

  function _get(path) {
    return fetch(BASE + path).then(function (r) {
      if (!r.ok) return _parseError(r);
      return r.json();
    });
  }

  return {
    fortune: fortune,
    fortuneDaily: fortuneDaily,
    calendarConvert: calendarConvert,
    lunarMonths: lunarMonths,
    health: health,
    extractBirth: extractBirth,
    chatStream: chatStream,
    deepAnalysisStream: deepAnalysisStream,
  };
})();
