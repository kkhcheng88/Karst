/* ============================================================
   Karst 運行詳情頁(KARST-032)
   ------------------------------------------------------------
   版面與元件照 KARST-015 原型第十版(已核准 v1 基線,D-023),
   數據全部經 /api/ 由庫內真實運行讀出——頁內沒有一個寫死的數字。

   左欄一個圖區,兩種形態互換:
     淨值圖   策略對 QQQ／SPY,曲線上標出有買賣的交易日(design-system 3.8)
     蠟燭圖   點一筆交易即鑽入該實體,買賣標記落在對應日期的蠟燭上(3.9)
   右欄一張卡兩個分頁:八項指標(D-020 第 8 條)、逐筆交易。
   ============================================================ */
(function () {
  'use strict';

  var el = {
    bcCrumb: document.getElementById('bc-crumb'),
    bcRun: document.getElementById('bc-run'),
    kpis: document.getElementById('kpis'),
    metricsNote: document.getElementById('metrics-note'),
    chartHost: document.getElementById('main-chart'),
    hov: document.getElementById('hovcard'),
    legend: document.getElementById('chart-legend'),
    title: document.getElementById('chart-title'),
    back: document.getElementById('chart-back'),
    winPick: document.getElementById('win-pick'),
    winFrom: document.getElementById('win-from'),
    winTo: document.getElementById('win-to'),
    winState: document.getElementById('win-state'),
    /* 以現版本重跑(KARST-052) */
    rerunOpen: document.getElementById('rerun-open'),
    rerunModal: document.getElementById('rerun-modal'),
    rerunBody: document.getElementById('rerun-body'),
    rerunGo: document.getElementById('rerun-go'),
    rerunCancel: document.getElementById('rerun-cancel'),
  };

  var state = {
    runId: null,
    detail: null,
    marksByDate: {},
    chart: null,
    mode: 'equity',
    table: null,
    /* 淨值圖上那幾條線:圖例鍵 → lightweight-charts 的線物件 */
    lines: {},
    /* 用戶在圖例收起了哪幾條。換運行、換視窗都留住——收起 QQQ 是一個看法,
       不是一次性的動作(用戶 2026-08-28:「Is it possible to turn off the
       QQQ and SPY in the chart?」)。 */
    hidden: {},
    /* 現正揀住的檢視視窗;兩個日子都是 null 即全期 */
    win: { key: 'all', from: null, to: null },
    applied: { key: 'all', from: null, to: null },
    window: null,
    seq: 0,
  };

  /* ============================================================
     小工具
     ============================================================ */
  function qs(name) {
    var m = new RegExp('[?&]' + name + '=([^&]*)').exec(location.search);
    return m ? decodeURIComponent(m[1]) : null;
  }

  function fail(message) {
    el.title.innerHTML = '<h2 style="font-size:var(--fs-md)">拿不到數據</h2>';
    el.chartHost.innerHTML =
      '<div class="drill-hint">' + KV.esc(message) + '</div>';
    el.legend.hidden = true;
  }

  /* D-035:運行詳情不再有自己的「檢視運行」選擇器,唯一入口是策略詳情頁的
     歷次運行表(或者直連 ?id=&run=)。網址一個運行都沒指名時,講清楚去哪裡揀,
     不猜一次「最近那次」出來。 */
  function noRunSelected() {
    el.title.innerHTML = '<h2 style="font-size:var(--fs-md)">未指定運行</h2>';
    el.chartHost.innerHTML =
      '<div class="drill-hint">運行詳情要由策略詳情頁的歷次運行表點入,' +
      '或者用帶 <span class="mono">?run=</span> 的連結直開。<br>' +
      '<a href="/">回策略總覽 →</a></div>';
    el.legend.hidden = true;
  }

  /* ============================================================
     檢視視窗:同一次運行揀一段日期重看(design-system 3.7)
     ------------------------------------------------------------
     頁內一個指標都不算。揀了日子只是把起訖日交給 /api/,八項指標與淨值線
     全部由薄 REST 層按那一段重出——是重看不是重跑,運行編號一個字不變。
     ============================================================ */
  var WINS = [
    { key: 'all', label: '全期' },
    { key: '1y', label: '近 1 年' },
    { key: '3y', label: '近 3 年' },
    { key: '2023', label: '2023 起' },
  ];

  function shiftYears(iso, years) {
    var d = new Date(iso + 'T00:00:00Z');
    d.setUTCFullYear(d.getUTCFullYear() - years);
    return d.toISOString().slice(0, 10);
  }

  function winParams() {
    var parts = [];
    if (state.win.from) parts.push('start=' + encodeURIComponent(state.win.from));
    if (state.win.to) parts.push('end=' + encodeURIComponent(state.win.to));
    return parts;
  }

  function setWindow(key, from, to) {
    state.win = { key: key, from: from || null, to: to || null };
    loadRun(state.runId);
  }

  function mountWinPick() {
    el.winPick.innerHTML = WINS.map(function (w) {
      return '<button type="button" data-win="' + w.key + '" aria-pressed="false">' +
        KV.esc(w.label) + '</button>';
    }).join('');

    el.winPick.addEventListener('click', function (e) {
      var b = e.target.closest('button[data-win]');
      if (!b || !state.window) return;
      var key = b.getAttribute('data-win');
      var last = state.window.runEnd;
      var from = key === 'all' ? null
        : (key === '1y' ? shiftYears(last, 1)
        : (key === '3y' ? shiftYears(last, 3) : '2023-01-01'));
      setWindow(key, from, null);
    });

    /* 自訂:揀了日子即由四個預設鍵轉為自訂,四鍵全部退選(design-system 3.7) */
    function custom() {
      var from = el.winFrom.value || null;
      var to = el.winTo.value || null;
      setWindow(from || to ? 'custom' : 'all', from, to);
    }
    el.winFrom.addEventListener('change', custom);
    el.winTo.addEventListener('change', custom);
  }

  /* 一段載回來之後,把控制列對回實際看到的那一段(伺服器會把日子貼到交易日上) */
  function syncWindow(win) {
    state.window = win;
    if (win.isFull) state.win = { key: 'all', from: null, to: null };
    state.applied = { key: state.win.key, from: state.win.from, to: state.win.to };

    var key = win.isFull ? 'all' : state.win.key;
    el.winPick.querySelectorAll('button[data-win]').forEach(function (b) {
      b.setAttribute('aria-pressed', b.getAttribute('data-win') === key ? 'true' : 'false');
    });

    el.winFrom.value = win.start;
    el.winTo.value = win.end;
    el.winFrom.min = el.winTo.min = win.runStart;
    el.winFrom.max = el.winTo.max = win.runEnd;

    el.winState.innerHTML = (win.isFull
      ? '視窗 全期'
      : '視窗 <b>' + KV.esc(win.start) + ' 至 ' + KV.esc(win.end) + '・非重跑</b>') +
      '・' + win.tradingDays + ' 個交易日' +
      (win.openingLots ? '・承接期初存貨 ' + win.openingLots + ' 注' : '');

    /* 網址記住運行與視窗,重新整理後仍是同一段;帶進來的 ?id= 也留住,
       不然直連網址那個格式(策略詳情鑽入時用的 ?id=&run=)一操作視窗就走樣 */
    var parts = (state.idQs ? ['id=' + encodeURIComponent(state.idQs)] : [])
      .concat(['run=' + encodeURIComponent(state.runId)])
      .concat(winParams());
    try { history.replaceState(null, '', location.pathname + '?' + parts.join('&')); }
    catch (e) {}
  }

  /* ============================================================
     載入一次運行
     ============================================================ */
  function loadRun(runId) {
    el.bcRun.textContent = runId;
    var token = ++state.seq;
    var parts = winParams();
    var url = '/api/runs/' + encodeURIComponent(runId) +
      (parts.length ? '?' + parts.join('&') : '');

    KV.fetchJSON(url).then(function (detail) {
      /* 期間又揀了另一次運行或另一段日子,這份作廢 */
      if (state.runId !== runId || state.seq !== token) return;
      state.detail = detail;
      state.marksByDate = {};
      detail.tradeMarks.forEach(function (m) { state.marksByDate[m.date] = m; });
      syncWindow(detail.window);

      renderIdentity(detail.run);
      renderMetrics(detail);
      renderTrades(detail);
      /* 頁尾要在畫圖之前掛好:貼屏頁的圖按「剩餘高度」量,頁尾遲一步掛上
         就會把已經量好的圖擠出版面,底部時間軸看不見。 */
      KV.mountFoot({
        snapshot: detail.run.snapshotId,
        periodFrom: detail.run.periodStart,
        periodTo: detail.run.periodEnd,
      });
      showEquity();
    }).catch(function (err) {
      if (state.seq !== token) return;
      fail('讀不到運行 ' + runId + '：' + err.message);
      /* 揀了一段揀不到的日子(例如只得一日):控制列退回上一段看得到的視窗 */
      state.win = {
        key: state.applied.key, from: state.applied.from, to: state.applied.to,
      };
      if (state.window) syncWindow(state.window);
    });
  }

  /* ---- 運行身份:版本與快照全頁只在這個晶片講一次(已裁畫面原則第 3 條) ---- */
  function renderIdentity(run) {
    /* 頂層導覽不再有「運行詳情」一項(D-035):運行頁掛在「策略詳情」之下,
       所以現頁標的是那一項,不是自己。回上層改由麵包屑與現役身份晶片承擔。 */
    KV.mountNav('/strategy', { snapshot: run.snapshotId, asOf: run.periodEnd });
    if (el.bcCrumb) {
      el.bcCrumb.innerHTML = KV.breadcrumb([
        { label: '策略詳情' },
        { label: run.strategyName, href: '/strategy?id=' + encodeURIComponent(run.strategyName) },
        { label: '運行' },
      ]);
    }
    /* 運行讀到了才開放重跑:未知道當前取值之前,彈窗沒有東西可以預填 */
    if (el.rerunOpen) el.rerunOpen.hidden = false;

    var factors = run.factors.map(function (f) {
      return KV.esc(f.name) + ' v' + f.versionNo;
    }).join('<span class="dim">・</span>') || '<span class="dim">—</span>';

    var params = Object.keys(run.paramValues).sort().map(function (k) {
      return KV.esc(k) + '=' + KV.esc(run.paramValues[k]);
    }).join('<span class="dim">・</span>') || '<span class="dim">—</span>';

    KV.runChip({
      ver: run.strategyName + ' v' + run.strategyVersionNo,
      snapshot: run.snapshotId,
      stale: { stale: run.isStale },
      warnText: (run.staleReasons || []).join('・'),
      rows: [
        { k: '運行編號', v: KV.esc(run.runId) },
        { k: '策略版本', v: KV.esc(run.strategyName) + ' v' + run.strategyVersionNo +
            '<span class="dim">・' + KV.esc(run.strategyType) + '</span>' },
        { k: '參數集', v: KV.esc(run.paramSetName) + ' v' + run.paramSetVersionNo +
            '<span class="dim">・' + KV.esc(run.rebalanceCadence) + '</span>' },
        { k: '因子版本', v: factors },
        { k: '參數', v: params },
        { k: '數據快照', v: KV.esc(run.snapshotId) },
        { k: '期間', v: run.periodStart + ' 至 ' + run.periodEnd +
            '<span class="dim">・' + run.tradingDays + ' 個交易日</span>' },
        { k: '引擎', v: KV.esc(run.engineName) + ' ' + KV.esc(run.engineVersion) },
      ],
    });
  }

  /* ============================================================
     以現版本重跑(KARST-052)
     ------------------------------------------------------------
     彈窗照 KARST-015 原型 run.html 那一個:同一個標題、同一段血統說明、
     同一塊 .lineage。原型只示意,這裡真的會跑。

     三件事在這裡講清楚,免得日後有人以為畫面在做運算:
       1. 每格預填的是**當前運行的取值**,不是預設值。所以整組取值原樣交回
          後端,一格都不會由前端補。
       2. 登記與執行全部在後端,而且經唯一入口。前端只負責交一份取值、
          輪詢進度、跳去結果那個運行編號。
       3. 同一組取值重跑必得同一個運行編號(運行編號是內容雜湊),所以
          「沒有改動就按重跑」不會多出一次運行——後端會照直講「沿用」。
     ============================================================ */
  var POLL_MS = 900;

  function postJSON(url, body) {
    return fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify(body),
    }).then(function (res) {
      return res.json().catch(function () { return {}; }).then(function (data) {
        if (!res.ok) throw new Error(data.error || ('HTTP ' + res.status));
        return data;
      });
    });
  }

  /* 參數一格:標籤 + 一個預填了當前取值的格 */
  function paramCell(key, value) {
    var id = 'rr-' + key.replace(/[^A-Za-z0-9_-]/g, '_');
    return '<div class="rr-cell" data-key="' + KV.esc(key) + '">' +
      '<label for="' + id + '">' + KV.esc(key) + '</label>' +
      '<input id="' + id + '" type="text" value="' + KV.esc(value) + '" ' +
        'data-current="' + KV.esc(value) + '" spellcheck="false">' +
      '</div>';
  }

  function rerunBodyHTML(run) {
    var keys = Object.keys(run.paramValues).sort();
    return '' +
      '<p>以<b>現行版本</b>重跑一次,產生一個<b>新的運行</b>,與本運行血統相連:' +
        '同一個策略、同一段期間、同一個數據快照,分別只在版本與你改動的那幾格參數。' +
        '兩個運行可以並排比較,本運行的數字不會被改寫。</p>' +
      '<p>下面每一格預填的是<b>本運行當時的取值</b>——那是當前值,不是預設值。' +
        '一格不改就按下去,得回的會是同一個運行編號(不會多出一次運行)。</p>' +
      '<div class="rr-grid">' +
        paramCell('__cadence__', run.rebalanceCadence) +
        keys.map(function (k) { return paramCell(k, run.paramValues[k]); }).join('') +
      '</div>' +
      '<p class="rr-facts">期間 <b>' + KV.esc(run.periodStart) + ' 至 ' +
        KV.esc(run.periodEnd) + '</b>・數據快照 <b>' + KV.esc(run.snapshotId) +
        '</b>・引擎 <b>' + KV.esc(run.engineName) + ' ' + KV.esc(run.engineVersion) +
        '</b>　這三件不變,所以不在這裡改。</p>' +
      '<div class="lineage">' +
        '本運行　<b>' + KV.esc(run.runId) + '</b>　' + KV.esc(run.strategyName) +
          ' v' + run.strategyVersionNo + '・' + KV.esc(run.paramSetName) +
          ' v' + run.paramSetVersionNo + '<br>' +
        '　　└─ 新運行　<b id="rr-newid">(按下去才知道)</b>' +
      '</div>' +
      '<p class="rr-facts" id="rr-state" role="status" aria-live="polite"></p>';
  }

  /* 換倉節奏那一格借用同一個格子形狀,鍵名用一個不會與參數撞名的記號 */
  function readForm() {
    var values = {};
    var cadence = '';
    el.rerunBody.querySelectorAll('.rr-cell').forEach(function (cell) {
      var key = cell.getAttribute('data-key');
      var input = cell.querySelector('input');
      var text = input.value.trim();
      var changed = text !== input.getAttribute('data-current');
      cell.classList.toggle('is-changed', changed);
      if (key === '__cadence__') cadence = text; else values[key] = text;
    });
    return { values: values, cadence: cadence };
  }

  function rerunSay(message, tone) {
    var box = document.getElementById('rr-state');
    if (!box) return;
    box.innerHTML = tone === 'bad'
      ? '<b style="color:var(--down)">' + KV.esc(message) + '</b>'
      : KV.esc(message);
  }

  function rerunBusy(on) {
    el.rerunGo.disabled = on;
    el.rerunBody.querySelectorAll('input').forEach(function (i) { i.disabled = on; });
  }

  function openRerun() {
    if (!state.detail) return;
    var run = state.detail.run;
    el.rerunBody.innerHTML = rerunBodyHTML(run);
    el.rerunGo.hidden = false;
    el.rerunGo.disabled = false;
    el.rerunCancel.textContent = '取消';
    rerunBusy(false);
    if (el.rerunModal.showModal) el.rerunModal.showModal();
  }

  /* 做完了:同一個編號就留在這一頁講一句,新編號就跳過去(畫面刷新到新運行) */
  function rerunDone(job) {
    var newId = job.runId;
    var idBox = document.getElementById('rr-newid');
    if (idBox) idBox.textContent = newId;
    if (newId && newId !== state.runId) {
      rerunSay(job.note || '跑完了,轉去新的運行…');
      location.href = '/run?run=' + encodeURIComponent(newId);
      return;
    }
    rerunSay(job.note || '同一組取值,沿用原來那個運行編號。');
    el.rerunGo.hidden = true;
    el.rerunCancel.textContent = '知道了';
  }

  function pollJob(jobId) {
    KV.fetchJSON('/api/job?id=' + encodeURIComponent(jobId)).then(function (job) {
      if (job.status === 'done') { rerunDone(job); return; }
      if (job.status === 'failed') {
        rerunSay('跑不完：' + (job.error || '不知道為什麼'), 'bad');
        rerunBusy(false);
        return;
      }
      rerunSay((job.status === 'queued' ? '排隊中' : '進行中') + '：' + (job.note || ''));
      setTimeout(function () { pollJob(jobId); }, POLL_MS);
    }).catch(function (err) {
      rerunSay('查不到進度：' + err.message, 'bad');
      rerunBusy(false);
    });
  }

  function submitRerun() {
    var form = readForm();
    rerunBusy(true);
    rerunSay('下單中…');
    postJSON('/api/rerun', {
      runId: state.runId,
      cadence: form.cadence,
      values: form.values,
    }).then(function (job) {
      pollJob(job.jobId);
    }).catch(function (err) {
      rerunSay('下不到單：' + err.message, 'bad');
      rerunBusy(false);
    });
  }

  if (el.rerunGo) el.rerunGo.addEventListener('click', submitRerun);
  if (el.rerunCancel) {
    el.rerunCancel.addEventListener('click', function () { el.rerunModal.close(); });
  }
  if (el.rerunOpen) el.rerunOpen.addEventListener('click', openRerun);
  /* 改過的格即時標出來。掛在外殼上一次就夠,彈窗內容重畫不用重新掛。 */
  if (el.rerunBody) el.rerunBody.addEventListener('input', readForm);

  /* ============================================================
     右欄一:八項指標(D-020 第 8 條,策略層四項 + 運行層四項)
     ============================================================ */
  function renderMetrics(detail) {
    var m = detail.metrics;
    var qqq = m.benchmarks.QQQ;
    var spy = m.benchmarks.SPY;

    function bench(b, key, fmt) {
      if (!b || b[key] === null || b[key] === undefined) return '無基準對照';
      return fmt(b[key]);
    }

    var vsQqq = (qqq && m.totalReturnPct !== null && qqq.totalReturnPct !== null)
      ? m.totalReturnPct - qqq.totalReturnPct : null;

    var perTurn = (m.turnover && m.turnover > 0)
      ? Math.round(252 / m.turnover) : null;

    var cells = [
      {
        l: '累計 對 QQQ',
        v: KV.pp(vsQqq),
        c: KV.cls(vsQqq),
        b: '本運行 ' + KV.pct(m.totalReturnPct),
      },
      {
        l: '年化回報',
        v: KV.pctPlain(m.annualReturnPct),
        c: KV.cls(m.annualReturnPct),
        b: 'QQQ ' + bench(qqq, 'annualReturnPct', KV.pctPlain),
      },
      {
        l: '最大回撤',
        v: KV.pctPlain(m.maxDrawdownPct),
        c: 'down',
        b: 'QQQ ' + bench(qqq, 'maxDrawdownPct', KV.pctPlain),
      },
      {
        l: '勝率 ／ 盈虧比',
        v: (m.winRatePct === null ? '—' : KV.pctPlain(m.winRatePct, 0)) + ' ／ ' +
           (m.profitLossRatio === null ? '—' : KV.fixed(m.profitLossRatio, 2)),
        c: '',
        b: '已平倉 ' + m.closedTrades + ' 筆',
      },
      {
        l: '年化超額',
        v: KV.pp(m.annualExcessPct.QQQ),
        c: KV.cls(m.annualExcessPct.QQQ),
        b: '策略減 QQQ・對 SPY ' + KV.pp(m.annualExcessPct.SPY),
      },
      {
        l: 'Sortino',
        v: m.sortino === null ? '—' : KV.fixed(m.sortino, 2),
        c: '',
        b: '無風險利率 ' + KV.pctPlain(m.riskFreeRatePct),
      },
      {
        l: '平均持倉日數',
        v: m.averageHoldingDays === null ? '—' : KV.fixed(m.averageHoldingDays, 1) + ' 日',
        c: '',
        b: '交易日計・已平倉 ' + m.closedTrades + ' 筆',
      },
      {
        l: '換手率',
        v: m.turnover === null ? '—' : KV.fixed(m.turnover, 2) + ' 轉／年',
        c: '',
        b: perTurn ? '約每 ' + perTurn + ' 個交易日換足一轉' : '按成交金額對淨值計',
      },
    ];

    el.kpis.innerHTML = cells.map(function (c) {
      return '<div class="mcell">' +
        '<div class="dc-l">' + c.l + '</div>' +
        '<div class="dc-v ' + c.c + '">' + c.v + '</div>' +
        '<div class="dc-b">' + c.b + '</div>' +
      '</div>';
    }).join('');

    /* 口徑會變的那幾項:全期註「本次運行紀錄」,揀了視窗註「視窗內重算」
       (design-system 3.7)。承接回來的期初存貨要講清楚,否則勝率同持倉日數
       會被讀成「這一段開的倉」。 */
    var win = detail.window;
    var basis = win.isFull
      ? '本次運行紀錄'
      : '視窗內重算・非重跑' +
        (win.openingLots ? '・承接視窗前已開的 ' + win.openingLots + ' 注' : '');

    el.metricsNote.textContent =
      '全部指標由 ' + m.start + ' 至 ' + m.end + ' 這段期間計出(' + m.tradingDays +
      ' 個交易日・' + basis + ')・基準 QQQ 與 SPY 皆為買入持有・已平倉 ' +
      m.closedTrades + ' 筆。' +
      (spy ? '' : ' 該數據快照沒有 SPY,少一條基準。');
  }

  /* ============================================================
     右欄二:逐筆交易(整頁唯一容許的內部捲軸 —— 表格本質上就是長)
     ============================================================ */
  function renderTrades(detail) {
    var host = document.getElementById('trades-table');
    host.innerHTML = '';
    state.table = KV.sortableTable({
      mount: '#trades-table',
      minWidth: '560px',
      defaultSort: 'entryDate',
      defaultDir: 'desc',
      rows: detail.trades,
      rowKey: function (t) { return t.id; },
      emptyText: '這次運行沒有已平倉的交易。',
      onRowClick: function (t) { state.table.select(t.id); openTrade(t); },
      cols: [
        { key: 'symbol', label: '代號', width: '62px',
          get: function (t) { return t.symbol; },
          render: function (t) {
            return '<span class="mono" title="' + KV.esc(t.name) + '">' +
              KV.esc(t.symbol) + '</span>';
          } },
        { key: 'entryDate', label: '進場日', width: '86px',
          get: function (t) { return Date.parse(t.entryDate); },
          render: function (t) { return '<span class="mono dim">' + t.entryDate + '</span>'; } },
        { key: 'exitDate', label: '出場日', width: '86px',
          get: function (t) { return Date.parse(t.exitDate); },
          render: function (t) { return '<span class="mono dim">' + t.exitDate + '</span>'; } },
        { key: 'holdDays', label: '持倉日', width: '56px', cls: 'num',
          get: function (t) { return t.holdDays; },
          render: function (t) { return t.holdDays; } },
        { key: 'profit', label: '損益', width: '84px', cls: 'num',
          get: function (t) { return t.profit; },
          render: function (t) {
            return '<span class="' + KV.cls(t.profit) + '">' +
              (t.profit > 0 ? '+' : '') + KV.money(t.profit) + '</span>';
          } },
        { key: 'retPct', label: '報酬率', width: '74px', cls: 'num',
          get: function (t) { return t.retPct; },
          render: function (t) {
            return '<span class="' + KV.cls(t.retPct) + '">' + KV.pct(t.retPct) + '</span>';
          } },
      ],
      foot: function (rows) {
        return '<span>共 ' + rows.length + ' 筆已平倉交易</span>' +
          '<span>點一行:左邊換蠟燭圖</span>';
      },
    });
  }

  function goTab(id) {
    var b = document.getElementById(id);
    if (b && b.getAttribute('aria-selected') !== 'true') b.click();
  }

  /* ============================================================
     圖區
     ============================================================ */
  function disposeChart() {
    var dead = state.chart;
    state.chart = null;
    el.chartHost.innerHTML = '';      /* 先脫離版面,舊圖的量度就不會再影響新圖 */
    /* 圖表庫在自己的下一格畫面仍會摸一次舊圖,所以等兩格才真正拆掉,免得它擲錯 */
    if (dead) {
      requestAnimationFrame(function () {
        requestAnimationFrame(function () { try { dead.remove(); } catch (e) {} });
      });
    }
  }

  function chartBox() {
    var box = document.createElement('div');
    el.chartHost.appendChild(box);
    return box;
  }

  function availH() {
    return Math.max(200, Math.round(el.chartHost.parentElement.clientHeight));
  }

  /* ---- 滑過成交浮層(design-system 3.8) ---- */
  var HOV_MAX = 8;

  function hideHover() { el.hov.hidden = true; }

  function showHover(pt, mark) {
    var rows = mark.buys.map(function (t) {
      return { side: '買', cls: 'b', sym: t.sym, shares: t.shares, px: t.px };
    }).concat(mark.sells.map(function (t) {
      return { side: '沽', cls: 's', sym: t.sym, shares: t.shares, px: t.px };
    }));

    var shown = rows.slice(0, HOV_MAX);
    el.hov.innerHTML =
      '<div class="hov-date"><span>' + mark.date + '</span><span class="dim">' +
        KV.esc(mark.label) + '</span></div>' +
      shown.map(function (x) {
        return '<div class="hov-row">' +
          '<span class="hov-side ' + x.cls + '">' + x.side + '</span>' +
          '<span class="hov-sym">' + KV.esc(x.sym) + '</span>' +
          '<span class="dim">' + KV.num(x.shares, 0) + ' 股</span>' +
          '<span>' + KV.fixed(x.px, 2) + '</span>' +
        '</div>';
      }).join('') +
      (rows.length > HOV_MAX
        ? '<div class="hov-more">另 ' + (rows.length - HOV_MAX) + ' 筆</div>' : '') +
      '<div class="hov-hint">點一下即跳到右邊那幾筆</div>';

    el.hov.hidden = false;

    /* 貼住游標,但不准越出圖區 */
    var box = el.hov.parentElement.getBoundingClientRect();
    var w = el.hov.offsetWidth, h = el.hov.offsetHeight;
    var x = pt.x + 16, y = pt.y + 16;
    if (x + w > box.width - 6) x = pt.x - w - 16;
    if (y + h > box.height - 6) y = Math.max(6, box.height - h - 6);
    el.hov.style.left = Math.max(6, x) + 'px';
    el.hov.style.top = Math.max(6, y) + 'px';
  }

  /* ============================================================
     圖例:每項可點,收起／放回那一條線
     ------------------------------------------------------------
     用戶 2026-08-28 原話:「Is it possible to turn off the QQQ and SPY in
     the chart?」。三條線一視同仁——QQQ、SPY、策略淨值都收得起,線一收,
     圖表自己會重新配刻度,剩下那幾條看得更清楚。

     收起只是「不畫」,不是「不算」:右邊八項指標照舊由 /api/ 按同一段日子
     交出來,一個數字都不會因為收起一條線而變。
     ============================================================ */
  /* 圖表色照 design-system 1.7:策略青、QQQ 紫、SPY 灰 */
  var STRATEGY_COLOR = '#26a69a';
  var BENCH_COLOR = { QQQ: '#b07de0', SPY: '#7d869c' };
  /* 策略那條線在圖例上的鍵。基準用自己的代號(QQQ／SPY),策略沒有代號,
     用一個不可能與代號相撞的字。 */
  var STRATEGY_LINE = '__strategy__';

  function benchColor(name) { return BENCH_COLOR[name] || '#7d869c'; }

  function legendButton(key, color, inner) {
    var on = !state.hidden[key];
    return '<button type="button" data-line="' + KV.esc(key) + '" ' +
      'aria-pressed="' + (on ? 'true' : 'false') + '" ' +
      'title="點一下收起這條線,再點放回來">' +
      '<i style="background:' + color + '"></i>' + inner + '</button>';
  }

  function toggleLine(key) {
    var on = !!state.hidden[key];   /* 本來收起了,點一下就是放回來 */
    state.hidden[key] = !on;
    if (state.lines[key]) state.lines[key].applyOptions({ visible: on });
    el.legend.querySelectorAll('button[data-line]').forEach(function (b) {
      if (b.getAttribute('data-line') !== key) return;
      b.setAttribute('aria-pressed', on ? 'true' : 'false');
    });
  }

  el.legend.addEventListener('click', function (e) {
    var b = e.target.closest('button[data-line]');
    if (b) toggleLine(b.getAttribute('data-line'));
  });

  /* ---- 淨值走勢 + 交易日標記 ---- */
  function showEquity() {
    var detail = state.detail;
    if (!detail) return;
    var series = detail.series;
    var m = detail.metrics;

    state.mode = 'equity';
    disposeChart();
    hideHover();
    el.back.hidden = true;
    el.legend.hidden = false;

    var benchNames = Object.keys(series.benchmarks);
    el.title.innerHTML =
      '<h2 style="font-size:var(--fs-md)">組合淨值 對 ' +
        (benchNames.join('／') || '(無基準)') + '</h2>';

    var legendParts = [
      legendButton(STRATEGY_LINE, STRATEGY_COLOR,
        KV.esc(series.strategy.label) +
        ' <b class="' + KV.cls(m.totalReturnPct) + '">' + KV.pct(m.totalReturnPct) +
        '</b>・年化 <b>' + KV.pctPlain(m.annualReturnPct) + '</b>'),
    ];
    benchNames.forEach(function (name) {
      var b = series.benchmarks[name];
      legendParts.push(
        legendButton(name, benchColor(name),
          KV.esc(name) + ' <b>' + KV.pct(b.totalReturnPct) + '</b>・年化 <b>' +
          KV.pctPlain(b.annualReturnPct) + '</b>')
      );
    });
    el.legend.innerHTML = legendParts.join('');

    var box = chartBox();
    var chart = KV.makeChart(box, availH());
    state.chart = chart;
    state.lines = {};

    /* 基準先畫,策略最後畫,策略那條才壓在最上(粗 2,基準幼 1) */
    benchNames.slice().reverse().forEach(function (name) {
      var b = series.benchmarks[name];
      var line = chart.addLineSeries({
        color: benchColor(name), lineWidth: 1,
        priceLineVisible: false, lastValueVisible: false,
        visible: !state.hidden[name],
      });
      line.setData(KV.zip(b.dates, b.values));
      state.lines[name] = line;
    });

    var strategy = chart.addLineSeries({
      color: STRATEGY_COLOR, lineWidth: 2,
      priceLineVisible: false, lastValueVisible: false,
      visible: !state.hidden[STRATEGY_LINE],
    });
    strategy.setData(KV.zip(series.strategy.dates, series.strategy.values));
    state.lines[STRATEGY_LINE] = strategy;

    /* 交易日標記:淨買入綠上箭、淨賣出紅下箭、同日一買一沽用中性圓點 */
    strategy.setMarkers(detail.tradeMarks.map(function (mk) {
      return {
        time: mk.date,
        position: mk.side === 'sell' ? 'aboveBar' : 'belowBar',
        color: mk.side === 'buy' ? '#26a69a' : (mk.side === 'sell' ? '#ef5350' : '#8f9bb3'),
        shape: mk.side === 'buy' ? 'arrowUp' : (mk.side === 'sell' ? 'arrowDown' : 'circle'),
        text: '',
      };
    }));

    /* 貼合全段,左右各多留幾格,免得頭尾的年份標籤被切走(design-system 3.8)。
       範圍由資料長度直接算——這一刻圖表可能仍未量度好闊度,回讀 visible range
       會拿到一個未定的細範圍,反而把圖縮成得幾個月。 */
    var points = series.strategy.dates.length;
    chart.timeScale().fitContent();
    try {
      chart.timeScale().setVisibleLogicalRange({ from: -12, to: points + 4 });
    } catch (e) {
      chart.timeScale().fitContent();
    }

    chart.subscribeCrosshairMove(function (p) {
      var iso = KV.timeToISO(p.time);
      var mark = iso && state.marksByDate[iso];
      if (!mark || !p.point) { hideHover(); return; }
      showHover(p.point, mark);
    });

    chart.subscribeClick(function (p) {
      var iso = KV.timeToISO(p.time);
      var mark = iso && state.marksByDate[iso];
      if (!mark) return;
      goTab('tab-t');
      highlightDate(mark);
    });
  }

  /* 圖上點一個交易日 → 高亮那幾筆並捲到視線內 */
  function highlightDate(mark) {
    var ids = {};
    mark.buys.concat(mark.sells).forEach(function (t) { if (t.id) ids[t.id] = true; });

    var first = null;
    document.querySelectorAll('#trades-table tbody tr[data-rk]').forEach(function (tr) {
      var on = !!ids[tr.getAttribute('data-rk')];
      tr.classList.toggle('is-hit', on);
      if (on && !first) first = tr;
    });
    if (first) first.scrollIntoView({ block: 'nearest' });
  }

  /* ---- 鑽入:同一個圖區換成該實體的蠟燭圖(design-system 3.9) ---- */
  function openTrade(trade) {
    var runId = state.runId;
    el.title.innerHTML =
      '<h2 style="font-size:var(--fs-md)">' + KV.esc(trade.symbol) + '　載入中……</h2>';

    /* 蠟燭圖同樣按這一段取數:K 線與買賣標記聚焦視窗,不會扯出段外那幾年 */
    var query = ['symbol=' + encodeURIComponent(trade.symbol)].concat(winParams());
    KV.fetchJSON('/api/runs/' + encodeURIComponent(runId) +
                 '/candles?' + query.join('&'))
      .then(function (data) {
        if (state.runId !== runId) return;
        drawCandles(trade, data);
      })
      .catch(function (err) {
        fail('畫不到 ' + trade.symbol + ' 的蠟燭圖：' + err.message);
        el.back.hidden = false;
      });
  }

  function drawCandles(trade, data) {
    state.mode = 'stock';
    disposeChart();
    hideHover();
    el.back.hidden = false;
    el.legend.hidden = true;

    el.title.innerHTML =
      '<h2 style="font-size:var(--fs-md)">' + KV.esc(data.symbol) + '　' +
        KV.esc(data.name) +
        (data.kind ? ' <span class="tag" style="margin-left:var(--s-2)">' +
          KV.esc(data.kind) + '</span>' : '') + '</h2>' +
      '<div class="section-note">' + KV.esc(trade.id) + '・' +
        trade.entryDate + ' 進場 ' + KV.fixed(trade.entryPrice, 2) +
        ' → ' + trade.exitDate + ' 出場 ' + KV.fixed(trade.exitPrice, 2) +
        '・持倉 ' + trade.holdDays + ' 日' +
        '　損益 <b class="' + KV.cls(trade.profit) + '">' +
        (trade.profit > 0 ? '+' : '') + KV.money(trade.profit) +
        '(' + KV.pct(trade.retPct) + ')</b>' +
        /* 揀了視窗:這裡數的是這一段之內的筆數,不是整次運行 */
        '<span class="dim">・該實體在' +
        (state.window && !state.window.isFull ? '這一段' : '本次運行') +
        '共 ' + data.trades.length + ' 筆</span></div>';

    var box = chartBox();
    var chart = KV.makeChart(box, availH());
    state.chart = chart;

    /* 蠟燭色照 design-system 3.9:升綠跌紅,實體、邊框、上下影同色 */
    var candles = chart.addCandlestickSeries({
      upColor: '#26a69a', downColor: '#ef5350',
      borderUpColor: '#26a69a', borderDownColor: '#ef5350',
      wickUpColor: '#26a69a', wickDownColor: '#ef5350',
    });
    candles.setData(data.candles);
    candles.priceScale().applyOptions({ scaleMargins: { top: 0.06, bottom: 0.26 } });

    if (data.volumes.length) {
      var closeByTime = {};
      var openByTime = {};
      data.candles.forEach(function (c) {
        closeByTime[c.time] = c.close;
        openByTime[c.time] = c.open;
      });
      var vol = chart.addHistogramSeries({
        priceFormat: { type: 'volume' }, priceScaleId: '',
        color: 'rgba(122,134,156,.4)', priceLineVisible: false, lastValueVisible: false,
      });
      vol.setData(data.volumes.map(function (v) {
        var up = closeByTime[v.time] >= openByTime[v.time];
        return {
          time: v.time, value: v.value,
          color: up ? 'rgba(38,166,154,.35)' : 'rgba(239,83,80,.35)',
        };
      }));
      vol.priceScale().applyOptions({ scaleMargins: { top: 0.82, bottom: 0 } });
    }

    /* 該次運行在這隻身上的全部買賣,落在對應日期的蠟燭上。
       與淨值圖不同,蠟燭圖上的標記帶文字(design-system 3.9)。 */
    candles.setMarkers(data.markers.map(function (mk) {
      return {
        time: mk.time,
        position: mk.side === 'buy' ? 'belowBar' : 'aboveBar',
        color: mk.side === 'buy' ? '#26a69a' : '#ef5350',
        shape: mk.side === 'buy' ? 'arrowUp' : 'arrowDown',
        text: mk.text,
      };
    }));

    /* 視域對準點中那一筆,前後各留一段,好讓那筆買賣看得清楚;
       全段資料照舊在圖上,拉得回去。 */
    var index = {};
    data.candles.forEach(function (c, i) { index[c.time] = i; });
    var from = index[trade.entryDate];
    var to = index[trade.exitDate];
    if (from !== undefined && to !== undefined) {
      var pad = Math.max(20, Math.round((to - from) * 0.6));
      var lo = Math.max(0, from - pad);
      var hi = Math.min(data.candles.length - 1, to + pad);
      try {
        chart.timeScale().setVisibleRange({
          from: data.candles[lo].time, to: data.candles[hi].time,
        });
      } catch (e) { chart.timeScale().fitContent(); }
    } else {
      chart.timeScale().fitContent();
    }
  }

  el.back.addEventListener('click', function () {
    showEquity();
    if (state.table) state.table.select(null);
  });

  /* ============================================================
     開機(D-035:唯一入口是策略詳情頁的歷次運行表,或者直連
     ?id=&run=;這一頁不再自己列運行清單,`run` 沒帶到就講清楚去哪揀)
     ============================================================ */
  KV.initTabs('.tabs');
  KV.mountNav('/strategy', {});
  mountWinPick();

  /* 網址帶住的視窗:重新整理、或者把連結傳開,看到的仍然是同一段 */
  var fromQs = qs('start');
  var toQs = qs('end');
  if (fromQs || toQs) state.win = { key: 'custom', from: fromQs, to: toQs };

  state.idQs = qs('id');
  var wanted = qs('run');
  if (!wanted) {
    noRunSelected();
  } else {
    state.runId = wanted;
    loadRun(wanted);
  }
})();
