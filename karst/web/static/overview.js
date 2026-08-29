/* ============================================================
   Karst 策略總覽(KARST-049)
   ------------------------------------------------------------
   照已核准的原型第十版 prototype/index.html 實作。與原型的差異只有兩處,
   兩處都因為「這裡不再是原型」:
     1. 數據一律經 /api/overview 由本機庫讀真實策略與真實運行,頁內
        一個寫死的數字都沒有;
     2. 補上原型未做的載入態與錯誤態(design-system 3.15 第 8、10 條:
        狀態塊與骨架列早已定義,原型未接上,應該補做)。
   顏色與字級一律靠 style.css 的 token,本檔不寫任何色值。
   ============================================================ */
(function () {
  'use strict';

  var COLS = 8;                       /* 表頭欄數,骨架列與空狀態要對齊 */
  var SKELETON_ROWS = 6;

  var el = {
    chips: document.getElementById('type-chips'),
    q: document.getElementById('q'),
    filterBar: document.getElementById('filter-bar'),
    filterCount: document.getElementById('filter-count'),
    body: document.getElementById('grp-body'),
    table: document.getElementById('grp-table'),
    pageFoot: document.getElementById('page-foot'),
    detail: document.getElementById('detail'),
    lastrun: document.getElementById('lastrun'),
    main: document.getElementById('fit-main'),
    state: document.getElementById('page-state'),
    stateBody: document.getElementById('page-state-body'),
  };

  var data = null;                    /* /api/overview 的回應 */
  var byId = {};
  var picked = {};                    /* 空 = 全部類型 */
  var query = '';
  var selectedId = null;
  var sortKey = 'vsBench', sortDir = 'desc';

  /* 盈虧比可以去到三位數(幾乎全贏的策略,平均蝕得極少),再帶一位小數就會
     撞爆詳情卡那一格、迫它換行。一百以上收起小數,一行放得回——這只是顯示
     精度,口徑同樣是 karst.metrics 算出來那個數。 */
  function ratio(v) {
    if (v === null || v === undefined || isNaN(v)) return '—';
    return KV.fixed(v, Math.abs(v) >= 100 ? 0 : 1);
  }

  /* ============================================================
     三態:載入中 / 空 / 錯誤
     ============================================================ */
  /* 收起一塊要改 display,不可以只靠 hidden 屬性:.fit-main 與 .filter-bar
     各自有 display:grid / display:flex,類別選擇器蓋得過瀏覽器對 [hidden]
     那條預設規則——只加 hidden 的話,錯誤態出現時骨架表仍然留在上面。 */
  function show(node, on) {
    node.hidden = !on;
    node.style.display = on ? '' : 'none';
  }

  function showLoading() {
    show(el.state, false);
    show(el.main, true);
    show(el.filterBar, true);
    var cell = '<td><div class="skeleton"></div></td>';
    var row = '<tr>' + new Array(COLS + 1).join(cell) + '</tr>';
    el.body.innerHTML = new Array(SKELETON_ROWS + 1).join(row);
    el.detail.innerHTML =
      '<div class="dc-top"><div class="skeleton" style="width:52%;height:16px"></div></div>' +
      '<div class="dc-metrics">' +
        new Array(5).join('<div class="dc-m"><div class="skeleton" style="height:32px"></div></div>') +
      '</div>';
    el.lastrun.innerHTML = '';
    el.pageFoot.textContent = '載入中……';
    el.filterCount.textContent = '';
    el.q.disabled = true;
  }

  /* 整版換成一塊:空表加半張空詳情卡,比一句話更難看得懂 */
  function showState(title, message, retry) {
    show(el.main, false);
    show(el.filterBar, false);
    show(el.state, true);
    el.stateBody.innerHTML =
      '<div class="state-block">' +
        '<div class="state-title">' + KV.esc(title) + '</div>' +
        '<div>' + KV.esc(message) + '</div>' +
        (retry ? '<button type="button" class="btn btn-primary" id="state-retry">再試一次</button>' : '') +
      '</div>';
    var btn = document.getElementById('state-retry');
    if (btn) btn.addEventListener('click', load);   /* load() 自己會回到載入態 */
  }

  /* ============================================================
     篩選:類型多選 + 名稱搜尋
     ============================================================ */
  function pickedCount() { return Object.keys(picked).length; }

  function visibleRows() {
    var q = query.trim().toLowerCase();
    return data.strategies.filter(function (s) {
      if (pickedCount() && !picked[s.type]) return false;
      if (!q) return true;
      return s.name.toLowerCase().indexOf(q) >= 0;
    });
  }

  function mountChips() {
    var counts = {};
    data.strategies.forEach(function (s) { counts[s.type] = (counts[s.type] || 0) + 1; });

    /* 庫內一套都沒有那幾類不擺出來:八個晶片有五個永遠是 0,反而礙眼 */
    var types = data.strategyTypes.filter(function (t) { return counts[t.id]; });

    var html =
      '<button type="button" class="fchip" data-t="" aria-pressed="true">全部' +
        '<span class="fchip-n">' + data.strategies.length + '</span></button>';
    html += types.map(function (t) {
      return '<button type="button" class="fchip" data-t="' + KV.esc(t.id) + '" aria-pressed="false">' +
        KV.esc(t.name) + '<span class="fchip-n">' + counts[t.id] + '</span></button>';
    }).join('');
    el.chips.innerHTML = html;

    el.chips.addEventListener('click', function (e) {
      var b = e.target.closest('button[data-t]');
      if (!b) return;
      var t = b.getAttribute('data-t');
      if (!t) picked = {};                                 /* 按「全部」= 清空篩選 */
      else if (picked[t]) delete picked[t];
      else picked[t] = true;
      paintChips();
      renderTable();
    });
  }

  function paintChips() {
    var none = pickedCount() === 0;
    el.chips.querySelectorAll('.fchip').forEach(function (b) {
      var t = b.getAttribute('data-t');
      b.setAttribute('aria-pressed', (t ? !!picked[t] : none) ? 'true' : 'false');
    });
  }

  el.q.addEventListener('input', function () {
    query = this.value;
    renderTable();
  });

  /* ============================================================
     右欄:緊湊詳情卡
     ============================================================ */
  function strategyHref(s) {
    /* strategy.js 的 boot() 只讀 ?id=(策略編號或者策略名皆收,見
       api_strategy._resolve),沒有 ?name= 這一格——舊寫法帶錯參數名,
       連結靜靜地選不中目標策略。 */
    return '/strategy?id=' + encodeURIComponent(s.name);
  }

  function renderDetail(id) {
    var s = byId[id];

    if (!s) {
      el.detail.innerHTML = '<div class="detail-empty">在左邊點一行,這裡出該策略的詳情。</div>';
      el.lastrun.innerHTML = '';
      return;
    }

    var m = s.metrics;
    if (!m) {
      /* 有這套策略,但拿不到成績(未跑過、或者序列讀不回) */
      el.detail.innerHTML =
        '<div class="dc-top">' +
          '<span class="dc-name">' + KV.esc(s.name) + '</span>' +
          '<span class="tag tag-type">' + KV.esc(s.typeName) + '</span>' +
          '<span class="dc-sum">' + KV.esc(s.versionLabel) + '</span>' +
        '</div>' +
        '<div class="detail-empty">' + KV.esc(s.note || '拿不到這套策略的成績。') + '</div>' +
        '<a class="btn btn-primary dc-cta" href="' + strategyHref(s) + '">開啟策略頁 →</a>';
      el.lastrun.innerHTML = '';
      return;
    }

    var bench = s.benchmarks || {};
    var qqq = bench[data.primaryBenchmark] || {};
    var spy = bench.SPY || {};
    var ddBetter = (m.maxDrawdownPct !== null && qqq.maxDrawdownPct !== null &&
      qqq.maxDrawdownPct !== undefined && m.maxDrawdownPct > qqq.maxDrawdownPct);
    var summary = s.versionLabel + '・' + (s.paramSummary || '');

    el.detail.innerHTML =
      '<div class="dc-top">' +
        '<span class="dc-name">' + KV.esc(s.name) + '</span>' +
        '<span class="tag tag-type">' + KV.esc(s.typeName) + '</span>' +
        '<span class="dc-sum" title="' + KV.esc(summary) + '">' + KV.esc(summary) + '</span>' +
      '</div>' +

      '<div class="dc-metrics">' +
        '<div class="dc-m">' +
          '<div class="dc-l">累計 對基準</div>' +
          '<div class="dc-v ' + KV.cls(m.vsBenchPp) + '">' + KV.pp(m.vsBenchPp) + '</div>' +
          '<div class="dc-b">本策略 ' + KV.pct(m.totalReturnPct) + '</div>' +
        '</div>' +
        '<div class="dc-m">' +
          '<div class="dc-l">年化回報</div>' +
          '<div class="dc-v ' + KV.cls(m.annualReturnPct) + '">' + KV.pctPlain(m.annualReturnPct) + '</div>' +
          '<div class="dc-b">對 ' + KV.esc(data.primaryBenchmark) + ' ' + KV.pp(m.annualExcessPp) + '</div>' +
        '</div>' +
        '<div class="dc-m">' +
          '<div class="dc-l">最大回撤</div>' +
          '<div class="dc-v down">' + KV.pctPlain(m.maxDrawdownPct) + '</div>' +
          '<div class="dc-b">' + KV.esc(data.primaryBenchmark) + ' ' + KV.pctPlain(qqq.maxDrawdownPct) +
            (qqq.maxDrawdownPct === null || qqq.maxDrawdownPct === undefined
              ? '' : '・' + (ddBetter ? '較淺' : '較深')) + '</div>' +
        '</div>' +
        '<div class="dc-m">' +
          '<div class="dc-l">勝率 ／ 盈虧比</div>' +
          '<div class="dc-v sm">' + KV.fixed(m.winRatePct, 1) +
            '<span class="dim" style="font-weight:400"> ／ </span>' +
            ratio(m.profitLossRatio) + '</div>' +
          '<div class="dc-b">共 ' + m.closedTrades + ' 筆交易</div>' +
        '</div>' +
      '</div>' +

      /* D-039/KARST-081:迷你走勢連同它的數據一併拿走,這裡只留文字對比
         (本策略／QQQ／SPY 的累計與年化),不再畫線。 */
      '<div class="bench-line" style="margin-top:var(--s-3)">' +
        '<span><i style="background:' +
          (m.totalReturnPct >= 0 ? 'var(--up)' : 'var(--down)') + '"></i>' +
          KV.esc(s.name) + ' <b class="' + KV.cls(m.totalReturnPct) + '">' +
          KV.pct(m.totalReturnPct) + '</b>・年化 <b>' + KV.pctPlain(m.annualReturnPct) + '</b></span>' +
        '<span><i style="background:var(--bench-spy)"></i>' + KV.esc(data.primaryBenchmark) +
          ' <b>' + KV.pct(qqq.totalReturnPct) + '</b>・年化 <b>' +
          KV.pctPlain(qqq.annualReturnPct) + '</b></span>' +
        (spy.totalReturnPct === undefined ? '' :
          '<span><i style="background:var(--bg-4)"></i>SPY <b>' + KV.pct(spy.totalReturnPct) +
            '</b>・年化 <b>' + KV.pctPlain(spy.annualReturnPct) + '</b></span>') +
      '</div>' +

      '<a class="btn btn-primary dc-cta" href="' + strategyHref(s) + '">開啟策略頁 →</a>';

    /* 運行編號同快照編號對用戶無用,收起;只留「幾時跑過、跑出幾多」 */
    el.lastrun.innerHTML =
      '最近運行 <b>' + KV.esc(s.lastRunAt) + '</b>・年化 <b>' +
      KV.pctPlain(m.annualReturnPct) + '</b>' +
      (s.isActiveSetup ? '　<span class="tag tag-live">現役設定</span>' : '');
  }

  /* ============================================================
     左欄:平表,跨全表排序
     ============================================================ */
  var GETTERS = {
    name: function (s) { return s.name; },
    type: function (s) { return s.typeName; },
    vsBench: function (s) { return s.metrics ? s.metrics.vsBenchPp : null; },
    cagr: function (s) { return s.metrics ? s.metrics.annualReturnPct : null; },
    sortino: function (s) { return s.metrics ? s.metrics.sortinoRatio : null; },
    maxDD: function (s) { return s.metrics ? s.metrics.maxDrawdownPct : null; },
    winRate: function (s) { return s.metrics ? s.metrics.winRatePct : null; },
  };

  function compare(a, b, get) {
    var x = get(a), y = get(b);
    /* 未跑過的策略沒有成績:一律排最後,無論升序降序——它不是「最差那一套」 */
    var xn = (x === null || x === undefined), yn = (y === null || y === undefined);
    if (xn && yn) return 0;
    if (xn) return 1;
    if (yn) return -1;
    if (typeof x === 'string') return sortDir === 'asc' ? x.localeCompare(y) : y.localeCompare(x);
    return sortDir === 'asc' ? x - y : y - x;
  }

  function renderTable() {
    var rows = visibleRows().slice().sort(function (a, b) {
      return compare(a, b, GETTERS[sortKey]);
    });

    var html = rows.map(function (s) {
      var m = s.metrics;

      return '<tr data-id="' + KV.esc(s.id) + '" tabindex="0" role="button" ' +
          'class="row-clickable' + (s.id === selectedId ? ' is-picked' : '') + '" ' +
          'aria-pressed="' + (s.id === selectedId ? 'true' : 'false') + '">' +
        '<td title="' + KV.esc(s.name) + '">' + KV.esc(s.name) + '</td>' +
        '<td><span class="tag tag-type">' + KV.esc(s.typeName) + '</span></td>' +
        /* D-034/D-040:一套策略全部正式運行都是失敗運行時,成績欄留空,
           只在「對基準」這一格講一句「N 條運行全部失敗」——不是隱藏這一行,
           這一行照常可點,只是沒有可比的成績(用戶原話:「if all are
           failed. You can just leave a failed count. Then the strategy
           will be visible as well」)。 */
        '<td class="num ' + (s.isFailed ? 'dim' : (m ? KV.cls(m.vsBenchPp) : 'dim')) + '">' +
          (s.isFailed ? KV.esc(s.failedRunCount + ' 條運行全部失敗')
            : (m ? KV.pp(m.vsBenchPp) : '—')) +
        '</td>' +
        '<td class="num ' + (m ? KV.cls(m.annualReturnPct) : 'dim') + '">' +
          (m ? KV.pctPlain(m.annualReturnPct) : '—') + '</td>' +
        '<td class="num">' + (m && m.sortinoRatio !== null && m.sortinoRatio !== undefined
          ? KV.fixed(m.sortinoRatio, 2) : '<span class="dim">—</span>') + '</td>' +
        '<td class="num ' + (m ? 'down' : 'dim') + '">' +
          (m ? KV.pctPlain(m.maxDrawdownPct) : '—') + '</td>' +
        '<td class="num">' + (m
          ? KV.pctPlain(m.winRatePct, 0) + '<div class="dim" style="font-size:11px">' +
            m.closedTrades + ' 筆</div>'
          : '<span class="dim">—</span>') + '</td>' +
        '<td><a class="row-go" href="' + strategyHref(s) + '" data-go="1" ' +
          'aria-label="開啟 ' + KV.esc(s.name) + ' 策略頁" title="開啟策略頁">→</a></td>' +
      '</tr>';
    }).join('');

    el.body.innerHTML = html ||
      '<tr><td colspan="' + COLS + '" class="dim" style="text-align:center;padding:var(--s-6) 0">' +
      '沒有符合的策略。清一清類型或搜尋字。</td></tr>';

    /* 點行選中。箭嘴是快捷入口,點它直接開頁,不當作選中 */
    el.body.querySelectorAll('tr[data-id]').forEach(function (tr) {
      function go() { select(tr.getAttribute('data-id')); }
      tr.addEventListener('click', function (e) {
        if (e.target.closest('[data-go]')) return;
        go();
      });
      tr.addEventListener('keydown', function (e) {
        if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); go(); }
      });
    });

    /* 分頁腳:現時一屏放得下,所以一頁到底;數目再大就在這裡分頁 */
    var total = data.strategies.length;
    el.pageFoot.textContent = rows.length
      ? ('顯示 1–' + rows.length + ' / 共 ' + rows.length + ' 套' +
         (rows.length < total ? '(由 ' + total + ' 套篩出)' : ''))
      : '沒有符合的策略';

    var parts = [];
    if (pickedCount()) {
      parts.push(data.strategyTypes.filter(function (t) { return picked[t.id]; })
        .map(function (t) { return t.name; }).join('、'));
    } else {
      parts.push('全部類型');
    }
    if (query.trim()) parts.push('名稱含「' + query.trim() + '」');
    el.filterCount.textContent = parts.join('・') + '　' + rows.length + ' / ' + total + ' 套';

    /* 選中那套被篩走的話,改為選第一行 */
    if (rows.length && !rows.some(function (s) { return s.id === selectedId; })) {
      select(rows[0].id);
    } else if (!rows.length) {
      selectedId = null;
      renderDetail(null);
    }
  }

  function select(id) {
    selectedId = id;
    el.body.querySelectorAll('tr[data-id]').forEach(function (tr) {
      var on = tr.getAttribute('data-id') === id;
      tr.classList.toggle('is-picked', on);
      tr.setAttribute('aria-pressed', on ? 'true' : 'false');
    });
    renderDetail(id);
  }

  /* 表頭排序:跨全表 */
  function paintHeads() {
    el.table.querySelectorAll('th.sortable').forEach(function (th) {
      var k = th.getAttribute('data-key');
      th.setAttribute('aria-sort',
        k === sortKey ? (sortDir === 'asc' ? 'ascending' : 'descending') : 'none');
    });
  }

  el.table.querySelectorAll('th.sortable').forEach(function (th) {
    th.setAttribute('tabindex', '0');
    th.setAttribute('role', 'button');
    function go() {
      if (!data) return;
      var k = th.getAttribute('data-key');
      if (k === sortKey) sortDir = sortDir === 'asc' ? 'desc' : 'asc';
      else { sortKey = k; sortDir = (k === 'name' || k === 'type') ? 'asc' : 'desc'; }
      paintHeads();
      renderTable();
    }
    th.addEventListener('click', go);
    th.addEventListener('keydown', function (e) {
      if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); go(); }
    });
  });

  /* ============================================================
     取數
     ============================================================ */
  function load() {
    showLoading();
    KV.mountNav('/', {});

    KV.fetchJSON('/api/overview').then(function (payload) {
      data = payload;
      var meta = payload.meta || {};
      KV.mountNav('/', { snapshot: meta.snapshot, asOf: meta.asOf });

      if (!payload.strategies.length) {
        showState('未有策略',
          '這個庫還未登記任何策略。登記一套策略、跑一次回測之後,它就會出現在這裡。',
          false);
        return;
      }
      if (!meta.runCount) {
        /* 有策略、一次都未跑過:表照出,但要講明為什麼整欄都是「—」 */
        el.pageFoot.textContent = '未有任何運行';
      }

      byId = {};
      payload.strategies.forEach(function (s) { byId[s.id] = s; });

      el.q.disabled = false;

      mountChips();
      paintChips();
      paintHeads();
      renderTable();              /* 內部會預設選中第一行 */
    }).catch(function (err) {
      showState('拿不到數據', '連不上本機服務,或者讀不到定義庫：' + err.message, true);
    });
  }

  load();
})();
