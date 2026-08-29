/* ============================================================
   Karst 策略詳情頁(KARST-050)
   ------------------------------------------------------------
   版面與元件照 KARST-015 原型第十版(已核准 v1 基線,D-023),
   數據全部經 /api/ 由庫內真實運行讀出——頁內沒有一個寫死的數字。

   一頁看清一套策略(D-036/D-037 定案的四段次序):
     門面成績   頭條數字(門面)+ 淨值走勢 + 選股快照,一律按代表運行算
     熱力圖帶   該策略每個參數掃描一條帶,標最佳格與代表格
     歷次運行   排名表,四個成績欄可點欄頭排序;配一段「持股分布」——
                點一行即換成該次運行最常持有的前十股票、累計報酬、行業佔比
     選股漏斗   逐層收窄,對應「選股快照」那一日

   因子敞口、因子版本兩塊(連「檢視中」的參數清單/運行編號/快照/視窗)
   KARST-080 起搬去運行詳情頁,策略頁不再顯示——見 run-view.js。

   頁內狀態:看哪一次運行(headline/圖表/選股快照,固定用代表運行,不隨
   歷次運行表點選而變)、由哪日起看、快照停在哪一日、漏斗篩到哪一層、
   持股分布正顯示歷次運行表的哪一行。
   ============================================================ */
(function () {
  'use strict';

  /* 歷次運行一頁的行數。每一行的年化/Sortino/回撤/勝率都要讀一次該運行的序列。 */
  var RUN_PAGE = 50;

  var el = {
    pageState: document.getElementById('page-state'),
    stack: document.getElementById('sp-stack'),
    name: document.getElementById('strat-name'),
    en: document.getElementById('strat-en'),
    kind: document.getElementById('strat-kind'),
    live: document.getElementById('strat-live'),
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
    heatband: document.getElementById('heatband-body'),
    heatbandNote: document.getElementById('heatband-note'),
    holdingsNote: document.getElementById('holdings-note'),
    holdingsBody: document.getElementById('holdings-body'),
  };

  var S = {
    sid: null,
    strategy: null,      /* /api/strategy 回來那份 */
    runId: null,          /* headline/圖表/選股快照那次運行:固定用代表運行 */
    detail: null,        /* /api/runs/<id> 回來那份 */
    runs: [],            /* 歷次運行:只有正式運行(D-029),失敗運行已篩走(D-034/D-040) */
    runTotal: 0,         /* 全部正式運行數(不論成敗) */
    failedCount: 0,      /* 篩走了幾多條失敗運行——只用來算「還有幾多可再載」,不顯示 */
    sweepCells: 0,       /* 這套策略有幾多格掃描格:空表那句話要講得出 */
    sort: 'annualReturnPct',   /* 歷次運行表現正按哪一欄排序(D-037 預設年化) */
    dir: 'desc',
    holdingsRunId: null,  /* 持股分布正顯示歷次運行表哪一行(D-037) */
    holdingsSeq: 0,
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
    /* 因子敞口(picks 端點連帶交回的 exposure 欄)搬去運行詳情頁顯示
       (D-037,KARST-080),這裡不再畫——與這一頁畫面上再沒有一格因子有關。 */
  }

  el.funnel.addEventListener('click', function (e) {
    var b = e.target.closest('button[data-layer]');
    if (!b) return;
    var i = Number(b.getAttribute('data-layer'));
    S.layer = (i === 0 || S.layer === i) ? 0 : i;
    renderPicks();
  });

  /* ============================================================
     六之一、熱力圖帶(D-036,KARST-079)
     ------------------------------------------------------------
     該策略每個掃描一條帶,沿用參數掃描頁(sweep.js)的熱力圖色階與最佳格/
     代表格籤(design-system 3.13),只是把方陣攤平成一行。掃描不入這一頁的
     任何狀態(S)——載入一次、畫完即止,不隨檢視運行/檢視視窗換而重載。
     ============================================================ */
  function heatbandEmpty(text) {
    el.heatband.innerHTML = '<div class="sp-empty">' + KV.esc(text) + '</div>';
    el.heatbandNote.textContent = '';
  }

  /* 兩格是不是同一組參數:逐條軸的取值都一樣(與 sweep.js 的 sameCell 同一個
     判法,這裡不跨檔共用——各自只用得著自己頁面那份 state)。 */
  function sameParams(a, b, axes) {
    if (!a || !b) return false;
    for (var i = 0; i < axes.length; i++) if (a[axes[i]] !== b[axes[i]]) return false;
    return true;
  }

  function heatbandCellHtml(data, cell, i, min, max) {
    var invalid = cell.invalid || cell.value === null || cell.value === undefined;
    var t = invalid ? 0 : (max === min ? 1 : (cell.value - min) / (max - min));
    var style = invalid ? '' : 'background:' + KV.heatColor(t);
    var isBest = data.best && sameParams(cell.params, data.best.params, data.axes);
    var isRep = data.representative && sameParams(cell.params, data.representative.params, data.axes);
    var marks = '';
    if (isBest) marks += '<i class="cell-mark best">最佳</i>';
    if (isRep) marks += '<i class="cell-mark rep">代表</i>';
    var where = data.axes.map(function (n) {
      return n + ' ' + cell.params[n];
    }).join('、');
    var label = where + '，' + data.objectiveLabel + ' ' +
      (invalid ? '不作數' : KV.fixed(cell.value, 2)) +
      (cell.verdict ? '，' + cell.verdict : '') +
      (isBest ? '，最佳格' : '') + (isRep ? '，代表格' : '');
    return '<button type="button" class="heatband-cell' + (invalid ? ' is-invalid' : '') + '" ' +
      'style="' + style + '" data-i="' + i + '" ' +
      'title="' + KV.esc(label) + '" aria-label="' + KV.esc(label) + '">' + marks + '</button>';
  }

  function heatbandBlockHtml(data) {
    var scored = data.cells.filter(function (c) {
      return c.value !== null && c.value !== undefined && !c.invalid;
    });
    var min = scored.length ? Math.min.apply(null, scored.map(function (c) { return c.value; })) : 0;
    var max = scored.length ? Math.max.apply(null, scored.map(function (c) { return c.value; })) : 1;
    var cells = data.cells.map(function (cell, i) {
      return heatbandCellHtml(data, cell, i, min, max);
    }).join('');
    return '<div class="heatband-block">' +
      '<div class="heatband-head">' +
        '<b>' + KV.esc(data.label) + '</b>' +
        (data.reference ? ' <span class="tag tag-type">對照</span>' : '') +
        '<span class="dim">' + KV.esc(data.objectiveLabel) + '・' + data.cells.length + ' 格・' +
          KV.esc(data.layer) + '</span>' +
      '</div>' +
      '<div class="heatband-scroll">' +
        '<div class="heatband-row" data-sweep="' + KV.esc(data.id) +
          '" data-layer="' + KV.esc(data.layer) + '">' + cells + '</div>' +
      '</div>' +
    '</div>';
  }

  el.heatband.addEventListener('click', function (e) {
    var btn = e.target.closest('.heatband-cell');
    if (!btn || btn.classList.contains('is-invalid')) return;
    var row = btn.closest('.heatband-row');
    if (!row) return;
    var sweepId = row.getAttribute('data-sweep');
    var layer = row.getAttribute('data-layer');
    var i = btn.getAttribute('data-i');
    /* D-036:點熱力圖某格下鑽到單格曲線,由策略頁直達參數掃描頁的第三層,
       麵包屑「策略詳情 › <策略名> › 掃描 <名> › 格」(design-system 3.6a)。 */
    location.href = '/sweep?id=' + encodeURIComponent(S.strategy.strategy.name) +
      '&sweep=' + encodeURIComponent(sweepId) +
      '&layer=' + encodeURIComponent(layer) +
      '&cell=' + encodeURIComponent(i);
  });

  function loadHeatband() {
    var name = S.strategy.strategy.name;
    heatbandEmpty('載入中……');
    KV.fetchJSON('/api/sweeps').then(function (list) {
      var mine = (list.sweeps || []).filter(function (s) {
        return !s.error && s.strategy === name;
      });
      if (!mine.length) { heatbandEmpty('尚無參數掃描'); return; }
      el.heatbandNote.textContent = mine.length + ' 個掃描';
      return Promise.all(mine.map(function (s) {
        return KV.fetchJSON('/api/sweep?id=' + encodeURIComponent(s.id))
          .catch(function () { return null; });   /* 一次掃描讀不到不拖冧整條帶 */
      })).then(function (details) {
        var ok = details.filter(function (d) { return d && d.cells && d.cells.length; });
        el.heatband.innerHTML = ok.length
          ? ok.map(heatbandBlockHtml).join('')
          : '<div class="sp-empty">尚無參數掃描</div>';
      });
    }).catch(function () {
      heatbandEmpty('讀不到參數掃描。');
    });
  }

  /* ============================================================
     七、歷次運行:排名表(D-037),點一行 = 換下面「持股分布」
     ------------------------------------------------------------
     這張表只有**正式運行**(D-029:一次掃描當一件事,掃描格不入運行清單)。
     來歷由庫身那一格講(backtest_run.origin,KARST-054),不再靠參數集名的
     前綴猜,所以這裡不用再標「掃描格」——表上一格都不會有。

     headline/圖表/選股快照固定用代表運行(S.runId,boot() 揀定就不再變)——
     這張表的行click 不再切換整頁,只切換下面「持股分布」段(S.holdingsRunId)。
     要看某次運行的完整詳情(圖表/逐筆交易/因子),click 運行編號那個連結,
     直達運行詳情頁(D-035/D-036 的「下鑽」)。
     ============================================================ */
  function noFormalRunsRow() {
    if (S.runTotal > 0) {
      /* D-034／D-040:這套策略真有正式運行(S.runTotal > 0),只是全部都是
         失敗運行——表格空白,只講一句「N 條運行全部失敗」的計數(與策略
         總覽同一句,D-040 明文定案這一句准講,不是「另有 N 條」那種展開行
         的計數)。上面圖表仍然顯示最近一次運行(即使它是失敗運行)的實際
         結果,不會是空白一片。 */
      return '<tr><td colspan="6"><div class="sp-empty">' +
          (S.failedCount || S.runTotal) + ' 條運行全部失敗' +
          '(年化回報同時低於 SPY 與 QQQ 買入持有)。' +
        '</div></td></tr>';
    }
    var cells = S.sweepCells
      ? '(庫內有 ' + S.sweepCells + ' 格掃描格)'
      : '';
    return '<tr><td colspan="6"><div class="sp-empty">' +
        '此策略未有正式運行' + cells + ';掃描結果見' +
        '<a href="/sweep">參數掃描頁</a>。' +
      '</div></td></tr>';
  }

  function renderRuns() {
    /* 排序狀態反映在欄頭(design-system 3.4 可排序表頭,沿用 th.sortable
       這個既有元件的視覺——↕/↑/↓ 由 CSS 按 aria-sort 畫,這裡只負責寫值)。 */
    el.runsBody.closest('table').querySelectorAll('th.sortable').forEach(function (th) {
      var active = th.getAttribute('data-sort') === S.sort;
      th.setAttribute('aria-sort', active ? (S.dir === 'asc' ? 'ascending' : 'descending') : 'none');
    });

    if (!S.runs.length) {
      el.runsBody.innerHTML = noFormalRunsRow();
      return;
    }
    var body = S.runs.map(function (r) {
      var selected = r.runId === S.holdingsRunId;
      return '<tr class="row-clickable' + (selected ? ' is-picked' : '') + '" ' +
          'data-run="' + KV.esc(r.runId) + '" tabindex="0" role="button" ' +
          'aria-pressed="' + (selected ? 'true' : 'false') + '" ' +
          'title="點一下:下面「持股分布」換成這一次">' +
        /* D-035:運行編號本身是連去運行詳情頁的連結(唯一入口),
           帶埋 ?id= 好讓運行頁的麵包屑與「重新整理」都認得返去邊一套策略。 */
        '<td class="mono"><a href="/run?id=' + encodeURIComponent(S.sid) + '&run=' +
          encodeURIComponent(r.runId) + '">' + KV.esc(r.runId) + '</a>' +
          (r.isActiveSetup ? ' <span class="tag tag-live">現役</span>' : '') +
          (r.isStale ? ' <span class="stale-badge">舊版本</span>' : '') + '</td>' +
        '<td class="mono">v' + r.strategyVersionNo + '</td>' +
        '<td class="num ' + KV.cls(r.annualReturnPct) + '">' + KV.pctPlain(r.annualReturnPct) + '</td>' +
        '<td class="num">' + (r.sortinoRatio === null || r.sortinoRatio === undefined
          ? '<span class="dim">—</span>' : KV.fixed(r.sortinoRatio, 2)) + '</td>' +
        '<td class="num down">' + KV.pctPlain(r.maxDrawdownPct) + '</td>' +
        '<td class="num">' + KV.pctPlain(r.winRatePct, 0) +
          '<div class="dim" style="font-size:11px">' + r.closedTrades + ' 筆</div></td>' +
      '</tr>';
    }).join('');

    /* 表上只有正式運行,一套策略通常得幾次,所以這一列平時不會出現。留住它
       是為了「共 N 次・已列 M 次」那句話:真的多過一頁時,寧可讓人見到還有,
       也不可以靜靜地只顯示頭 50 次。
       N 用「篩走失敗運行之後那個總數」(visibleTotal),不是 S.runTotal——
       失敗運行完全不顯示(D-040),連累計數都不可以露出它們存在過,
       不然「共 9 次」但表上一條都揭不出多過 1 條,一樣是講大話。 */
    var visibleTotal = S.runTotal - (S.failedCount || 0);
    var more = S.runs.length < visibleTotal
      ? '<tr><td colspan="6" style="text-align:center;padding:var(--s-4) 0">' +
          '<span class="dim">共 ' + visibleTotal + ' 次・已列 ' + S.runs.length + ' 次　</span>' +
          '<button class="btn" id="more-runs">再載 ' +
            Math.min(RUN_PAGE, visibleTotal - S.runs.length) + ' 次</button>' +
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

  /* 點一行(非連結、非按鈕):下面「持股分布」換成該次運行 */
  el.runsBody.addEventListener('click', function (e) {
    var tr = e.target.closest('tr[data-run]');
    if (!tr || e.target.closest('a') || e.target.closest('button')) return;
    selectHoldingsRun(tr.getAttribute('data-run'));
  });
  el.runsBody.addEventListener('keydown', function (e) {
    if (e.key !== 'Enter' && e.key !== ' ') return;
    var tr = e.target.closest('tr[data-run]');
    if (!tr || e.target.closest('a')) return;
    e.preventDefault();
    selectHoldingsRun(tr.getAttribute('data-run'));
  });

  /* 點欄頭:按該欄排序,再點一次反轉升降;換一欄由該欄的預設降序起
     (與 KV.sortableTable 同一套鍵盤操作:Enter/Space 一樣觸發) */
  function onSortHeaderActivate(e) {
    var th = e.target.closest('th.sortable');
    if (!th) return;
    if (e.type === 'keydown' && e.key !== 'Enter' && e.key !== ' ') return;
    if (e.type === 'keydown') e.preventDefault();
    var key = th.getAttribute('data-sort');
    if (S.sort === key) {
      S.dir = S.dir === 'desc' ? 'asc' : 'desc';
    } else {
      S.sort = key;
      S.dir = 'desc';
    }
    loadRuns(0);
  }
  var runsThead = el.runsBody.closest('table').querySelector('thead');
  runsThead.addEventListener('click', onSortHeaderActivate);
  runsThead.addEventListener('keydown', onSortHeaderActivate);

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
        /* 導航列的快照與截止日跟住代表運行走(與運行詳情頁同一個做法) */
        KV.mountNav('/strategy', {
          snapshot: S.detail.run.snapshotId,
          asOf: S.detail.run.periodEnd,
        });
        syncWindow();
        renderKpis(both[1].annualVolatilityPct);
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
      '&sort=' + encodeURIComponent(S.sort) + '&dir=' + encodeURIComponent(S.dir) +
      '&limit=' + RUN_PAGE + '&offset=' + (offset || 0);
    return KV.fetchJSON(url).then(function (page) {
      S.runTotal = page.total;
      S.failedCount = page.failedCount || 0;
      S.sweepCells = page.sweepCellTotal || 0;
      S.runs = offset ? S.runs.concat(page.items) : page.items;
      renderRuns();

      /* D-037:頁面載入時(以及每次重新排序、offset 由 0 開始那一頁)顯示
         排名第一行的持股分布;之前選定那次若仍在這一頁之內就留住它,
         不因為重新排序而無端跳走用戶正在看的那一次。 */
      if (!offset) {
        var stillThere = S.holdingsRunId &&
          S.runs.some(function (r) { return r.runId === S.holdingsRunId; });
        if (!stillThere) {
          if (S.runs.length) selectHoldingsRun(S.runs[0].runId);
          else { S.holdingsRunId = null; renderHoldingsEmpty('此策略未有正式運行,持股分布無從畫起。'); }
        }
      }
      return page;
    });
  }

  /* ============================================================
     九、持股分布(D-037,原「因子分布」):與歷次運行表配對
     ------------------------------------------------------------
     排名基準:持有日數(該實體在這次運行逐日持倉長表裡出現的交易日數),
     不是平均權重——不必逐日回讀收市價、算法簡單直驗(詞彙表「持股分布」
     條目已寫明用這個口徑)。累計報酬:該股票在此運行全部已平倉交易的合計
     損益,除以該次運行的起始資金(不是檢視視窗用的 BASE=100 顯示常數)。
     行業佔比:現有實體登記冊與宇宙檔都沒有行業欄,這裡照後端 notes 講
     清楚原因,不假裝有資料(已在票上舉手,詞彙表一併補注)。
     ============================================================ */
  function selectHoldingsRun(runId) {
    if (!runId || runId === S.holdingsRunId) return;
    S.holdingsRunId = runId;
    renderRuns();   /* 更新表上的「選中」標記 */
    loadHoldings(runId);
  }

  function renderHoldingsEmpty(text) {
    el.holdingsNote.textContent = '';
    el.holdingsBody.innerHTML = '<div class="sp-empty">' + KV.esc(text) + '</div>';
  }

  function renderHoldings(payload) {
    el.holdingsNote.textContent = '運行 ' + payload.runId + '・以持有日數排名前十';
    var rows = payload.topHoldings || [];
    if (!rows.length) {
      el.holdingsBody.innerHTML = '<div class="sp-empty">這次運行沒有持倉紀錄。</div>';
      return;
    }
    var basis = '<div class="section-note" style="padding:var(--s-2) var(--s-4) 0">' +
      '累計報酬 ＝ 該股在此運行全部已平倉交易的合計損益 ÷ 起始資金 ' +
      KV.num(payload.startingCapital, 0) + '</div>';
    var sectorNote = '<div class="section-note dim" style="padding:0 var(--s-4) var(--s-3)">' +
      KV.esc((payload.notes && payload.notes.why) || '行業佔比未有資料來源。') + '</div>';
    el.holdingsBody.innerHTML =
      '<table class="kt"><thead><tr>' +
        '<th style="width:70px">代號</th>' +
        '<th>名稱</th>' +
        '<th class="num" style="width:88px">持有日數</th>' +
        '<th class="num" style="width:96px">累計報酬</th>' +
      '</tr></thead><tbody>' +
      rows.map(function (r) {
        return '<tr>' +
          '<td class="mono">' + KV.esc(r.symbol) + '</td>' +
          '<td title="' + KV.esc(r.name) + '">' + KV.esc(KV.truncate(r.name, 28)) + '</td>' +
          '<td class="num">' + r.holdingDays + '</td>' +
          '<td class="num ' + KV.cls(r.cumulativeReturnPct) + '">' +
            (r.cumulativeReturnPct === null || r.cumulativeReturnPct === undefined
              ? '<span class="dim">—</span>' : KV.pctPlain(r.cumulativeReturnPct)) +
          '</td>' +
        '</tr>';
      }).join('') +
      '</tbody></table>' + basis + sectorNote;
  }

  function loadHoldings(runId) {
    var token = ++S.holdingsSeq;
    el.holdingsNote.textContent = '';
    el.holdingsBody.innerHTML = '<div class="sp-empty">載入中……</div>';
    KV.fetchJSON('/api/strategy/holdings?run=' + encodeURIComponent(runId))
      .then(function (payload) {
        if (token !== S.holdingsSeq) return;
        renderHoldings(payload);
      })
      .catch(function (err) {
        if (token !== S.holdingsSeq) return;
        el.holdingsBody.innerHTML = '<div class="sp-empty">讀不到持股分布:' +
          KV.esc(err.message) + '</div>';
      });
  }

  function boot() {
    showLoading('正在讀取策略');
    var wanted = qs('id');
    var wantedRun = qs('run');

    /* 只帶 ?run= 不帶 ?id= 時,端點由那一次運行反查它自己那套策略(KARST-067)。
       以前這裡不帶 run 問,端點退回「最近有運行的那一套」,於是頁頂的策略身份
       與歷次運行表指住一套策略、正在看的運行卻屬於另一套——兩種寫法看同一次
       運行,顯示不一樣,而且錯得無聲(KARST-056 順帶發現)。 */
    var ask = [];
    if (wanted) ask.push('id=' + encodeURIComponent(wanted));
    if (wantedRun) ask.push('run=' + encodeURIComponent(wantedRun));

    KV.fetchJSON('/api/strategy' + (ask.length ? '?' + ask.join('&') : ''))
      .then(function (payload) {
        S.strategy = payload;
        S.sid = payload.strategy.id;
        KV.mountNav('/strategy');
        renderHead();
        loadHeatband();

        /* 這一頁畫的是一次正式運行。只跑過參數掃描的策略在這裡是空的——空一頁
           而不講「掃描去哪裡看」,用戶會以為頁壞了(D-029、KARST-054)。 */
        if (!payload.runTotal || !payload.defaultRunId) {
          var cells = payload.sweepCellTotal || 0;
          if (cells) {
            showEmpty(
              '這套策略未有正式運行',
              '「' + payload.strategy.name + '」在庫內只有 ' + cells +
                ' 格掃描格運行,所以淨值、選股快照與持股分布都畫不出。掃描結果見',
              { href: '/sweep', text: '參數掃描頁 →' }
            );
          } else {
            showEmpty('這套策略未有運行',
              '「' + payload.strategy.name + '」在庫內未有任何回測運行,' +
              '所以淨值、選股快照與持股分布都畫不出。');
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
