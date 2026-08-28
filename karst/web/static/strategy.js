/* ============================================================
   Karst 策略詳情頁(KARST-050)
   ------------------------------------------------------------
   版面與元件照 KARST-015 原型第十版(已核准 v1 基線,D-023),
   數據全部經 /api/ 由庫內真實運行讀出——頁內沒有一個寫死的數字。

   一頁看清一套策略:
     淨值走勢   策略對 QQQ／SPY,曲線上標出有買賣的交易日(design-system 3.8)
     選股快照   某一日的範圍與持倉,連逐層收窄的漏斗(3.11、5.1)
     歷次運行   該策略每一次運行,點一行全頁換成該次(3.7)
     因子分布   這次運行的因子敞口,連因子版本鏈

   全頁只有四個狀態:看哪一次運行、由哪日起看、快照停在哪一日、漏斗篩到哪一層。
   ============================================================ */
(function () {
  'use strict';

  /* 一行擺得下的運行按鈕數目。一次參數掃描就寫幾百個運行,按鈕列擺不下;
     其餘經下面「歷次運行」表揀得到(data.py list_runs 同一個處理)。 */
  var RUN_PICK_LIMIT = 8;
  /* 歷次運行一頁的行數。每一行的年化/回撤/勝率都要讀一次該運行的序列。 */
  var RUN_PAGE = 50;

  var el = {
    pageState: document.getElementById('page-state'),
    stack: document.getElementById('sp-stack'),
    name: document.getElementById('strat-name'),
    en: document.getElementById('strat-en'),
    kind: document.getElementById('strat-kind'),
    live: document.getElementById('strat-live'),
    runPick: document.getElementById('run-pick'),
    backLive: document.getElementById('back-live'),
    config: document.getElementById('config-slim'),
    kpis: document.getElementById('kpis'),
    bench: document.getElementById('equity-bench'),
    winPick: document.getElementById('win-pick'),
    winDate: document.getElementById('win-date'),
    chartSub: document.getElementById('chart-sub'),
    chartHost: document.getElementById('equity-chart'),
    hov: document.getElementById('hovcard'),
    atPoint: document.getElementById('at-point'),
    filter: document.getElementById('picks-filter'),
    basis: document.getElementById('picks-basis'),
    funnel: document.getElementById('funnel'),
    picks: document.getElementById('picks-table'),
    runsBody: document.getElementById('runs-body'),
    factorNote: document.getElementById('factor-note'),
    factorExpo: document.getElementById('factor-expo'),
    factorHist: document.getElementById('factor-hist'),
  };

  var S = {
    sid: null,
    strategy: null,      /* /api/strategy 回來那份 */
    runId: null,
    detail: null,        /* /api/runs/<id> 回來那份 */
    runs: [],            /* 歷次運行:只有正式運行(D-029) */
    runTotal: 0,
    sweepCells: 0,       /* 這套策略有幾多格掃描格:空表那句話要講得出 */
    winKey: 'all',
    winFrom: null,
    date: null,          /* 選股快照停在哪一日 */
    layer: 0,            /* 漏斗篩到哪一層,0 = 不篩 */
    picks: null,
    marksByDate: {},
    chart: null,
    series: null,
    seq: 0,
  };

  /* ============================================================
     小工具
     ============================================================ */
  function qs(name) {
    var m = new RegExp('[?&]' + name + '=([^&]*)').exec(location.search);
    return m ? decodeURIComponent(m[1]) : null;
  }

  function shiftYears(iso, n) {
    var d = new Date(iso + 'T00:00:00Z');
    d.setUTCFullYear(d.getUTCFullYear() - n);
    return d.toISOString().slice(0, 10);
  }

  /* link:{href, text} —— 空狀態要帶得出下一步去哪裡(例:掃描結果見參數掃描頁) */
  function stateBlock(title, body, retry, link) {
    return '<div class="state-block">' +
      '<div class="state-title">' + KV.esc(title) + '</div>' +
      '<div>' + KV.esc(body) +
        (link ? ' <a href="' + KV.esc(link.href) + '">' + KV.esc(link.text) + '</a>' : '') +
      '</div>' +
      (retry ? '<button class="btn" id="state-retry">再試一次</button>' : '') +
    '</div>';
  }

  function showLoading(what) {
    el.stack.hidden = true;
    el.pageState.innerHTML =
      '<div class="sp-panel"><div class="state-block">' +
        '<div class="state-title">' + KV.esc(what) + '</div>' +
        '<div style="max-width:320px;margin:var(--s-4) auto 0;display:grid;gap:var(--s-2)">' +
          '<div class="skeleton"></div>' +
          '<div class="skeleton" style="width:72%;margin:0 auto"></div>' +
          '<div class="skeleton" style="width:48%;margin:0 auto"></div>' +
        '</div>' +
      '</div></div>';
  }

  function showFail(title, message) {
    el.stack.hidden = true;
    el.pageState.innerHTML = '<div class="sp-panel">' +
      stateBlock(title, message, true) + '</div>';
    var again = document.getElementById('state-retry');
    if (again) again.addEventListener('click', function () { boot(); });
  }

  function showEmpty(title, message, link) {
    el.stack.hidden = true;
    el.pageState.innerHTML = '<div class="sp-panel">' +
      stateBlock(title, message, false, link) + '</div>';
  }

  function ready() {
    el.pageState.innerHTML = '';
    el.stack.hidden = false;
  }

  /* 網址記住揀了哪一套策略、哪一次運行,重新整理仍是同一版 */
  function rememberUrl() {
    var parts = [];
    if (S.sid !== null && S.sid !== undefined) parts.push('id=' + encodeURIComponent(S.sid));
    if (S.runId) parts.push('run=' + encodeURIComponent(S.runId));
    try { history.replaceState(null, '', location.pathname + '?' + parts.join('&')); }
    catch (e) {}
  }

  function winQuery() {
    return S.winFrom ? '&start=' + encodeURIComponent(S.winFrom) : '';
  }

  /* ============================================================
     一、策略身份、版本沿革、因子
     ============================================================ */
  function renderHead() {
    var s = S.strategy.strategy;
    document.title = s.name + ' 策略詳情 — Karst';
    el.name.textContent = s.name;
    el.en.textContent = 'v' + s.versionNo;
    el.kind.textContent = s.typeLabel;
    /* .tag 的 display 蓋得過 [hidden] 屬性,所以一律用 style 收起 */
    el.kind.style.display = '';
    /* 庫內未指定現役設定就不掛這個籤——沒有的東西不擺上畫面 */
    el.live.style.display = S.strategy.activeSetup ? '' : 'none';
  }

  function renderFactors() {
    var factors = S.strategy.factors || [];
    el.factorNote.textContent = factors.length
      ? '這次運行引用 ' + factors.length + ' 個因子'
      : '這套策略未引用任何因子';

    el.factorHist.innerHTML = factors.length ? factors.map(function (f) {
      var chain = f.chain.map(function (v) {
        return '<span class="' + (v.versionNo === f.versionNo ? 'fh-cur' : '') + '" title="' +
          KV.esc(v.createdAt + '　' + (v.description || '')) + '">v' + v.versionNo + '</span>';
      }).join('<span class="fh-note"> ← </span>');
      /* 因子名寫成「族·定義」,族已經自成一欄,右邊只留定義那一截 */
      var def = String(f.name || '');
      var dot = def.indexOf('·');
      if (dot >= 0) def = def.slice(dot + 1);
      return '<div class="fh-row">' +
        '<div><span class="fh-fam">' + KV.esc(f.family) + '・</span>' +
          '<span class="fh-def">' + KV.esc(def) + '</span>' +
          (f.used ? '<span class="fh-used">現用</span>' : '') + '</div>' +
        '<div class="fh-chain">' + chain + '</div>' +
        '<div class="fh-note">' + KV.esc(f.scaleKind + '　' + (f.description || '')) + '</div>' +
      '</div>';
    }).join('') : '<div class="sp-empty">這套策略未引用任何因子。</div>';
  }

  /* 因子敞口:每一格因子由哪一個對象承載、佔多少比重(詞彙表「因子敞口」) */
  function renderExposure() {
    var rows = (S.picks && S.picks.exposure) || [];
    if (!rows.length) {
      el.factorExpo.innerHTML = '<div class="sp-empty">這一日沒有持倉,敞口是空的。</div>';
      return;
    }
    var top = Math.max.apply(null, rows.map(function (r) { return r.weightPct || 0; }));
    var scale = top > 0 ? top : 1;
    el.factorExpo.innerHTML = rows.map(function (r) {
      var w = r.weightPct || 0;
      var label = r.family || r.symbol || '—';
      return '<div class="factor-row" title="' +
          KV.esc((r.factorName || r.name || '') + '　' + (r.symbol || '')) + '">' +
        '<span class="factor-name">' + KV.esc(label) + '</span>' +
        '<span class="factor-bar-track">' +
          '<span class="factor-bar-fill" style="width:' +
            (w / scale * 100).toFixed(1) + '%;background:var(--accent)"></span>' +
        '</span>' +
        '<span class="factor-score">' + w.toFixed(0) + '%</span>' +
      '</div>';
    }).join('') +
    '<div class="section-note" style="padding:var(--s-2) var(--s-4) 0">' +
      '按 ' + KV.esc(S.picks.date) + ' 收工時的持倉市值計,現金 ' +
      KV.pctPlain(Math.max(0, S.picks.cashWeightPct || 0)) + '</div>';
  }

  /* ============================================================
     二、檢視運行(頁頂按鈕列 + 設定薄列)
     ============================================================ */
  function renderRunPick() {
    var shown = S.runs.slice(0, RUN_PICK_LIMIT);
    /* 正在看的那一次若不在頭幾個之內,補上去——不能有揀了但見不到的狀態 */
    var inShown = shown.some(function (r) { return r.runId === S.runId; });
    if (!inShown) {
      var hit = S.runs.filter(function (r) { return r.runId === S.runId; })[0];
      if (hit) shown = [hit].concat(shown.slice(0, RUN_PICK_LIMIT - 1));
    }

    el.runPick.innerHTML = shown.map(function (r) {
      return '<button type="button" data-run="' + KV.esc(r.runId) + '" ' +
        'aria-pressed="' + (r.runId === S.runId ? 'true' : 'false') + '" ' +
        'title="' + KV.esc(r.runId + '・' + r.paramSetName + ' v' + r.paramSetVersionNo) + '">' +
        KV.esc(r.runId.slice(4, 12)) +
        (r.isActiveSetup ? '<span class="rp-live">現役</span>' : '') +
      '</button>';
    }).join('') +
    (S.runTotal > shown.length
      ? '<span class="section-note">共 ' + S.runTotal + ' 次・其餘在下面「歷次運行」揀</span>'
      : '');

    var active = S.runs.filter(function (r) { return r.isActiveSetup; })[0];
    el.backLive.hidden = !active || active.runId === S.runId;
  }

  /* 參數區顯示的是**驅動器設定**,不是四隻 ETF 的比例(D-029:比例是每個換倉日
     由驅動器算出的輸出,不是參數;要看比例就看右邊選股快照與下面因子分布)。 */
  var DRIVER_LABELS = [
    ['driver', '訊號'],
    ['macro_series', '訊號來源'],
    ['lookback_days', '回望期'],
    ['lookback_months', '回望期'],
    ['fallback', '退路'],
    ['mode', '模式'],
    ['tilt', '傾斜'],
  ];
  var CADENCE = { daily: '日度', weekly: '週度', monthly: '月度', quarterly: '季度' };
  var RATIO_KEY = /^weight_/;              /* 四隻 ETF 的比例:D-029 訂明是輸出 */
  var WARMUP_KEY = /^warmup_/;             /* 熱身期:是可掃描參數(詞彙表「熱身期」) */

  function chip(k, v) {
    return '<span class="chip"><span class="chip-k">' + KV.esc(k) + '</span>' +
      '<span class="chip-v">' + KV.esc(v) + '</span></span>';
  }

  function renderConfig() {
    var run = S.detail.run;
    var live = !!run.isActiveSetup;
    var w = S.detail.window;
    var p = run.paramValues;
    var used = {};

    /* 一、驅動器設定:訊號、回望期、換倉節奏、退路(D-029 點名那四樣行先) */
    var chips = DRIVER_LABELS.filter(function (pair) {
      return p[pair[0]] !== undefined;
    }).map(function (pair) {
      used[pair[0]] = true;
      var v = p[pair[0]];
      if (pair[0] === 'lookback_days') v = v + ' 日';
      if (pair[0] === 'lookback_months') v = v + ' 個月';
      return chip(pair[1], v);
    }).join('');
    chips += chip('換倉節奏', CADENCE[run.rebalanceCadence] || run.rebalanceCadence);

    /* 二、熱身期:一個晶片講完,四格熱身權重不逐個攤開 */
    var warmup = Object.keys(p).filter(function (k) { return WARMUP_KEY.test(k); });
    if (warmup.length) {
      warmup.forEach(function (k) { used[k] = true; });
      chips += chip('熱身期', (p.warmup_bars ? p.warmup_bars + ' 根' : '') +
        (warmup.length > (p.warmup_bars ? 1 : 0) ? '・等權起步' : ''));
    }

    /* 三、其餘的執行設定(費用、滑點、快照);四隻 ETF 的比例一格都不出現 */
    var ratios = Object.keys(p).filter(function (k) { return RATIO_KEY.test(k); });
    chips += Object.keys(p).sort().filter(function (k) {
      return !used[k] && !RATIO_KEY.test(k);
    }).map(function (k) { return chip(k, p[k]); }).join('');

    if (ratios.length) {
      chips += '<span class="section-note">四隻 ETF 的比例由驅動器每個換倉日算出,' +
        '看右邊選股快照</span>';
    }

    var years = ((w.tradingDays - 1) / 252).toFixed(1);
    el.config.className = 'config-slim' + (live ? '' : ' is-past');
    el.config.innerHTML =
      '<span class="tag ' + (live ? 'tag-live">現役設定' : 'tag-current">檢視中') + '</span>' +
      '<span class="mono" style="font-weight:700">v' + run.strategyVersionNo +
        '・' + KV.esc(run.paramSetName) + ' v' + run.paramSetVersionNo + '</span>' +
      chips +
      '<span class="section-note mono">' + KV.esc(run.runId) + '・' + KV.esc(run.snapshotId) + '</span>' +
      '<span class="slim-win">視窗 ' +
        (w.isFull ? '全期' : '<b>' + KV.esc(w.start) + ' 起・非重跑</b>') + '</span>' +
      '<span class="slim-past">' + KV.esc(w.start) + ' 至 ' + KV.esc(w.end) +
        '・' + years + ' 年' +
        (run.isStale ? '　<span class="stale-badge">舊版本</span>' : '') + '</span>';
  }

  /* ============================================================
     三、頭條數字
     ============================================================ */
  function renderKpis(vol) {
    var m = S.detail.metrics;
    var q = (m.benchmarks && m.benchmarks.QQQ) || {};

    var items = [
      { l: '累計報酬', v: KV.pct(m.totalReturnPct), c: KV.cls(m.totalReturnPct),
        b: 'QQQ ' + KV.pct(q.totalReturnPct) },
      { l: '年化', v: KV.pctPlain(m.annualReturnPct), c: KV.cls(m.annualReturnPct),
        b: 'QQQ ' + KV.pctPlain(q.annualReturnPct) },
      { l: '最大回撤', v: KV.pctPlain(m.maxDrawdownPct), c: 'down',
        b: 'QQQ ' + KV.pctPlain(q.maxDrawdownPct) },
      { l: '波幅', v: KV.pctPlain(vol), c: '', b: '日度年化' },
      { l: 'Sortino', v: KV.fixed(m.sortino), c: '',
        b: '無風險 ' + KV.pctPlain(m.riskFreeRatePct) },
      { l: '勝率', v: KV.pctPlain(m.winRatePct, 0), c: '',
        b: '盈虧比 ' + KV.fixed(m.profitLossRatio, 1) },
      { l: '交易筆數', v: String(m.closedTrades), c: '',
        b: '平均持倉 ' + KV.fixed(m.averageHoldingDays, 0) + ' 日' },
    ];
    el.kpis.innerHTML = items.map(function (k) {
      return '<div class="kpi">' +
        '<div class="kpi-label">' + KV.esc(k.l) + '</div>' +
        '<div class="kpi-value ' + k.c + '">' + KV.esc(k.v) + '</div>' +
        '<div class="kpi-basis">' + KV.esc(k.b) + '</div>' +
      '</div>';
    }).join('');

    var s = S.detail.series;
    var bench = Object.keys(s.benchmarks);
    el.bench.innerHTML =
      '<span><i style="background:#26a69a"></i>' + KV.esc(s.strategy.label) +
        ' <b class="' + KV.cls(m.totalReturnPct) + '">' + KV.pct(m.totalReturnPct) + '</b></span>' +
      bench.map(function (t) {
        var colour = t === 'QQQ' ? '#b07de0' : '#7d869c';
        return '<span><i style="background:' + colour + '"></i>' + KV.esc(t) +
          ' <b>' + KV.pct(s.benchmarks[t].totalReturnPct) + '</b></span>';
      }).join('');

    el.chartSub.innerHTML =
      '<span><span class="up">▲</span> 買・<span class="down">▼</span> 沽・滑過看成交・點日期換快照</span>' +
      '<span class="mono">基期 ' + s.base + ' ＝ ' + KV.esc(S.detail.window.start) + '</span>' +
      '<span class="mono">' + S.detail.tradeMarks.length + ' 個交易日有買賣</span>';
  }

  /* ============================================================
     四、檢視視窗
     ============================================================ */
  var WINS = [
    { key: 'all', label: '全期' },
    { key: '1y', label: '近 1 年' },
    { key: '3y', label: '近 3 年' },
    { key: '2023', label: '2023 起' },
  ];
  el.winPick.innerHTML = WINS.map(function (w) {
    return '<button type="button" data-win="' + w.key + '" aria-pressed="false">' +
      KV.esc(w.label) + '</button>';
  }).join('');

  el.winPick.addEventListener('click', function (e) {
    var b = e.target.closest('button[data-win]');
    if (!b || !S.detail) return;
    var key = b.getAttribute('data-win');
    var last = S.detail.window.runEnd;
    S.winKey = key;
    S.winFrom = key === 'all' ? null
      : (key === '1y' ? shiftYears(last, 1)
      : (key === '3y' ? shiftYears(last, 3) : '2023-01-01'));
    S.date = null;
    loadRun(S.runId);
  });

  el.winDate.addEventListener('change', function () {
    if (!this.value) return;
    S.winKey = 'custom';
    S.winFrom = this.value;
    S.date = null;
    loadRun(S.runId);
  });

  function syncWindow() {
    var w = S.detail.window;
    el.winPick.querySelectorAll('button[data-win]').forEach(function (b) {
      b.setAttribute('aria-pressed', b.getAttribute('data-win') === S.winKey ? 'true' : 'false');
    });
    el.winDate.value = w.start;
    el.winDate.min = w.runStart;
    el.winDate.max = w.runEnd;
  }

  /* ============================================================
     五、淨值圖:三條線 + 買賣標記 + 懸停成交
     ============================================================ */
  function hideHover() { el.hov.hidden = true; }

  function showHover(pt, mark) {
    var rows = mark.buys.map(function (t) {
      return { side: '買', cls: 'b', sym: t.sym, shares: t.shares, px: t.px };
    }).concat(mark.sells.map(function (t) {
      return { side: '沽', cls: 's', sym: t.sym, shares: t.shares, px: t.px };
    }));
    var shown = rows.slice(0, 8);

    el.hov.innerHTML =
      '<div class="hov-date"><span>' + KV.esc(mark.date) + '</span>' +
        '<span class="dim">' + KV.esc(mark.label) + '</span></div>' +
      shown.map(function (x) {
        return '<div class="hov-row">' +
          '<span class="hov-side ' + x.cls + '">' + x.side + '</span>' +
          '<span class="hov-sym">' + KV.esc(x.sym) + '</span>' +
          '<span class="dim">' + KV.num(x.shares, 0) + ' 股</span>' +
          '<span>' + KV.fixed(x.px) + '</span>' +
        '</div>';
      }).join('') +
      (rows.length > 8 ? '<div class="hov-more">另 ' + (rows.length - 8) + ' 筆</div>' : '') +
      '<div class="hov-hint">點一下:快照跳到這一日</div>';

    el.hov.hidden = false;

    var box = el.hov.parentElement.getBoundingClientRect();
    var w = el.hov.offsetWidth, h = el.hov.offsetHeight;
    var x = pt.x + 16, y = pt.y + 16;
    if (x + w > box.width - 6) x = pt.x - w - 16;
    if (y + h > box.height - 6) y = Math.max(6, box.height - h - 6);
    el.hov.style.left = Math.max(6, x) + 'px';
    el.hov.style.top = Math.max(6, y) + 'px';
  }

  function drawChart() {
    var dead = S.chart;
    S.chart = null; S.series = null;
    el.chartHost.innerHTML = '';
    hideHover();
    /* 圖表庫在下一格畫面仍會摸一次舊圖,等兩格才真正拆掉 */
    if (dead) {
      requestAnimationFrame(function () {
        requestAnimationFrame(function () { try { dead.remove(); } catch (e) {} });
      });
    }

    var box = document.createElement('div');
    el.chartHost.appendChild(box);
    var chart = KV.makeChart(box, el.chartHost.clientHeight || 320);
    S.chart = chart;

    var s = S.detail.series;
    if (s.benchmarks.SPY) {
      var spy = chart.addLineSeries({
        color: '#7d869c', lineWidth: 1, priceLineVisible: false, lastValueVisible: false,
      });
      spy.setData(KV.zip(s.benchmarks.SPY.dates, s.benchmarks.SPY.values));
    }
    if (s.benchmarks.QQQ) {
      var qqq = chart.addLineSeries({
        color: '#b07de0', lineWidth: 1, priceLineVisible: false, lastValueVisible: false,
      });
      qqq.setData(KV.zip(s.benchmarks.QQQ.dates, s.benchmarks.QQQ.values));
    }
    var line = chart.addLineSeries({
      color: '#26a69a', lineWidth: 2, priceLineVisible: false, lastValueVisible: false,
    });
    line.setData(KV.zip(s.strategy.dates, s.strategy.values));
    S.series = line;

    /* 交易日標記:買綠上箭、沽紅下箭、同日一買一沽用中性圓點 */
    line.setMarkers(S.detail.tradeMarks.map(function (m) {
      return {
        time: m.date,
        position: m.side === 'sell' ? 'aboveBar' : 'belowBar',
        color: m.side === 'buy' ? '#26a69a' : (m.side === 'sell' ? '#ef5350' : '#8f9bb3'),
        shape: m.side === 'buy' ? 'arrowUp' : (m.side === 'sell' ? 'arrowDown' : 'circle'),
        text: '',
      };
    }));

    chart.timeScale().fitContent();

    chart.subscribeCrosshairMove(function (p) {
      var iso = KV.timeToISO(p.time);
      var mark = iso && S.marksByDate[iso];
      if (!mark || !p.point) { hideHover(); return; }
      showHover(p.point, mark);
    });

    /* 點日期 = 換右邊選股快照的時點,圖本身不重畫;
       右邊標題閃一下,好等「左邊點、右邊換」這個關係一眼看得出 */
    chart.subscribeClick(function (p) {
      var iso = KV.timeToISO(p.time);
      if (!iso) return;
      S.date = iso;
      S.layer = 0;
      loadPicks();
      el.atPoint.classList.remove('is-flash');
      void el.atPoint.offsetWidth;
      el.atPoint.classList.add('is-flash');
    });
  }

  /* ============================================================
     六、選股快照與漏斗
     ============================================================ */
  /* 由闊到窄各層一個色;層數按運行真有的痕跡而定,所以按位取色不夠用,
     取到盡就沿用最後一個(design-system 5.1) */
  var FUNNEL_COLOR = ['#6b7488', '#4a9eff', '#26a69a', '#f0a83c'];
  function funnelColor(i, total) {
    if (i === 0) return FUNNEL_COLOR[0];
    if (i === total - 1) return FUNNEL_COLOR[FUNNEL_COLOR.length - 1];
    return FUNNEL_COLOR[Math.min(i, FUNNEL_COLOR.length - 2)];
  }

  /* 四個狀態:持倉/入選/觀察/未過(詞彙表「選股快照」)。舊運行只答得出
     持倉/未持倉兩個,一樣落得到這張對照表 */
  var ST_CLS = {
    '持倉': 'st-hold', '入選': 'st-in', '觀察': 'st-watch',
    '未過': 'st-out', '未持倉': 'st-out'
  };

  /* 分數的位數:賠率一類個位數要看到小數,比重一類百分比看兩位就夠 */
  function scoreText(cell) {
    if (!cell || cell.value === null || cell.value === undefined) return '<span class="dim">—</span>';
    var v = cell.value;
    var digits = Math.abs(v) >= 100 ? 1 : (Math.abs(v) >= 1 ? 2 : 3);
    return KV.num(v, digits) +
      (cell.rank ? ' <span class="dim" style="font-size:11px">#' + cell.rank + '</span>' : '');
  }

  function picksTable(rows, scoreNames) {
    /* 這一頁全頁只有瀏覽器那一條捲軸(design-system 2.1),表不外加捲動框。
       欄寬是固定佈局(table-layout:fixed),分數欄一多,沒有指定寬度的「名稱」
       就會被壓到剩一個字。所以分數欄按數量收窄,其餘欄位一併收緊,
       把餘下的寬度留給名稱;名稱過長照舊省略號收尾,全名在 title 上。 */
    var names = scoreNames || [];
    var scoreW = names.length >= 3 ? 72 : (names.length === 2 ? 80 : 96);
    return '<table class="kt"><thead><tr>' +
        '<th style="width:60px">代號</th>' +
        '<th>名稱</th>' +
        '<th style="width:56px">因子</th>' +
        '<th style="width:48px">類型</th>' +
        names.map(function (n) {
          return '<th class="num" style="width:' + scoreW + 'px" title="' + KV.esc(n) + '">' +
            KV.esc(n) + '</th>';
        }).join('') +
        '<th class="num" style="width:72px">股數</th>' +
        '<th class="num" style="width:60px">權重</th>' +
        '<th style="width:64px">狀態</th>' +
      '</tr></thead><tbody>' +
      rows.map(function (r) {
        return '<tr>' +
          '<td class="mono">' + KV.esc(r.symbol) + '</td>' +
          '<td title="' + KV.esc(r.name) + '">' + KV.esc(KV.truncate(r.name, 22)) + '</td>' +
          '<td class="dim">' + KV.esc(r.family || '—') + '</td>' +
          '<td class="dim">' + KV.esc(r.kind) + '</td>' +
          names.map(function (n) {
            return '<td class="num">' + scoreText((r.scores || {})[n]) + '</td>';
          }).join('') +
          '<td class="num">' + (r.shares === null ? '<span class="dim">—</span>' : KV.num(r.shares, 0)) + '</td>' +
          '<td class="num">' + (r.weightPct === null ? '<span class="dim">—</span>' : KV.pctPlain(r.weightPct)) + '</td>' +
          '<td><span class="st ' + (ST_CLS[r.status] || 'st-out') + '">' + KV.esc(r.status) + '</span></td>' +
        '</tr>';
      }).join('') + '</tbody></table>';
  }

  function renderPicks() {
    var p = S.picks;
    el.atPoint.textContent = '快照・' + p.date;

    el.basis.innerHTML =
      '<span class="mono">' + KV.esc(p.snapshotId) + '</span>' +
      '<span>權重＝該換倉日算出的比例,按當日收市價與淨值計</span>' +
      (p.decisionDate && p.decisionDate !== p.date
        ? '<span>分數與名單出自決策日 <span class="mono">' + KV.esc(p.decisionDate) + '</span></span>'
        : '') +
      (p.notes && !p.notes.scoresAvailable
        ? '<span class="dim" title="' + KV.esc(p.notes.why) + '">未有逐股分數</span>'
        : '');

    /* 漏斗:只畫真有數據的層(design-system 5.1「到達該層」的語意) */
    var total = p.funnel.length;
    el.funnel.className = 'funnel-bar' + (S.layer ? ' has-filter' : '');
    el.funnel.innerHTML = p.funnel.map(function (f, i) {
      var prev = i ? p.funnel[i - 1].count : 0;
      var keep = i && prev ? Math.round(f.count / prev * 1000) / 10 : 100;
      return '<button type="button" class="fb-seg" data-layer="' + i + '" ' +
          'aria-pressed="' + (S.layer === i && i ? 'true' : 'false') + '" ' +
          'style="flex:' + Math.max(1, f.count) + ' 1 74px" ' +
          'title="' + KV.esc(f.label + '　' + f.hint) +
            (i ? '　點一下:只看這一層' : '　點一下:取消篩選') + '">' +
          '<div class="fb-block" style="background:' + funnelColor(i, total) + '">' +
            '<span class="fb-num">' + f.count + '<small>隻</small></span>' +
            '<span class="fb-keep">' + (i ? '剩 ' + keep + '%' : '全部') + '</span>' +
          '</div>' +
          '<div class="fb-lab">' + KV.esc(f.label) + (i ? '　−' + (prev - f.count) : '') + '</div>' +
        '</button>';
    }).join('');

    /* 篩到某一層 = 只看到達了那一層的名單;每一行自己帶住它到過哪幾層 */
    var key = S.layer ? p.funnel[S.layer].key : null;
    var rows = key
      ? p.rows.filter(function (r) { return (r.stages || []).indexOf(key) >= 0; })
      : p.rows;

    el.filter.innerHTML = S.layer
      ? '<span class="sp-filter">只看 ' + KV.esc(p.funnel[S.layer].label) + '・' + rows.length +
          ' 隻<button type="button" id="clear-filter" aria-label="取消篩選">✕</button></span>'
      : '';
    var clear = document.getElementById('clear-filter');
    if (clear) clear.addEventListener('click', function () { S.layer = 0; renderPicks(); });

    el.picks.innerHTML = rows.length
      ? picksTable(rows, p.scoreNames)
      : '<div class="sp-empty">這一層在本日沒有標的。</div>';

    renderExposure();
  }

  el.funnel.addEventListener('click', function (e) {
    var b = e.target.closest('button[data-layer]');
    if (!b) return;
    var i = Number(b.getAttribute('data-layer'));
    S.layer = (i === 0 || S.layer === i) ? 0 : i;
    renderPicks();
  });

  /* ============================================================
     七、歷次運行:點一行 = 換上面整頁
     ------------------------------------------------------------
     這張表只有**正式運行**(D-029:一次掃描當一件事,掃描格不入運行清單)。
     來歷由庫身那一格講(backtest_run.origin,KARST-054),不再靠參數集名的
     前綴猜,所以這裡不用再標「掃描格」——表上一格都不會有。
     ============================================================ */
  function noFormalRunsRow() {
    var cells = S.sweepCells
      ? '(庫內有 ' + S.sweepCells + ' 格掃描格)'
      : '';
    return '<tr><td colspan="8"><div class="sp-empty">' +
        '此策略未有正式運行' + cells + ';掃描結果見' +
        '<a href="/sweep">參數掃描頁</a>。' +
      '</div></td></tr>';
  }

  function renderRuns() {
    if (!S.runs.length) {
      el.runsBody.innerHTML = noFormalRunsRow();
      return;
    }
    var body = S.runs.map(function (r) {
      var picked = r.runId === S.runId;
      var params = Object.keys(r.paramValues).sort().map(function (k) {
        return k + '=' + r.paramValues[k];
      }).join('・');
      return '<tr class="row-clickable' + (picked ? ' is-picked' : '') + '" ' +
          'data-run="' + KV.esc(r.runId) + '" tabindex="0" role="button" ' +
          'aria-pressed="' + (picked ? 'true' : 'false') + '">' +
        '<td class="mono">' + KV.esc(r.runId) +
          (r.isActiveSetup ? ' <span class="tag tag-live">現役</span>' : '') +
          (picked && !r.isActiveSetup ? ' <span class="tag tag-current">檢視中</span>' : '') +
          (r.isStale ? ' <span class="stale-badge">舊版本</span>' : '') + '</td>' +
        '<td class="mono">v' + r.strategyVersionNo + '</td>' +
        '<td title="' + KV.esc(params) + '">' + KV.esc(KV.truncate(params, 46)) + '</td>' +
        '<td class="num ' + KV.cls(r.annualReturnPct) + '">' + KV.pctPlain(r.annualReturnPct) + '</td>' +
        '<td class="num down">' + KV.pctPlain(r.maxDrawdownPct) + '</td>' +
        '<td class="num">' + KV.pctPlain(r.winRatePct, 0) + '</td>' +
        '<td class="mono dim" title="' + KV.esc(r.snapshotId) + '">' +
          KV.esc(KV.truncate(r.snapshotId, 14)) + '</td>' +
        '<td><a href="/run?run=' + encodeURIComponent(r.runId) + '">查看 →</a></td>' +
      '</tr>';
    }).join('');

    /* 表上只有正式運行,一套策略通常得幾次,所以這一列平時不會出現。留住它
       是為了「共 N 次・已列 M 次」那句話:真的多過一頁時,寧可讓人見到還有,
       也不可以靜靜地只顯示頭 50 次。 */
    var more = S.runs.length < S.runTotal
      ? '<tr><td colspan="8" style="text-align:center;padding:var(--s-4) 0">' +
          '<span class="dim">共 ' + S.runTotal + ' 次・已列 ' + S.runs.length + ' 次　</span>' +
          '<button class="btn" id="more-runs">再載 ' +
            Math.min(RUN_PAGE, S.runTotal - S.runs.length) + ' 次</button>' +
        '</td></tr>'
      : '';

    el.runsBody.innerHTML = body + more;
    var btn = document.getElementById('more-runs');
    if (btn) {
      btn.addEventListener('click', function () {
        btn.disabled = true;
        btn.textContent = '載入中……';
        loadRuns(S.runs.length);
      });
    }
  }

  el.runsBody.addEventListener('click', function (e) {
    var tr = e.target.closest('tr[data-run]');
    if (!tr || e.target.closest('a') || e.target.closest('button')) return;
    pickRun(tr.getAttribute('data-run'));
  });
  el.runsBody.addEventListener('keydown', function (e) {
    if (e.key !== 'Enter' && e.key !== ' ') return;
    var tr = e.target.closest('tr[data-run]');
    if (!tr) return;
    e.preventDefault();
    pickRun(tr.getAttribute('data-run'));
  });

  el.runPick.addEventListener('click', function (e) {
    var b = e.target.closest('button[data-run]');
    if (!b) return;
    pickRun(b.getAttribute('data-run'));
  });
  el.backLive.addEventListener('click', function () {
    var active = S.runs.filter(function (r) { return r.isActiveSetup; })[0];
    if (active) pickRun(active.runId);
  });

  function pickRun(runId) {
    if (!runId || runId === S.runId) return;
    S.runId = runId;
    S.date = null;   /* 換運行:快照時點回到該次運行的最後一日 */
    S.layer = 0;
    loadRun(runId);
  }

  /* ============================================================
     八、載入
     ============================================================ */
  function loadPicks() {
    var runId = S.runId, token = S.seq;
    var url = '/api/strategy/picks?run=' + encodeURIComponent(runId) +
      (S.date ? '&date=' + encodeURIComponent(S.date) : '');
    return KV.fetchJSON(url).then(function (p) {
      if (S.runId !== runId || S.seq !== token) return;
      S.picks = p;
      S.date = p.date;
      renderPicks();
    }).catch(function (err) {
      if (S.seq !== token) return;
      el.picks.innerHTML = '<div class="sp-empty">讀不到選股快照:' +
        KV.esc(err.message) + '</div>';
      el.funnel.innerHTML = '';
      el.factorExpo.innerHTML = '<div class="sp-empty">讀不到因子敞口。</div>';
    });
  }

  function loadRun(runId) {
    var token = ++S.seq;
    S.runId = runId;
    var detailUrl = '/api/runs/' + encodeURIComponent(runId) +
      (S.winFrom ? '?start=' + encodeURIComponent(S.winFrom) : '');
    var volUrl = '/api/strategy/window?run=' + encodeURIComponent(runId) + winQuery();

    return Promise.all([KV.fetchJSON(detailUrl), KV.fetchJSON(volUrl)])
      .then(function (both) {
        if (S.seq !== token) return;
        S.detail = both[0];
        S.marksByDate = {};
        S.detail.tradeMarks.forEach(function (m) { S.marksByDate[m.date] = m; });

        ready();
        /* 導航列的快照與截止日跟住檢視中那一次運行走(與運行詳情頁同一個做法) */
        KV.mountNav('/strategy', {
          snapshot: S.detail.run.snapshotId,
          asOf: S.detail.run.periodEnd,
        });
        renderRunPick();
        renderConfig();
        syncWindow();
        renderKpis(both[1].annualVolatilityPct);
        renderRuns();
        KV.mountFoot({
          snapshot: S.detail.run.snapshotId,
          periodFrom: S.detail.run.periodStart,
          periodTo: S.detail.run.periodEnd,
        });
        drawChart();
        rememberUrl();
        return loadPicks();
      })
      .catch(function (err) {
        if (S.seq !== token) return;
        showFail('讀不到這次運行', runId + '：' + err.message);
        /* 揀了一段揀不到的日子(例如只得一日):視窗退回全期 */
        S.winKey = 'all';
        S.winFrom = null;
      });
  }

  function loadRuns(offset) {
    var url = '/api/strategy/runs?id=' + encodeURIComponent(S.sid) +
      '&limit=' + RUN_PAGE + '&offset=' + (offset || 0);
    return KV.fetchJSON(url).then(function (page) {
      S.runTotal = page.total;
      S.sweepCells = page.sweepCellTotal || 0;
      S.runs = offset ? S.runs.concat(page.items) : page.items;
      renderRuns();
      renderRunPick();
      return page;
    });
  }

  function boot() {
    showLoading('正在讀取策略');
    var wanted = qs('id');
    var wantedRun = qs('run');

    KV.fetchJSON('/api/strategy' + (wanted ? '?id=' + encodeURIComponent(wanted) : ''))
      .then(function (payload) {
        S.strategy = payload;
        S.sid = payload.strategy.id;
        KV.mountNav('/strategy');
        renderHead();
        renderFactors();

        /* 這一頁畫的是一次正式運行。只跑過參數掃描的策略在這裡是空的——空一頁
           而不講「掃描去哪裡看」,用戶會以為頁壞了(D-029、KARST-054)。 */
        if (!payload.runTotal || !payload.defaultRunId) {
          var cells = payload.sweepCellTotal || 0;
          if (cells) {
            showEmpty(
              '這套策略未有正式運行',
              '「' + payload.strategy.name + '」在庫內只有 ' + cells +
                ' 格掃描格運行,所以淨值、選股快照與因子敞口都畫不出。掃描結果見',
              { href: '/sweep', text: '參數掃描頁 →' }
            );
          } else {
            showEmpty('這套策略未有運行',
              '「' + payload.strategy.name + '」在庫內未有任何回測運行,' +
              '所以淨值、選股快照與因子敞口都畫不出。');
          }
          return;
        }
        return loadRuns(0).then(function () {
          return loadRun(wantedRun || payload.defaultRunId);
        });
      })
      .catch(function (err) {
        showFail('拿不到策略', err.message);
      });
  }

  boot();
})();
