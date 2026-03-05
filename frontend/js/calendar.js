/**
 * 农历三列滚动选择器 (年/月/日)
 * 支持 touch 惯性滚动、闰月标记
 */
var LunarPicker = (function () {
  'use strict';

  var ITEM_H = 40;
  var VISIBLE = 5;
  var PADDING = Math.floor(VISIBLE / 2);

  var state = {
    year: 1990, month: 1, day: 1, isLeap: false,
    monthsData: null,
    _monthItems: null,
    _monthsCache: {},
    onConfirm: null,
  };

  var els = {};

  function init(onConfirm) {
    state.onConfirm = onConfirm;
    els.overlay = document.getElementById('picker-overlay');
    els.sheet = document.getElementById('lunar-picker');
    els.yearCol = document.getElementById('picker-year');
    els.monthCol = document.getElementById('picker-month');
    els.dayCol = document.getElementById('picker-day');

    document.getElementById('picker-cancel').addEventListener('click', hide);
    document.getElementById('picker-confirm').addEventListener('click', confirm);
    els.overlay.addEventListener('click', hide);

    _initColumn(els.yearCol, _yearItems(), state.year, function (val) {
      state.year = val;
      _refreshMonths();
    });
  }

  function show(year, month, day, isLeap) {
    state.year = year || 1990;
    state.month = month || 1;
    state.day = day || 1;
    state.isLeap = isLeap || false;

    _renderYear();
    _refreshMonths();

    els.overlay.classList.add('active');
    els.sheet.classList.add('active');
  }

  function hide() {
    els.overlay.classList.remove('active');
    els.sheet.classList.remove('active');
  }

  function confirm() {
    hide();
    if (state.onConfirm) {
      state.onConfirm({
        year: state.year,
        month: state.month,
        day: state.day,
        isLeap: state.isLeap,
      });
    }
  }

  function _yearItems() {
    var items = [];
    var GAN = '甲乙丙丁戊己庚辛壬癸';
    var ZHI = '子丑寅卯辰巳午未申酉戌亥';
    for (var y = 1940; y <= 2050; y++) {
      var g = GAN[(y - 4) % 10];
      var z = ZHI[(y - 4) % 12];
      items.push({ value: y, label: y + ' ' + g + z + '年' });
    }
    return items;
  }

  function _renderYear() {
    var items = _yearItems();
    var idx = state.year - 1940;
    _initColumn(els.yearCol, items, idx, function (i) {
      state.year = 1940 + i;
      _refreshMonths();
    });
  }

  function _refreshMonths() {
    var cached = state._monthsCache[state.year];
    if (cached) {
      _buildMonthColumn(cached);
      return;
    }

    _buildMonthColumn(null);

    if (typeof FortuneAPI !== 'undefined' && FortuneAPI.lunarMonths) {
      FortuneAPI.lunarMonths(state.year)
        .then(function (data) {
          var months = data.months || [];
          state._monthsCache[state.year] = months;
          _buildMonthColumn(months);
        })
        .catch(function () {});
    }
  }

  function _buildMonthColumn(apiMonths) {
    var MONTH_CN = ['', '正月', '二月', '三月', '四月', '五月', '六月',
                    '七月', '八月', '九月', '十月', '冬月', '腊月'];
    var items = [];

    if (apiMonths && apiMonths.length > 0) {
      apiMonths.forEach(function (m) {
        items.push({ value: m.month, label: m.name, isLeap: m.is_leap, days: m.days });
      });
    } else {
      for (var m = 1; m <= 12; m++) {
        items.push({ value: m, label: MONTH_CN[m], isLeap: false, days: 30 });
      }
    }

    state._monthItems = items;

    var monthIdx = 0;
    for (var i = 0; i < items.length; i++) {
      if (items[i].value === state.month && items[i].isLeap === state.isLeap) {
        monthIdx = i;
        break;
      }
    }

    _initColumn(els.monthCol, items, monthIdx, function (i) {
      var item = items[i];
      state.month = item.value;
      state.isLeap = item.isLeap;
      _refreshDays();
    });
    _refreshDays();
  }

  function _refreshDays() {
    var DAY_CN = ['', '初一', '初二', '初三', '初四', '初五', '初六', '初七',
                  '初八', '初九', '初十', '十一', '十二', '十三', '十四', '十五',
                  '十六', '十七', '十八', '十九', '二十', '廿一', '廿二', '廿三',
                  '廿四', '廿五', '廿六', '廿七', '廿八', '廿九', '三十'];

    var maxDay = 30;
    var mItems = state._monthItems;
    if (mItems) {
      for (var i = 0; i < mItems.length; i++) {
        if (mItems[i].value === state.month && mItems[i].isLeap === state.isLeap) {
          maxDay = mItems[i].days || 30;
          break;
        }
      }
    }

    var items = [];
    for (var d = 1; d <= maxDay; d++) {
      items.push({ value: d, label: DAY_CN[d] });
    }
    var dayIdx = Math.min(state.day, maxDay) - 1;
    _initColumn(els.dayCol, items, dayIdx, function (i) {
      state.day = i + 1;
    });
  }

  function _initColumn(colEl, items, selectedIdx, onChange) {
    var scroller = colEl.querySelector('.picker-scroller');
    if (!scroller) return;

    var html = '';
    for (var i = 0; i < PADDING; i++) {
      html += '<div class="picker-item" style="height:' + ITEM_H + 'px"></div>';
    }
    for (var j = 0; j < items.length; j++) {
      var cls = items[j].isLeap ? ' leap' : '';
      html += '<div class="picker-item' + cls + '" style="height:' + ITEM_H + 'px" data-idx="' + j + '">' +
              items[j].label + '</div>';
    }
    for (var k = 0; k < PADDING; k++) {
      html += '<div class="picker-item" style="height:' + ITEM_H + 'px"></div>';
    }
    scroller.innerHTML = html;

    var currentIdx = selectedIdx || 0;
    var offset = -currentIdx * ITEM_H;
    scroller.style.transform = 'translateY(' + offset + 'px)';

    var startY = 0, startOffset = 0, lastY = 0, lastTime = 0, velocity = 0;
    var touching = false;

    function snap() {
      var idx = Math.round(-offset / ITEM_H);
      idx = Math.max(0, Math.min(idx, items.length - 1));
      offset = -idx * ITEM_H;
      scroller.style.transition = 'transform .3s cubic-bezier(.22,1,.36,1)';
      scroller.style.transform = 'translateY(' + offset + 'px)';
      if (idx !== currentIdx) {
        currentIdx = idx;
        if (onChange) onChange(idx);
      }
    }

    function onStart(e) {
      var t = e.touches ? e.touches[0] : e;
      startY = t.clientY;
      startOffset = offset;
      lastY = startY;
      lastTime = Date.now();
      velocity = 0;
      touching = true;
      scroller.style.transition = 'none';
    }

    function onMove(e) {
      if (!touching) return;
      e.preventDefault();
      var t = e.touches ? e.touches[0] : e;
      var now = Date.now();
      var dt = now - lastTime;
      var dy = t.clientY - lastY;
      if (dt > 0) velocity = dy / dt;
      lastY = t.clientY;
      lastTime = now;
      offset = startOffset + (t.clientY - startY);
      scroller.style.transform = 'translateY(' + offset + 'px)';
    }

    function onEnd() {
      if (!touching) return;
      touching = false;
      if (Math.abs(velocity) > 0.3) {
        offset += velocity * 150;
      }
      snap();
    }

    colEl.removeEventListener('touchstart', colEl._ts);
    colEl.removeEventListener('touchmove', colEl._tm);
    colEl.removeEventListener('touchend', colEl._te);
    colEl.removeEventListener('mousedown', colEl._md);

    colEl._ts = onStart;
    colEl._tm = onMove;
    colEl._te = onEnd;
    colEl._md = onStart;

    colEl.addEventListener('touchstart', onStart, { passive: true });
    colEl.addEventListener('touchmove', onMove, { passive: false });
    colEl.addEventListener('touchend', onEnd);
    colEl.addEventListener('mousedown', onStart);
    document.addEventListener('mousemove', onMove);
    document.addEventListener('mouseup', onEnd);
  }

  return { init: init, show: show, hide: hide };
})();
