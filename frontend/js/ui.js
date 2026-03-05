/**
 * UI 渲染模块：结果页各区域的 DOM 生成
 */
var FortuneUI = (function () {
  'use strict';

  var $ = FortuneUtils.$;
  var $$ = FortuneUtils.$$;

  function showScreen(id) {
    $$('.screen').forEach(function (s) { s.classList.remove('active'); });
    var target = document.getElementById('screen-' + id);
    if (target) target.classList.add('active');
  }

  function showOverlay(id) {
    var el = document.getElementById('overlay-' + id);
    if (el) el.classList.add('active');
  }

  function hideOverlay(id) {
    var el = document.getElementById('overlay-' + id);
    if (el) el.classList.remove('active');
  }

  // ── 加载步骤 ──
  function setLoadingStep(step) {
    $$('#loading-steps .step').forEach(function (el) {
      var s = el.getAttribute('data-step');
      el.classList.remove('active', 'done');
      if (s === step) el.classList.add('active');
    });
    var ordered = ['paipan', 'wuxing', 'fortune', 'reading'];
    var idx = ordered.indexOf(step);
    $$('#loading-steps .step').forEach(function (el, i) {
      if (i < idx) el.classList.add('done');
    });
  }

  // ── 渲染结果页 ──
  function renderResult(data) {
    _renderBazi(data.bazi);
    _renderWuxing(data.wuxing);
    _renderScore(data.daily, data.reading);
    _renderFortuneGrid(data.daily, data.reading);
    _renderLucky(data.daily);
    _renderAlmanac(data.daily);
    _renderCautions(data.daily, data.reading);
  }

  function _renderBazi(bazi) {
    var el = $('#bazi-card');
    if (!el) return;
    var names = { year: '年柱', month: '月柱', day: '日柱', hour: '时柱' };
    var html = '';
    ['year', 'month', 'day', 'hour'].forEach(function (k) {
      var p = bazi.pillars[k];
      var nayin = bazi.nayin[k] || '';
      var ss = bazi.shishen[k] || {};
      var ssGan = ss.gan || '';
      html += '<div class="pillar-col">' +
        '<div class="pillar-label">' + names[k] + '</div>' +
        '<div class="pillar-gan">' + p.gan + '</div>' +
        '<div class="pillar-zhi">' + p.zhi + '</div>' +
        '<div class="pillar-nayin">' + nayin + '</div>' +
        '<div class="pillar-shishen">' + ssGan + '</div>' +
        '</div>';
    });
    el.innerHTML = html;
  }

  function _renderWuxing(wx) {
    var el = $('#wuxing-chart');
    if (!el) return;
    var dist = wx.distribution || {};
    var map = { '金': 'metal', '木': 'wood', '水': 'water', '火': 'fire', '土': 'earth' };
    var cn = { '金': '金', '木': '木', '水': '水', '火': '火', '土': '土' };
    var maxVal = 0;
    ['金', '木', '水', '火', '土'].forEach(function (k) {
      if ((dist[k] || 0) > maxVal) maxVal = dist[k];
    });
    maxVal = maxVal || 1;
    var fav = wx.favorable || [];

    var html = '';
    ['金', '木', '水', '火', '土'].forEach(function (k) {
      var val = dist[k] || 0;
      var pct = Math.round((val / (maxVal * 1.2)) * 100);
      var isFav = fav.indexOf(k) >= 0;
      html += '<div class="wx-row">' +
        '<span class="wx-label">' + cn[k] + '</span>' +
        '<div class="wx-bar-wrap"><div class="wx-bar ' + map[k] + '" style="width:' + pct + '%"></div></div>' +
        '<span class="wx-value">' + val.toFixed(1) +
        (isFav ? '<span class="wx-tag fav">喜</span>' : '') +
        '</span></div>';
    });
    el.innerHTML = html;
  }

  function _renderScore(daily, reading) {
    var el = $('#score-hero');
    if (!el) return;
    var scores = daily.scores || {};
    var overall = scores.overall || 70;
    var stars = FortuneUtils.scoreToStars(overall);
    var overview = (reading && reading.overview) || '';

    el.innerHTML =
      '<div class="score-number">' + overall + '</div>' +
      '<div class="score-label">今日综合运势</div>' +
      '<div class="score-stars">' + stars + '</div>' +
      (overview ? '<div class="score-overview">' + overview + '</div>' : '');
  }

  function _renderFortuneGrid(daily, reading) {
    var el = $('#fortune-grid');
    if (!el) return;
    var scores = daily.scores || {};
    var items = [
      { name: '事业运', key: 'career', icon: '💼' },
      { name: '财运', key: 'wealth', icon: '💰' },
      { name: '感情运', key: 'love', icon: '❤️' },
      { name: '健康运', key: 'health', icon: '🏃' },
    ];
    var html = '';
    items.forEach(function (item) {
      var score = scores[item.key] || 70;
      var text = (reading && reading[item.key]) || '';
      html += '<div class="fortune-card">' +
        '<div class="fc-header">' +
        '<span class="fc-name">' + item.icon + ' ' + item.name + '</span>' +
        '<span class="fc-score">' + score + '</span>' +
        '</div>' +
        '<div class="fc-text">' + text + '</div>' +
        '</div>';
    });
    el.innerHTML = html;
  }

  function _renderLucky(daily) {
    var el = $('#lucky-row');
    if (!el) return;
    var lucky = daily.lucky || {};
    var colorHex = FortuneUtils.colorToHex(lucky.color || '绿色');

    el.innerHTML =
      '<div class="lucky-item"><div class="li-label">幸运色</div>' +
      '<div class="li-value"><span class="lucky-color-dot" style="background:' + colorHex + '"></span>' +
      (lucky.color || '') + '</div></div>' +
      '<div class="lucky-item"><div class="li-label">幸运数字</div>' +
      '<div class="li-value">' + (lucky.number || '') + '</div></div>' +
      '<div class="lucky-item"><div class="li-label">幸运方位</div>' +
      '<div class="li-value">' + (lucky.direction || '') + '</div></div>';
  }

  function _renderAlmanac(daily) {
    var el = $('#almanac-row');
    if (!el) return;
    var alm = daily.almanac || {};
    var yiHtml = (alm.yi || []).map(function (t) {
      return '<span class="almanac-tag yi">' + t + '</span>';
    }).join('');
    var jiHtml = (alm.ji || []).map(function (t) {
      return '<span class="almanac-tag ji">' + t + '</span>';
    }).join('');

    el.innerHTML =
      '<div class="almanac-col"><div class="al-label yi">宜</div>' +
      '<div class="almanac-tags">' + yiHtml + '</div></div>' +
      '<div class="almanac-col"><div class="al-label ji">忌</div>' +
      '<div class="almanac-tags">' + jiHtml + '</div></div>';
  }

  function _renderCautions(daily, reading) {
    var el = $('#cautions-card');
    if (!el) return;
    var cautions = daily.cautions || [];
    if (cautions.length === 0) {
      el.style.display = 'none';
      return;
    }
    el.style.display = '';
    var html = '<div class="cc-title">今日注意</div>';
    cautions.forEach(function (c) {
      html += '<div class="cc-item">' + c + '</div>';
    });
    el.innerHTML = html;
  }

  // ── 渲染大运 ──
  function renderDayun(data) {
    var dayun = data.dayun || {};
    var list = dayun.list || [];
    var current = dayun.current_dayun;

    var info = $('#dayun-info');
    if (info) {
      info.textContent = '起运 ' + dayun.start_age + ' 岁 · 当前流年 ' +
        (dayun.current_liunian || '');
    }

    var el = $('#dayun-timeline');
    if (!el) return;
    var html = '';
    list.forEach(function (d) {
      var isCurrent = current && d.start_year === current.start_year;
      html += '<div class="dayun-item' + (isCurrent ? ' current' : '') + '">' +
        '<div class="dy-header">' +
        '<span class="dy-ganzhi">' + d.ganzhi + '</span>' +
        '<span class="dy-years">' + d.start_year + '–' + d.end_year + '</span>' +
        '</div>' +
        '<div class="dy-shishen">' + (d.shishen_gan || '') +
        (d.nayin ? ' · ' + d.nayin : '') + '</div>' +
        '<div class="dy-age">' + d.start_age + '–' + d.end_age + ' 岁</div>' +
        '</div>';
    });
    el.innerHTML = html;
  }

  // ── 渲染本年运势 ──
  function renderYearly(data) {
    var yearly = data.yearly || {};
    var yr = data.yearly_reading || {};

    _renderYearlyHeader(yearly);
    _renderTaisui(yearly.taisui);
    _renderYearlyScore(yearly, yr);
    _renderYearlyKeywords(yearly.keywords);
    _renderYearlyFortuneGrid(yearly, yr);
    _renderYearlyCautions(yearly, yr);
    _renderMonthlyChart(yearly.monthly);
  }

  function _renderYearlyHeader(yearly) {
    var el = $('#yearly-header');
    if (!el) return;
    el.innerHTML =
      '<div class="yh-year">' + (yearly.year || '') + '年</div>' +
      '<div class="yh-ganzhi">' + (yearly.ganzhi || '') + '年 · ' +
      (yearly.shengxiao || '') + '年</div>' +
      '<div class="yh-meta">纳音 ' + (yearly.nayin || '') +
      ' · 流年十神 ' + (yearly.shishen || '') + '</div>' +
      '<div class="yh-theme">' + (yearly.theme || '') + '</div>';
  }

  function _renderTaisui(taisui) {
    var el = $('#taisui-card');
    if (!el) return;
    if (!taisui || !taisui.has_conflict) {
      el.style.display = 'none';
      return;
    }
    el.style.display = '';
    var typesHtml = (taisui.types || []).map(function (t) {
      return '<span class="ts-type">' + t.type + '</span>';
    }).join('');
    var descsHtml = (taisui.types || []).map(function (t) {
      return '<div class="ts-desc">' + t.type + '：' + t.desc + '</div>';
    }).join('');

    el.innerHTML =
      '<div class="ts-title">⚠ 犯太岁提醒</div>' +
      '<div>' + typesHtml + '</div>' +
      descsHtml;
  }

  function _renderYearlyScore(yearly, yr) {
    var el = $('#yearly-score-hero');
    if (!el) return;
    var scores = yearly.scores || {};
    var overall = scores.overall || 65;
    var stars = FortuneUtils.scoreToStars(overall);
    var overview = yr.yearly_overview || '';

    el.innerHTML =
      '<div class="score-number">' + overall + '</div>' +
      '<div class="score-label">年度综合运势</div>' +
      '<div class="score-stars">' + stars + '</div>' +
      (overview ? '<div class="score-overview">' + overview + '</div>' : '');
  }

  function _renderYearlyKeywords(keywords) {
    var el = $('#yearly-keywords');
    if (!el) return;
    if (!keywords || keywords.length === 0) {
      el.innerHTML = '';
      return;
    }
    el.innerHTML = keywords.map(function (kw) {
      return '<span class="yk-tag">' + kw + '</span>';
    }).join('');
  }

  function _renderYearlyFortuneGrid(yearly, yr) {
    var el = $('#yearly-fortune-grid');
    if (!el) return;
    var scores = yearly.scores || {};
    var items = [
      { name: '事业运', key: 'career', readingKey: 'yearly_career', icon: '💼' },
      { name: '财运', key: 'wealth', readingKey: 'yearly_wealth', icon: '💰' },
      { name: '感情运', key: 'love', readingKey: 'yearly_love', icon: '❤️' },
      { name: '健康运', key: 'health', readingKey: 'yearly_health', icon: '🏃' },
    ];
    var html = '';
    items.forEach(function (item) {
      var score = scores[item.key] || 65;
      var text = yr[item.readingKey] || '';
      html += '<div class="fortune-card">' +
        '<div class="fc-header">' +
        '<span class="fc-name">' + item.icon + ' ' + item.name + '</span>' +
        '<span class="fc-score">' + score + '</span>' +
        '</div>' +
        '<div class="fc-text">' + text + '</div>' +
        '</div>';
    });
    el.innerHTML = html;
  }

  function _renderYearlyCautions(yearly, yr) {
    var el = $('#yearly-cautions-card');
    if (!el) return;
    var cautions = yearly.cautions || [];
    if (cautions.length === 0) {
      el.style.display = 'none';
      return;
    }
    el.style.display = '';
    var html = '<div class="cc-title">年度注意事项</div>';
    cautions.forEach(function (c) {
      html += '<div class="cc-item">' + c + '</div>';
    });
    var advice = yr.yearly_advice || '';
    if (advice) {
      html += '<div class="cc-item" style="margin-top:8px;font-weight:500;color:var(--gold-dark);">' +
        '💡 ' + advice + '</div>';
    }
    el.innerHTML = html;
  }

  function _renderMonthlyChart(monthly) {
    var el = $('#monthly-chart');
    if (!el) return;
    if (!monthly || monthly.length === 0) {
      el.innerHTML = '<p style="text-align:center;color:var(--muted);font-size:13px;">暂无数据</p>';
      return;
    }

    var maxScore = 0;
    monthly.forEach(function (m) {
      if (m.score > maxScore) maxScore = m.score;
    });
    maxScore = maxScore || 1;

    var html = '';
    monthly.forEach(function (m) {
      var pct = Math.round((m.score / (maxScore * 1.1)) * 100);
      var barClass = m.score >= 75 ? 'high' : (m.score >= 60 ? 'mid' : 'low');
      var rowClass = m.score >= 78 ? ' mc-highlight' : (m.score < 55 ? ' mc-low' : '');

      html += '<div class="mc-row' + rowClass + '">' +
        '<span class="mc-name">' + m.name + '</span>' +
        '<span class="mc-gz">' + m.ganzhi + '</span>' +
        '<div class="mc-bar-wrap"><div class="mc-bar ' + barClass +
        '" style="width:' + pct + '%"></div></div>' +
        '<span class="mc-score">' + m.score + '</span>' +
        '</div>';
    });
    el.innerHTML = html;
  }

  // ── 渲染历史列表 ──
  function renderHistory(targetId) {
    var el = document.getElementById(targetId);
    if (!el) return;
    var history = FortuneUtils.getHistory();
    var keys = Object.keys(history).sort().reverse();

    if (keys.length === 0) {
      el.innerHTML = '<p style="text-align:center;color:var(--muted);font-size:13px;padding:20px 0;">暂无记录</p>';
      return;
    }

    var isHome = targetId === 'history-list';
    var limit = isHome ? 5 : 30;
    var html = '';
    keys.slice(0, limit).forEach(function (date) {
      var item = history[date];
      var score = (item && item.daily && item.daily.scores)
        ? item.daily.scores.overall : '—';
      html += '<div class="history-item" data-date="' + date + '">' +
        '<div class="h-left"><span class="h-name">' + date + '</span></div>' +
        '<span class="h-score">' + score + '分</span>' +
        '<span class="h-arrow">›</span></div>';
    });
    el.innerHTML = html;

    if (isHome) {
      var moreBtn = document.getElementById('history-more');
      if (moreBtn) moreBtn.style.display = keys.length > 5 ? '' : 'none';
    }
  }

  return {
    showScreen: showScreen,
    showOverlay: showOverlay,
    hideOverlay: hideOverlay,
    setLoadingStep: setLoadingStep,
    renderResult: renderResult,
    renderDayun: renderDayun,
    renderYearly: renderYearly,
    renderHistory: renderHistory,
  };
})();
