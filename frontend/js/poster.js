/**
 * Canvas 海报生成（750×1334 国风运势海报）
 */
var FortunePoster = (function () {
  'use strict';

  var W = 750, H = 1334;
  var canvas, ctx;

  function generate(data) {
    canvas = document.getElementById('poster-canvas');
    if (!canvas) return;
    canvas.width = W;
    canvas.height = H;
    canvas.style.width = '100%';
    ctx = canvas.getContext('2d');

    _drawBackground();
    _drawHeader(data);
    _drawBazi(data);
    _drawScores(data);
    _drawLucky(data);
    _drawAlmanac(data);
    _drawTips(data);
    _drawFooter();
  }

  function save() {
    if (!canvas) return;
    try {
      canvas.toBlob(function (blob) {
        if (!blob) return;
        var url = URL.createObjectURL(blob);
        var a = document.createElement('a');
        a.href = url;
        a.download = '运势海报_' + FortuneUtils.today() + '.png';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
      }, 'image/png');
    } catch (e) {
      alert('保存失败，请长按图片保存');
    }
  }

  function _drawBackground() {
    var grad = ctx.createLinearGradient(0, 0, 0, H);
    grad.addColorStop(0, '#FFF8F0');
    grad.addColorStop(0.4, '#FFFAF5');
    grad.addColorStop(1, '#F5E6D3');
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, W, H);

    ctx.strokeStyle = 'rgba(196,30,58,0.08)';
    ctx.lineWidth = 2;
    _roundRect(20, 20, W - 40, H - 40, 24);
    ctx.stroke();

    ctx.font = '600 280px "Noto Serif SC", serif';
    ctx.fillStyle = 'rgba(196,30,58,0.03)';
    ctx.textAlign = 'center';
    ctx.fillText('命', W / 2, 340);
  }

  function _drawHeader(data) {
    var daily = data.daily || {};
    ctx.font = '700 48px "Noto Serif SC", serif';
    ctx.fillStyle = '#C41E3A';
    ctx.textAlign = 'center';
    ctx.fillText('今日运势', W / 2, 120);

    ctx.font = '400 24px -apple-system, sans-serif';
    ctx.fillStyle = '#A0887A';
    var dateStr = daily.date || '';
    var lunarStr = daily.lunar_date || '';
    ctx.fillText(dateStr + (lunarStr ? '  ' + lunarStr : ''), W / 2, 160);
  }

  function _drawBazi(data) {
    var bazi = data.bazi || {};
    var pillars = bazi.pillars || {};
    var names = ['年柱', '月柱', '日柱', '时柱'];
    var keys = ['year', 'month', 'day', 'hour'];
    var startX = 95;
    var gap = 155;
    var y = 220;

    keys.forEach(function (k, i) {
      var p = pillars[k] || {};
      var x = startX + i * gap;

      ctx.font = '400 18px -apple-system, sans-serif';
      ctx.fillStyle = '#A0887A';
      ctx.textAlign = 'center';
      ctx.fillText(names[i], x, y);

      ctx.font = '700 42px "Noto Serif SC", serif';
      ctx.fillStyle = '#C41E3A';
      ctx.fillText(p.gan || '', x, y + 50);

      ctx.fillStyle = '#B8922F';
      ctx.fillText(p.zhi || '', x, y + 95);
    });
  }

  function _drawScores(data) {
    var daily = data.daily || {};
    var scores = daily.scores || {};
    var y = 400;

    ctx.font = '700 72px "Noto Serif SC", serif';
    ctx.fillStyle = '#C41E3A';
    ctx.textAlign = 'center';
    ctx.fillText(String(scores.overall || 70), W / 2, y);

    ctx.font = '400 22px -apple-system, sans-serif';
    ctx.fillStyle = '#A0887A';
    ctx.fillText('综合运势', W / 2, y + 30);

    var stars = Math.round((scores.overall || 70) / 20);
    stars = Math.max(1, Math.min(5, stars));
    var starStr = '';
    for (var i = 0; i < 5; i++) starStr += i < stars ? '★' : '☆';
    ctx.font = '400 28px -apple-system, sans-serif';
    ctx.fillStyle = '#D4A84B';
    ctx.fillText(starStr, W / 2, y + 64);

    var items = [
      { name: '事业', score: scores.career || 70 },
      { name: '财运', score: scores.wealth || 70 },
      { name: '感情', score: scores.love || 70 },
      { name: '健康', score: scores.health || 70 },
    ];
    var gridY = y + 100;
    var colW = 150;
    var startGridX = (W - colW * 4) / 2;

    items.forEach(function (item, idx) {
      var cx = startGridX + idx * colW + colW / 2;
      ctx.font = '400 20px -apple-system, sans-serif';
      ctx.fillStyle = '#A0887A';
      ctx.fillText(item.name, cx, gridY);

      ctx.font = '700 36px "Noto Serif SC", serif';
      ctx.fillStyle = '#2D1810';
      ctx.fillText(String(item.score), cx, gridY + 42);
    });
  }

  function _drawLucky(data) {
    var daily = data.daily || {};
    var lucky = daily.lucky || {};
    var y = 620;

    ctx.fillStyle = 'rgba(212,168,75,0.08)';
    _roundRect(60, y - 20, W - 120, 80, 12);
    ctx.fill();

    ctx.font = '600 22px -apple-system, sans-serif';
    ctx.fillStyle = '#B8922F';
    ctx.textAlign = 'center';
    ctx.fillText(
      '幸运色 ' + (lucky.color || '') +
      '    数字 ' + (lucky.number || '') +
      '    方位 ' + (lucky.direction || ''),
      W / 2, y + 30
    );
  }

  function _drawAlmanac(data) {
    var daily = data.daily || {};
    var alm = daily.almanac || {};
    var y = 740;

    ctx.font = '600 22px -apple-system, sans-serif';
    ctx.textAlign = 'left';
    ctx.fillStyle = '#C41E3A';
    ctx.fillText('宜', 80, y);
    ctx.fillStyle = '#5C3D2E';
    ctx.font = '400 20px -apple-system, sans-serif';
    ctx.fillText((alm.yi || []).join('  '), 120, y);

    y += 36;
    ctx.font = '600 22px -apple-system, sans-serif';
    ctx.fillStyle = '#A0887A';
    ctx.fillText('忌', 80, y);
    ctx.fillStyle = '#5C3D2E';
    ctx.font = '400 20px -apple-system, sans-serif';
    ctx.fillText((alm.ji || []).join('  '), 120, y);
  }

  function _drawTips(data) {
    var reading = data.reading || {};
    var overview = reading.overview || '';
    if (!overview) return;

    var y = 850;
    ctx.fillStyle = 'rgba(196,30,58,0.04)';
    _roundRect(60, y - 10, W - 120, 160, 12);
    ctx.fill();

    ctx.font = '400 20px -apple-system, sans-serif';
    ctx.fillStyle = '#5C3D2E';
    ctx.textAlign = 'left';
    _wrapText(overview, 80, y + 24, W - 160, 28);
  }

  function _drawFooter() {
    var y = H - 80;
    ctx.font = '400 18px -apple-system, sans-serif';
    ctx.fillStyle = '#A0887A';
    ctx.textAlign = 'center';
    ctx.fillText('仅供娱乐参考，不构成任何决策建议', W / 2, y);

    ctx.font = '600 20px "Noto Serif SC", serif';
    ctx.fillStyle = '#C41E3A';
    ctx.fillText('今日运势', W / 2, y + 36);
  }

  function _roundRect(x, y, w, h, r) {
    ctx.beginPath();
    ctx.moveTo(x + r, y);
    ctx.lineTo(x + w - r, y);
    ctx.quadraticCurveTo(x + w, y, x + w, y + r);
    ctx.lineTo(x + w, y + h - r);
    ctx.quadraticCurveTo(x + w, y + h, x + w - r, y + h);
    ctx.lineTo(x + r, y + h);
    ctx.quadraticCurveTo(x, y + h, x, y + h - r);
    ctx.lineTo(x, y + r);
    ctx.quadraticCurveTo(x, y, x + r, y);
    ctx.closePath();
  }

  function _wrapText(text, x, y, maxW, lineH) {
    var chars = text.split('');
    var line = '';
    for (var i = 0; i < chars.length; i++) {
      var test = line + chars[i];
      var w = ctx.measureText(test).width;
      if (w > maxW && line) {
        ctx.fillText(line, x, y);
        line = chars[i];
        y += lineH;
      } else {
        line = test;
      }
    }
    if (line) ctx.fillText(line, x, y);
  }

  return { generate: generate, save: save };
})();
