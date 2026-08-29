/* ============================================================
   Karst 本機網頁殼 — 共用行為(KARST-032)
   ------------------------------------------------------------
   由 prototype/assets/app.js 移植。原型版本從 window.KARST(假數據檔)
   取數;本版一律經 fetch 向本機 REST 層取真實運行,頁內不留任何寫死數據。

   與原型的差異只有三處,全部因為「這裡不再是原型」:
     1. 導航列不再掛原型斜紋條與「原型・假數據」徽章(design-system 3.15
        明文:兩者皆屬原型專用,正式版移除);
     2. 頁尾不再宣告假數據,改為講真實數據期間與快照;
     3. 導航列的頁連結只列已建成的畫面,不列尚未建成那幾頁的死連結。
   顏色與字級一律靠 static/style.css 的 token,本檔不寫任何色值——
   唯一例外是圖表庫要求以字面值傳入的那組(design-system 1.7 已登記在案)。
   ============================================================ */
(function (global) {
  'use strict';

  /* ---------------- 取數 ---------------- */
  function fetchJSON(url) {
    return fetch(url, { headers: { Accept: 'application/json' } }).then(function (res) {
      if (!res.ok) {
        return res.text().then(function (body) {
          var msg = body;
          try { msg = JSON.parse(body).error || body; } catch (e) {}
          throw new Error('HTTP ' + res.status + '：' + msg);
        });
      }
      return res.json();
    });
  }

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
  function fixed(v, digits) {
    if (v === null || v === undefined || isNaN(v)) return '—';
    return Number(v).toFixed(digits === undefined ? 2 : digits);
  }
  function money(v) {
    if (v === null || v === undefined || isNaN(v)) return '—';
    return (v < 0 ? '-' : '') + '$' + Math.abs(Math.round(v)).toLocaleString('en-US');
  }
  function moneyShort(v) {
    if (v === null || v === undefined || isNaN(v)) return '—';
    var a = Math.abs(v);
    if (a >= 1e6) return (v < 0 ? '-' : '') + '$' + (a / 1e6).toFixed(2) + 'M';
    if (a >= 1e3) return (v < 0 ? '-' : '') + '$' + (a / 1e3).toFixed(1) + 'K';
    return money(v);
  }
  function cls(v) { return v > 0 ? 'up' : (v < 0 ? 'down' : 'dim'); }
  function esc(s) {
    if (s === null || s === undefined) return '';
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
  /* 兩頁齊列(D-036:策略詳情改為一頁四段——門面成績→熱力圖帶→正式運行表→
     選股漏斗,參數掃描降為熱力圖帶的下鑽層,連同運行詳情(D-035)一併移出
     頂層導覽,只經策略詳情頁點入,直連網址照舊保留:運行詳情 ?id=&run=、
     參數掃描 ?id=&sweep=&layer=&cell=)。 */
  var PAGES = [
    { href: '/', label: '策略總覽' },
    { href: '/strategy', label: '策略詳情' },
  ];

  function mountNav(active, meta) {
    meta = meta || {};
    var links = PAGES.map(function (p) {
      var cur = p.href === active ? ' aria-current="page"' : '';
      return '<a class="nav-link" href="' + p.href + '"' + cur + '>' + p.label + '</a>';
    }).join('');

    var html =
      '<nav class="nav">' +
        '<div class="brand">' +
          '<span class="brand-mark">KARST</span>' +
        '</div>' +
        '<div class="nav-links">' + links + '</div>' +
        '<div class="nav-meta">' +
          (meta.snapshot ? '<span>數據快照 ' + esc(meta.snapshot) + '</span>' : '') +
          (meta.asOf ? '<span>截至 ' + esc(meta.asOf) + '</span>' : '') +
          '<div id="nav-identity"></div>' +
        '</div>' +
      '</nav>';

    var host = document.getElementById('nav-host');
    if (host) host.innerHTML = html;
  }

  /**
   * 運行身份晶片:版本與快照只在導航列出現一次,詳情收在浮層裡
   * (design-system 3.2、已裁畫面原則第 3 條)。
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
              (cfg.actionLabel
                ? '<button class="btn btn-primary idpop-act" id="idchip-act">' +
                    esc(cfg.actionLabel) + '</button>'
                : '')
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

  function mountFoot(meta) {
    var host = document.getElementById('foot-host');
    if (!host) return;
    meta = meta || {};
    var period = (meta.periodFrom && meta.periodTo)
      ? '數據期間 ' + esc(meta.periodFrom) + ' 至 ' + esc(meta.periodTo) + '　'
      : '';
    host.innerHTML =
      '<div class="foot">' +
        period +
        (meta.snapshot ? '數據快照 ' + esc(meta.snapshot) + '　' : '') +
        '數字全部由本機庫內一次真實回測運行讀出,無任何寫死數值。<br>' +
        '圖表 TradingView Lightweight Charts v4.2.3(Apache-2.0,本地載入)' +
      '</div>';
  }

  /* ---------------- 因子用的細行圖(0-100 固定刻度) ---------------- */
  function factorSpark(el, values, color) {
    if (!el || !values || !values.length) return;
    var W = 100, H = 100;
    var d = '';
    for (var i = 0; i < values.length; i++) {
      var x = values.length === 1 ? 0 : (i / (values.length - 1)) * W;
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

  /* ---------------- 熱力圖色階(design-system 1.8) ----------------
     單一正本:參數掃描頁的熱圖(3.13)與策略詳情頁的熱力圖帶(3.16,KARST-079)
     同一套色階、同一套判讀色,不各自各寫一份。五個停站是唯一登記在案的形態,
     顏色不是唯一載體——裁決另以形狀(邊框/斜紋/最佳格代表格籤)區分。 */
  var HEAT_STOPS = [
    [0.00, [23, 33, 54]],
    [0.30, [26, 78, 96]],
    [0.55, [30, 132, 121]],
    [0.78, [116, 178, 88]],
    [1.00, [240, 196, 76]]
  ];
  function heatColor(t) {
    t = Math.max(0, Math.min(1, t));
    for (var i = 0; i < HEAT_STOPS.length - 1; i++) {
      if (t >= HEAT_STOPS[i][0] && t <= HEAT_STOPS[i + 1][0]) {
        var f = (t - HEAT_STOPS[i][0]) / (HEAT_STOPS[i + 1][0] - HEAT_STOPS[i][0]);
        var a = HEAT_STOPS[i][1], b = HEAT_STOPS[i + 1][1];
        return 'rgb(' + Math.round(a[0] + (b[0] - a[0]) * f) + ',' +
          Math.round(a[1] + (b[1] - a[1]) * f) + ',' +
          Math.round(a[2] + (b[2] - a[2]) * f) + ')';
      }
    }
    return 'rgb(240,196,76)';
  }
  function heatTextColor(t) { return t > 0.62 ? '#06121f' : '#dfe4ee'; }

  /* ---------------- lightweight-charts ---------------- */
  /* 這裡的字面值即 design-system 1.7「圖表專用色」那一格,逐個對得上 token。
     圖表庫的選項不吃 CSS 變數,只能傳字面值——正本仍然是 design-system.md。 */
  function chartOptions(extra) {
    var LC = global.LightweightCharts;
    var base = {
      layout: {
        background: { type: LC.ColorType.Solid, color: 'transparent' },
        textColor: '#7d869c',                    /* --text-3 / --bench-spy */
        fontFamily: getComputedStyle(document.body).fontFamily,
        fontSize: 11,                            /* --fs-xs */
        attributionLogo: false,
      },
      grid: {
        vertLines: { color: 'rgba(38,44,59,.55)' },   /* --line 半透明 */
        horzLines: { color: 'rgba(38,44,59,.55)' },
      },
      rightPriceScale: { borderColor: '#262c3b', scaleMargins: { top: 0.12, bottom: 0.12 } },
      /* minBarSpacing 由原型的 0.4 放寬到 0.02:真實運行是十一年、2929 個交易日,
         0.4 之下 fitContent() 壓不進面板闊度,左邊幾年會被靜靜切走——圖例寫住
         「基期 100 ＝ 2015-01-02」而圖上根本見不到那一年。 */
      timeScale: { borderColor: '#262c3b', rightOffset: 4, minBarSpacing: 0.02 },
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

  /* lightweight-charts 的 time 可能是字串或 {year,month,day},一律轉回 ISO 日期 */
  function timeToISO(tm) {
    if (typeof tm === 'string') return tm;
    if (tm && tm.year) {
      return tm.year + '-' + String(tm.month).padStart(2, '0') + '-' + String(tm.day).padStart(2, '0');
    }
    return null;
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
    try { history.replaceState(null, '', url); }
    catch (e) { location.hash = s; }
  }

  /**
   * 令一個表格可排序,排序狀態看得見(aria-sort)並寫入網址。
   * cols: [{key, label, cls, get(row), render(row)}]
   * 可選:rowKey(row)、onRowClick(row)、selected。
   * 回傳 {render, select, setRows}。
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

      var body = rows.length ? rows.map(function (r) {
        var key = cfg.rowKey ? cfg.rowKey(r) : null;
        var attrs = '';
        if (key !== null && key !== undefined) attrs += ' data-rk="' + esc(key) + '"';
        var klass = [];
        if (cfg.onRowClick) klass.push('row-clickable');
        if (key !== null && String(key) === String(selected)) klass.push('is-picked');
        if (klass.length) attrs += ' class="' + klass.join(' ') + '"';
        if (cfg.onRowClick) attrs += ' tabindex="0" role="button" aria-pressed="' +
          (String(key) === String(selected) ? 'true' : 'false') + '"';
        return '<tr' + attrs + '>' + cfg.cols.map(function (c) {
          return '<td class="' + (c.cls || '') + '">' + c.render(r) + '</td>';
        }).join('') + '</tr>';
      }).join('')
        /* 空狀態照 design-system 3.15 現行做法:表身一行居中灰字 */
        : '<tr><td colspan="' + cfg.cols.length + '" class="dim" ' +
            'style="text-align:center;padding:var(--s-6) 0">' +
            esc(cfg.emptyText || '沒有可顯示的資料。') + '</td></tr>';

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
      setRows: function (rows) { cfg.rows = rows; selected = null; render(); },
    };
  }

  /* ---------------- 麵包屑(D-035) ---------------- */
  /**
   * 鑽取層回上層的路徑。parts:[{label, href}],href 略去即該節是純文字
   * (通常是最後一節——正在看的這一頁,或者無獨立網址的分節標籤)。
   * 回傳的是 <nav class="breadcrumb"> 之內那一截,掛的頁自己提供外層 <nav>
   * 容器(id 由該頁決定),好讓靜態 HTML 與其餘頁的麵包屑同一個殼。
   */
  function breadcrumb(parts) {
    return parts.map(function (p, i) {
      var sep = i > 0 ? '<span>／</span>' : '';
      var last = i === parts.length - 1;
      var seg = p.href
        ? '<a href="' + esc(p.href) + '">' + esc(p.label) + '</a>'
        : '<span' + (last ? ' aria-current="page"' : '') + '>' + esc(p.label) + '</span>';
      return sep + seg;
    }).join('');
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

  global.KV = {
    fetchJSON: fetchJSON,
    pct: pct, pctPlain: pctPlain, pp: pp, num: num, fixed: fixed,
    money: money, moneyShort: moneyShort, cls: cls, esc: esc, truncate: truncate,
    mountNav: mountNav, mountFoot: mountFoot, runChip: runChip, breadcrumb: breadcrumb,
    factorSpark: factorSpark, heatColor: heatColor, heatTextColor: heatTextColor,
    makeChart: makeChart, chartOptions: chartOptions, zip: zip, timeToISO: timeToISO,
    sortableTable: sortableTable, initTabs: initTabs,
  };
})(window);
