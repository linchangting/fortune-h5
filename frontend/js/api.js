/**
 * API 交互层
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
  };
})();
