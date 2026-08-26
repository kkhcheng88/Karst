/* ============================================================
   Karst 原型共用行為
   ------------------------------------------------------------
   純前端、無外部請求。所有數據來自 assets/data.js(window.KARST)。
   ============================================================ */
(function (global) {
  'use strict';

  var K = global.KARST || {};

  /* ---------------- 格式化 ---------------- */
  function pct(v, digits) {
    if (v === null || v === undefined || isNaN(v)) return '—';
    var d = digits === undefined ? 1 : digits;
    return (v > 0 ? '+' : '') + v.toFixed(d) + '%';
  }
  function pctPlain(v, digits) {
    if (v === null || v === undefined || isNaN(v)) return '—';
    return v.toFixed(digits === undefined ? 1 : digits) + '%';
  }
  function pp(v, digits) {
    if (v === null || v === undefined || isNaN(v)) return '—';
    var d = digits === undefined ? 1 : digits;
    return (v > 0 ? '+' : '') + v.toFixed(d) + 'pp';
  }
  function num(v, digits) {
    if (v === null || v === undefined || isNaN(v)) return '—';
    return v.toFixed(digits === undefined ? 2 : digits);
  }
  function money(v) {
    if (v === null || v === undefined || isNaN(v)) return '—';
    return (v < 0 ? '-' : '') + '$' + Math.abs(Math.round(v)).toLocaleString('en-US');
  }
  function moneyShort(v) {
    var a = Math.abs(v);
    if (a >= 1e6) return (v < 0 ? '-' : '') + '$' + (a / 1e6).toFixed(2) + 'M';
    if (a >= 1e3) return (v < 0 ? '-' : '') + '$' + (a / 1e3).toFixed(1) + 'K';
    return money(v);
  }
  function cls(v) { return v > 0 ? 'up' : (v < 0 ? 'down' : 'dim'); }
  function esc(s) {
    return String(s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }
  /* 中文截字用全形省略號,不用英文三點 */
  function truncate(s, n) {
    s = String(s);
    return s.length > n ? s.slice(0, n) + '……' : s;
  }

  /* ---------------- 頂欄 ---------------- */
  /* 個股兩個變體已併入運行詳情頁,存檔連結留在該頁頁尾,不再佔主導航 */
  var PAGES = [
    { href: 'index.html', label: '策略總覽' },
    { href: 'strategy.html', label: '趨勢波段' },
    { href: 'run.html', label: '運行詳情' },
    { href: 'sweep.html', label: '參數掃描' },
  ];

  function mountNav(active) {
    var links = PAGES.map(function (p) {
      var cur = p.href === active ? ' aria-current="page"' : '';
      return '<a class="nav-link" href="' + p.href + '"' + cur + '>' + p.label + '</a>';
    }).join('');

    var html =
      '<div class="proto-stripe"></div>' +
      '<nav class="nav">' +
        '<div class="brand">' +
          '<span class="brand-mark">KARST</span>' +
          '<span class="proto-badge">原型・假數據</span>' +
        '</div>' +
        '<div class="nav-links">' + links + '</div>' +
        '<div class="nav-meta">' +
          '<span>數據快照 ' + esc(K.meta.snapshot) + '</span>' +
          '<span>截至 ' + esc(K.meta.asOf) + '</span>' +
          '<div id="nav-identity"></div>' +
        '</div>' +
      '</nav>';

    var host = document.getElementById('nav-host');
    if (host) host.innerHTML = html;
  }

  /**
   * 運行身份晶片:版本與快照只在導航列出現一次,詳情收在浮層裡。
   * cfg = { ver, snapshot, stale, rows:[{k,v}], warnText, actionLabel, onAction }
   */
  function runChip(cfg) {
    var host = document.getElementById('nav-identity');
    if (!host) return;
    var bad = !!(cfg.stale && cfg.stale.stale);

    host.innerHTML =
      '<div class="idchip-wrap">' +
        '<button type="button" class="idchip' + (bad ? ' is-stale' : '') + '" ' +
          'id="idchip-btn" aria-expanded="false" aria-controls="idchip-pop" ' +
          'title="本次運行綁定的版本與數據快照">' +
          '<span class="idchip-v">' + esc(cfg.ver) + '</span>' +
          '<span class="idchip-dot">・</span>' +
          '<span class="idchip-s">' + esc(cfg.snapshot) + '</span>' +
          (bad ? '<span class="idchip-warn" aria-label="綁定的版本已經落後">⚠</span>' : '') +
        '</button>' +
        '<div class="idchip-pop" id="idchip-pop" hidden>' +
          '<div class="idpop-head">運行身份</div>' +
          cfg.rows.map(function (r) {
            return '<div class="idpop-row"><span class="idpop-k">' + esc(r.k) + '</span>' +
              '<span class="idpop-v">' + r.v + '</span></div>';
          }).join('') +
          (bad
            ? '<div class="idpop-warn"><span class="stale-badge">舊版本</span>' +
                '<span>' + esc(cfg.warnText || '') + '</span></div>' +
              '<button class="btn btn-primary idpop-act" id="idchip-act">' +
                esc(cfg.actionLabel || '') + '</button>'
            : '') +
        '</div>' +
      '</div>';

    var wrap = host.firstChild;
    var btn = document.getElementById('idchip-btn');
    var pop = document.getElementById('idchip-pop');
    var pinned = false, timer = null;

    function show() { clearTimeout(timer); pop.hidden = false; btn.setAttribute('aria-expanded', 'true'); }
    function hide() { if (pinned) return; pop.hidden = true; btn.setAttribute('aria-expanded', 'false'); }

    wrap.addEventListener('mouseenter', show);
    wrap.addEventListener('mouseleave', function () { timer = setTimeout(hide, 160); });
    btn.addEventListener('click', function () {
      pinned = !pinned;
      if (pinned) show(); else { pinned = false; hide(); }
    });
    document.addEventListener('click', function (e) {
      if (!wrap.contains(e.target)) { pinned = false; hide(); }
    });
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') { pinned = false; hide(); }
    });

    var act = document.getElementById('idchip-act');
    if (act && cfg.onAction) act.addEventListener('click', cfg.onAction);
  }

  function mountFoot() {
    var host = document.getElementById('foot-host');
    if (!host) return;
    host.innerHTML =
      '<div class="foot">' +
        '<b style="color:var(--warn)">原型・假數據</b>　' +
        '此頁全部數字為合成假數據,僅供判斷版面與資訊層次之用,不代表任何真實回測結果。' +
        '個股與持倉代號皆屬虛構,不對應任何真實標的。基準 QQQ／SPY 沿用真實名稱,但價格序列同樣是假的。<br>' +
        '數據期間 ' + esc(K.meta.periodFrom) + ' 至 ' + esc(K.meta.periodTo) +
        '(' + K.meta.years + ' 年)・數據快照 ' + esc(K.meta.snapshot) +
        '・圖表 TradingView Lightweight Charts v4.2.3(Apache-2.0,本地載入)' +
      '</div>';
  }

  /* ---------------- SVG 迷你走勢 ---------------- */
  /**
   * 畫一條(或兩條)迷你淨值線。
   * series 為主線,bench 為背景基準線(可選)。
   * 用 viewBox + preserveAspectRatio="none" 拉伸,線寬靠 non-scaling-stroke 保持一致。
   */
  function sparkline(el, series, bench, opts) {
    opts = opts || {};
    var W = 100, H = 100, pad = 4;
    var all = bench && bench.length ? series.concat(bench) : series;
    var min = Math.min.apply(null, all);
    var max = Math.max.apply(null, all);
    var span = (max - min) || 1;

    function path(vals) {
      var n = vals.length;
      var d = '';
      for (var i = 0; i < n; i++) {
        var x = (i / (n - 1)) * W;
        var y = H - pad - ((vals[i] - min) / span) * (H - pad * 2);
        d += (i === 0 ? 'M' : 'L') + x.toFixed(2) + ' ' + y.toFixed(2);
      }
      return d;
    }

    var up = series[series.length - 1] >= series[0];
    var color = opts.color || (up ? 'var(--up)' : 'var(--down)');
    var fillId = 'sg' + Math.random().toString(36).slice(2, 8);

    var areaD = path(series) +
      'L' + W + ' ' + H + 'L0 ' + H + 'Z';

    var svg =
      '<svg viewBox="0 0 ' + W + ' ' + H + '" preserveAspectRatio="none" aria-hidden="true" focusable="false">' +
        '<defs><linearGradient id="' + fillId + '" x1="0" y1="0" x2="0" y2="1">' +
          '<stop offset="0%" stop-color="' + color + '" stop-opacity=".22"/>' +
          '<stop offset="100%" stop-color="' + color + '" stop-opacity="0"/>' +
        '</linearGradient></defs>' +
        '<path d="' + areaD + '" fill="url(#' + fillId + ')"/>' +
        (bench && bench.length
          ? '<path d="' + path(bench) + '" fill="none" stroke="var(--bench-spy)" stroke-width="1" ' +
            'stroke-dasharray="3 2.5" vector-effect="non-scaling-stroke" opacity=".85"/>'
          : '') +
        '<path d="' + path(series) + '" fill="none" stroke="' + color + '" stroke-width="1.6" ' +
          'stroke-linejoin="round" stroke-linecap="round" vector-effect="non-scaling-stroke"/>' +
      '</svg>';

    el.innerHTML = svg;
  }

  /* 因子用的細行圖(0-100 固定刻度) */
  function factorSpark(el, values, color) {
    var W = 100, H = 100;
    var d = '';
    for (var i = 0; i < values.length; i++) {
      var x = (i / (values.length - 1)) * W;
      var y = H - (Math.max(0, Math.min(100, values[i])) / 100) * H;
      d += (i === 0 ? 'M' : 'L') + x.toFixed(2) + ' ' + y.toFixed(2);
    }
    el.innerHTML =
      '<svg viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true" focusable="false">' +
        '<line x1="0" y1="50" x2="100" y2="50" stroke="var(--line)" stroke-width="1" vector-effect="non-scaling-stroke"/>' +
        '<path d="' + d + '" fill="none" stroke="' + color + '" stroke-width="1.4" ' +
          'vector-effect="non-scaling-stroke" stroke-linejoin="round"/>' +
      '</svg>';
  }

  /* ---------------- lightweight-charts ---------------- */
  function chartOptions(extra) {
    var LC = global.LightweightCharts;
    var base = {
      layout: {
        background: { type: LC.ColorType.Solid, color: 'transparent' },
        textColor: '#7d869c',
        fontFamily: getComputedStyle(document.body).fontFamily,
        fontSize: 11,
        attributionLogo: false,   /* 細圖上會遮住線,關掉 */
      },
      grid: {
        vertLines: { color: 'rgba(38,44,59,.55)' },
        horzLines: { color: 'rgba(38,44,59,.55)' },
      },
      rightPriceScale: { borderColor: '#262c3b', scaleMargins: { top: 0.12, bottom: 0.12 } },
      timeScale: { borderColor: '#262c3b', rightOffset: 4, minBarSpacing: 0.4 },
      crosshair: {
        mode: LC.CrosshairMode.Normal,
        vertLine: { color: '#4a5468', width: 1, style: 2, labelBackgroundColor: '#2b3246' },
        horzLine: { color: '#4a5468', width: 1, style: 2, labelBackgroundColor: '#2b3246' },
      },
      handleScale: { axisPressedMouseMove: { time: true, price: false } },
      localization: {
        locale: 'zh-Hant',
        priceFormatter: function (p) { return p.toFixed(1); },
      },
    };
    return Object.assign(base, extra || {});
  }

  function makeChart(el, height, extra) {
    var chart = global.LightweightCharts.createChart(el, Object.assign(
      chartOptions(extra),
      { width: el.clientWidth, height: height }
    ));
    var ro = new ResizeObserver(function () {
      /* 圖已經拆走(例如換成另一張圖)之後,這裡會再響一次;響到就自己收手 */
      if (!el.isConnected) { ro.disconnect(); return; }
      try { chart.applyOptions({ width: el.clientWidth }); }
      catch (e) { ro.disconnect(); }
    });
    ro.observe(el);
    return chart;
  }

  /* 把 dates[] + values[] 併成 lightweight-charts 要的形狀 */
  function zip(dates, values) {
    var out = [];
    for (var i = 0; i < dates.length; i++) out.push({ time: dates[i], value: values[i] });
    return out;
  }

  /* ---------------- 表格排序(狀態寫入網址 hash) ---------------- */
  function readHashState() {
    var h = (location.hash || '').replace(/^#/, '');
    var out = {};
    h.split('&').forEach(function (kv) {
      if (!kv) return;
      var p = kv.split('=');
      out[decodeURIComponent(p[0])] = decodeURIComponent(p[1] || '');
    });
    return out;
  }
  function writeHashState(state) {
    var s = Object.keys(state)
      .filter(function (k) { return state[k] !== '' && state[k] != null; })
      .map(function (k) { return encodeURIComponent(k) + '=' + encodeURIComponent(state[k]); })
      .join('&');
    var url = location.pathname + location.search + (s ? '#' + s : '#');
    // file:// 下 replaceState 有機會被擋,擋到就退回直接改 hash
    try { history.replaceState(null, '', url); }
    catch (e) { location.hash = s; }
  }

  /**
   * 令一個表格可排序,排序狀態看得見(aria-sort)並寫入網址。
   * cols: [{key, label, cls, get(row), render(row)}]
   * 可選:rowKey(row) 給每行一個身分、onRowClick(row) 點行的行為、
   *       selected 目前選中那行的 rowKey(選中行會亮起)。
   * 回傳 {render, select} —— 選中另一行時叫 select(key) 重畫。
   */
  function sortableTable(cfg) {
    var host = document.querySelector(cfg.mount);
    if (!host) return;
    var state = readHashState();
    var sortKey = state[cfg.hashKey || 'sort'] || cfg.defaultSort;
    var sortDir = state[(cfg.hashKey || 'sort') + 'd'] || cfg.defaultDir || 'desc';
    var selected = cfg.selected || null;

    function render() {
      var rows = cfg.rows.slice();
      var col = cfg.cols.filter(function (c) { return c.key === sortKey; })[0];
      if (col && col.get) {
        rows.sort(function (a, b) {
          var x = col.get(a), y = col.get(b);
          if (typeof x === 'string') return sortDir === 'asc' ? x.localeCompare(y) : y.localeCompare(x);
          return sortDir === 'asc' ? x - y : y - x;
        });
      }

      var head = cfg.cols.map(function (c) {
        var aria = c.key === sortKey ? (sortDir === 'asc' ? 'ascending' : 'descending') : 'none';
        var w = c.width ? ' style="width:' + c.width + '"' : '';
        return '<th class="' + (c.cls || '') + ' sortable" data-key="' + c.key + '" ' +
          'aria-sort="' + aria + '" tabindex="0" role="button"' + w + '>' + c.label + '</th>';
      }).join('');

      var body = rows.map(function (r) {
        var key = cfg.rowKey ? cfg.rowKey(r) : null;
        var attrs = '';
        if (key !== null && key !== undefined) attrs += ' data-rk="' + esc(key) + '"';
        var klass = [];
        if (cfg.onRowClick) klass.push('row-clickable');
        if (key !== null && key === selected) klass.push('is-picked');
        if (klass.length) attrs += ' class="' + klass.join(' ') + '"';
        if (cfg.onRowClick) attrs += ' tabindex="0" role="button" aria-pressed="' +
          (key === selected ? 'true' : 'false') + '"';
        return '<tr' + attrs + '>' + cfg.cols.map(function (c) {
          return '<td class="' + (c.cls || '') + '">' + c.render(r) + '</td>';
        }).join('') + '</tr>';
      }).join('');

      host.innerHTML =
        '<div class="table-scroll' + (cfg.maxHeight ? ' table-scroll-y' : '') + '"' +
          (cfg.maxHeight ? ' style="max-height:' + cfg.maxHeight + '"' : '') + '>' +
          '<table class="kt"' + (cfg.minWidth ? ' style="min-width:' + cfg.minWidth + '"' : '') + '>' +
            '<thead><tr>' + head + '</tr></thead><tbody>' + body + '</tbody></table>' +
        '</div>' +
        (cfg.foot ? '<div class="table-foot">' + cfg.foot(rows) + '</div>' : '');

      host.querySelectorAll('th.sortable').forEach(function (th) {
        function go() {
          var k = th.getAttribute('data-key');
          if (k === sortKey) sortDir = sortDir === 'asc' ? 'desc' : 'asc';
          else { sortKey = k; sortDir = 'desc'; }
          var st = readHashState();
          st[cfg.hashKey || 'sort'] = sortKey;
          st[(cfg.hashKey || 'sort') + 'd'] = sortDir;
          writeHashState(st);
          render();
        }
        th.addEventListener('click', go);
        th.addEventListener('keydown', function (e) {
          if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); go(); }
        });
      });

      if (cfg.onRowClick) {
        host.querySelectorAll('tbody tr[data-rk]').forEach(function (tr) {
          var key = tr.getAttribute('data-rk');
          var row = null;
          for (var i = 0; i < rows.length; i++) {
            if (String(cfg.rowKey(rows[i])) === key) { row = rows[i]; break; }
          }
          function go() { cfg.onRowClick(row, key); }
          tr.addEventListener('click', go);
          tr.addEventListener('keydown', function (e) {
            if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); go(); }
          });
        });
      }
    }
    render();

    return {
      render: render,
      select: function (key) { selected = key; render(); },
    };
  }

  /* ---------------- 分頁籤 ---------------- */
  function initTabs(root) {
    var host = document.querySelector(root);
    if (!host) return;
    var btns = host.querySelectorAll('.tab-btn');
    btns.forEach(function (b) {
      b.addEventListener('click', function () {
        btns.forEach(function (o) {
          var on = o === b;
          o.setAttribute('aria-selected', on ? 'true' : 'false');
          var panel = document.getElementById(o.getAttribute('aria-controls'));
          if (panel) panel.hidden = !on;
        });
      });
    });
  }

  /* ---------------- 熱力圖配色 ---------------- */
  /* 單色系連續刻度(深藍 → 青 → 黃),同時以文字顯示數值,顏色不是唯一載體 */
  function heatColor(t) {
    t = Math.max(0, Math.min(1, t));
    var stops = [
      [0.00, [23, 33, 54]],
      [0.30, [26, 78, 96]],
      [0.55, [30, 132, 121]],
      [0.78, [116, 178, 88]],
      [1.00, [240, 196, 76]],
    ];
    for (var i = 0; i < stops.length - 1; i++) {
      if (t >= stops[i][0] && t <= stops[i + 1][0]) {
        var f = (t - stops[i][0]) / (stops[i + 1][0] - stops[i][0]);
        var a = stops[i][1], b = stops[i + 1][1];
        return 'rgb(' + Math.round(a[0] + (b[0] - a[0]) * f) + ',' +
          Math.round(a[1] + (b[1] - a[1]) * f) + ',' +
          Math.round(a[2] + (b[2] - a[2]) * f) + ')';
      }
    }
    return 'rgb(240,196,76)';
  }
  /* 深底用淺字、淺底用深字,保住對比 */
  function heatTextColor(t) { return t > 0.62 ? '#06121f' : '#dfe4ee'; }

  global.KV = {
    K: K,
    pct: pct, pctPlain: pctPlain, pp: pp, num: num,
    money: money, moneyShort: moneyShort, cls: cls, esc: esc, truncate: truncate,
    mountNav: mountNav, mountFoot: mountFoot, runChip: runChip,
    sparkline: sparkline, factorSpark: factorSpark,
    makeChart: makeChart, chartOptions: chartOptions, zip: zip,
    sortableTable: sortableTable, initTabs: initTabs,
    heatColor: heatColor, heatTextColor: heatTextColor,
  };
})(window);
