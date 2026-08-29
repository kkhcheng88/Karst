/* ============================================================
   KARST-051 參數掃描頁 — 真數據

   由 prototype/sweep.html 那一版移植。原型從 window.KARST 假數據取數,本版
   一律經 /api/sweeps 與 /api/sweep 向本機薄 REST 層取真實掃描表與判讀表,
   頁內不留任何寫死數據。

   兩個視圖:
     一、掃描清單——一次掃描一行,**最佳格與代表格並排**。一次掃描動輒幾千格,
         只報最佳格會把孤峰當成成績,所以兩格永遠並列、裁決籤跟住每一格走。
     二、點進一行,才見熱力圖、小倍數、切片、鄰域這四個元件。

   與原型的差異,全部因為「這裡不再是原型」:
     1. 多了上面那張清單,以及一條揀掃描的列(原型只得一次掃描);
     2. 揀軸的選單**只列連續軸**,選擇軸改為分層按鈕(KARST-047 的軸型);
     3. 鄰域數字全部由判讀表讀回,頁面自己不算——鄰域平均只沿連續軸取,
        這件事只有後端知道怎樣算;
     4. 熱力圖格內是**該次判讀的目標指標**,不是一律年化回報:裁決本身就是
        按那個指標判的,兩者不對齊會誤導。
   顏色一律靠 style.css 的 token,唯一例外是熱圖色階(design-system 1.8 已
   登記的那五個停站)。
   ============================================================ */
(function () {
  'use strict';

  var NO_CHOICE_LAYER = '全格(沒有選擇軸)';
  var TAG_CLASS = { '平原': 'tag-live', '山脊': 'tag-strategy', '孤峰': 'tag-current' };

  var el = {
    listView: document.getElementById('list-view'),
    detailView: document.getElementById('detail-view'),
    table: document.getElementById('sweep-table'),
    listCount: document.getElementById('list-count'),
    back: document.getElementById('back-list'),
    title: document.getElementById('page-title'),
    sub: document.getElementById('page-sub'),
    pick: document.getElementById('sweep-pick'),
    bar: document.getElementById('sweep-bar'),
    main: document.getElementById('fit-main'),
    state: document.getElementById('page-state'),
    selY: document.getElementById('ax-y'),
    selX: document.getElementById('ax-x'),
    layers: document.getElementById('layers'),
    slices: document.getElementById('slices'),
    note: document.getElementById('slice-note'),
    heat: document.getElementById('heat'),
    small: document.getElementById('small'),
    smallNote: document.getElementById('small-note'),
    tabSmall: document.getElementById('tab-small'),
    tabHeat: document.getElementById('tab-heat'),
    verdict: document.getElementById('verdict'),
    cellTag: document.getElementById('cell-tag'),
    cellDetail: document.getElementById('cell-detail'),
    nbhd: document.getElementById('nbhd'),
    cellEmpty: document.getElementById('cell-empty'),
    cellBody: document.getElementById('cell-body'),
    curveHead: document.getElementById('curve-head'),
    cellChart: document.getElementById('cell-chart'),
    scaleBar: document.getElementById('scale-bar'),
    scaleMin: document.getElementById('scale-min'),
    scaleMax: document.getElementById('scale-max'),
    bcCrumb: document.getElementById('bc-crumb'),
    /* 以現版本重掃(KARST-052) */
    rescanOpen: document.getElementById('rescan-open'),
    rescanModal: document.getElementById('rescan-modal'),
    rescanBody: document.getElementById('rescan-body'),
    rescanGo: document.getElementById('rescan-go'),
    rescanCancel: document.getElementById('rescan-cancel'),
  };

  var state = {
    seq: 0,
    sweeps: [],
    sweepId: null,
    layer: null,
    data: null,
    yId: null,
    xId: null,
    fixed: {},
    rows: [], cols: [],
    grid: [],
    min: 0, max: 1, digits: 2,
    chart: null,
    curveSeq: 0,
    /* KARST-079:由策略詳情頁的熱力圖帶直達某一格,索引指向 load() 剛讀回那份
       data.cells(即當時開著那一層)的第幾個;consumed 之後清走,免得換層/換軸
       之後仍然誤中一格。 */
    pendingCellIndex: null,
    cellPicked: false,
  };

  /* 熱力圖配色(design-system 1.8):單一正本住 app.js 的 KV.heatColor/
     heatTextColor,策略詳情頁的熱力圖帶(3.16)同一套,不各自各寫一份。
     顏色不是唯一載體——每格同時印出數值,裁決另以形狀區分。 */
  function heatColor(t) { return KV.heatColor(t); }
  function heatTextColor(t) { return KV.heatTextColor(t); }

  /* ============================================================
     小工具
     ============================================================ */
  function fmtVal(v) {
    if (v === null || v === undefined) return '';
    return String(v);
  }

  function fmtUnit(v, unit, digits) {
    if (v === null || v === undefined) return '—';
    if (unit === 'pct') return KV.pctPlain(v, digits === undefined ? 2 : digits);
    if (unit === 'days') return KV.fixed(v, 0) + ' 日';
    return KV.fixed(v, 2);
  }

  function objUnit() { return state.data ? state.data.objectiveUnit : 'num'; }
  function fmtObj(v) { return fmtUnit(v, objUnit(), state.digits); }
  function fmtObjDelta(v) {
    if (v === null || v === undefined) return '—';
    return objUnit() === 'pct' ? KV.pp(v, state.digits) : (v > 0 ? '+' : '') + KV.fixed(v, 2);
  }

  function paramLine(params) {
    if (!params) return '';
    return Object.keys(params).map(function (k) {
      return k + ' ' + fmtVal(params[k]);
    }).join('、');
  }

  function tag(verdict) {
    if (!verdict) return '<span class="tag">未判</span>';
    return '<span class="tag ' + (TAG_CLASS[verdict] || '') + '">' + KV.esc(verdict) + '</span>';
  }

  function parseLayer(name) {
    var out = {};
    if (!name || name === NO_CHOICE_LAYER) return out;
    name.split('、').forEach(function (part) {
      var i = part.indexOf('=');
      if (i > 0) out[part.slice(0, i)] = part.slice(i + 1);
    });
    return out;
  }

  function axisOf(name) {
    var list = state.data ? state.data.axisList : [];
    for (var i = 0; i < list.length; i++) if (list[i].name === name) return list[i];
    return null;
  }

  /* ============================================================
     視圖切換與三態
     ============================================================ */
  function hideAll() {
    el.listView.hidden = true;
    el.detailView.hidden = true;
    el.state.hidden = true;
  }
  function showList() {
    hideAll();
    el.listView.hidden = false;
    el.title.textContent = '參數掃描';
    el.sub.textContent = '一次掃描一行。最佳格與代表格並排——只看最佳格會把孤峰當成成績,' +
      '代表格是高地中間那格,鄰域一齊好的那一格。點一行看熱力圖、小倍數、切片與鄰域。';
    /* D-036:參數掃描不再是頂層頁面,清單本身也是由策略詳情的熱力圖帶(或直連
       網址)進來的下鑽層,所以一樣掛麵包屑——只是未揀定哪一次掃描,還講不出
       是哪一套策略,退到「策略總覽」那一級。 */
    if (el.bcCrumb) {
      el.bcCrumb.innerHTML = KV.breadcrumb([
        { label: '策略總覽', href: '/' },
        { label: '參數掃描' },
      ]);
    }
  }
  function showDetail() {
    hideAll();
    el.detailView.hidden = false;
    el.title.textContent = '參數掃描';
    el.sub.textContent = '兩個連續軸做圖,其餘連續軸定住做切片;選擇軸不做軸,改為分層。' +
      '右欄的鄰域數字全部由判讀表讀回,不是這一頁自己算。';
  }

  function showState(html) {
    hideAll();
    el.state.innerHTML = html;
    el.state.hidden = false;
  }
  function loading(what) {
    showState(
      '<div class="state-block">' +
        '<div class="state-title">載入中……</div>' +
        '<div>' + KV.esc(what) + '</div>' +
        '<div style="max-width:420px;margin:var(--s-4) auto 0">' +
          '<div class="skeleton" style="margin-bottom:6px"></div>' +
          '<div class="skeleton" style="margin-bottom:6px"></div>' +
          '<div class="skeleton" style="width:60%"></div>' +
        '</div>' +
      '</div>'
    );
  }
  function empty(title, body, backToList) {
    showState(
      '<div class="state-block">' +
        '<div class="state-title">' + KV.esc(title) + '</div>' +
        '<div>' + body + '</div>' +
        (backToList ? '<button class="btn" id="state-back">← 掃描清單</button>' : '') +
      '</div>'
    );
    var btn = document.getElementById('state-back');
    if (btn) btn.addEventListener('click', toList);
  }
  function fail(message, retry) {
    showState(
      '<div class="state-block">' +
        '<div class="state-title">出了問題</div>' +
        '<div>' + KV.esc(message) + '</div>' +
        '<button class="btn" id="state-retry">再試一次</button>' +
      '</div>'
    );
    var btn = document.getElementById('state-retry');
    if (btn) btn.addEventListener('click', retry);
  }

  /* ============================================================
     網址狀態:換掃描、換層可以貼連結給人(與表格排序共用同一個 hash)
     ============================================================ */
  function readHash() {
    var out = {};
    (location.hash || '').replace(/^#/, '').split('&').forEach(function (part) {
      if (!part) return;
      var p = part.split('=');
      out[decodeURIComponent(p[0])] = decodeURIComponent(p[1] || '');
    });
    return out;
  }
  function writeHash() {
    var st = readHash();
    if (state.sweepId) st.sweep = state.sweepId; else delete st.sweep;
    if (state.sweepId && state.layer) st.layer = state.layer; else delete st.layer;
    var s = Object.keys(st)
      .filter(function (k) { return st[k] !== '' && st[k] != null; })
      .map(function (k) { return encodeURIComponent(k) + '=' + encodeURIComponent(st[k]); })
      .join('&');
    try { history.replaceState(null, '', location.pathname + location.search + '#' + s); }
    catch (e) { location.hash = s; }
  }

  /* ============================================================
     視圖一:掃描清單
     ============================================================ */
  function renderList() {
    el.listCount.textContent = state.sweeps.length + ' 次掃描・' +
      state.sweeps.reduce(function (a, s) { return a + (s.cells || 0); }, 0) + ' 格';

    function cellBlock(sweep, cell) {
      if (!cell) return '<span class="dim">—</span>';
      return '<div style="display:flex;align-items:center;gap:var(--s-2)">' +
          '<b class="' + KV.cls(cell.value) + '">' +
            fmtUnit(cell.value, sweep.objectiveUnit, 2) + '</b>' +
          tag(cell.verdict) +
        '</div>' +
        '<div class="dim mono" style="font-size:var(--fs-xs);line-height:1.5" ' +
          'title="' + KV.esc(paramLine(cell.params)) + '">' +
          KV.esc(KV.truncate(paramLine(cell.params), 34)) + '</div>';
    }

    KV.sortableTable({
      mount: '#sweep-table',
      hashKey: 'ls',
      defaultSort: 'label',
      defaultDir: 'asc',
      rows: state.sweeps,
      rowKey: function (r) { return r.id; },
      onRowClick: function (row) { toDetail(row.id, null); },
      emptyText: '沒有掃描落檔。',
      minWidth: '1000px',
      cols: [
        {
          key: 'label', label: '掃描',
          get: function (r) { return r.label; },
          render: function (r) {
            /* D-029:固定比例權重掃描只作對照——ETF 比例是驅動器的輸出,
               不是策略的參數,不可與驅動器參數掃描混為一談。 */
            return '<b>' + KV.esc(r.label) + '</b>' +
              (r.reference ? ' <span class="tag tag-type">對照</span>' : '') +
              '<div class="dim" style="font-size:var(--fs-xs)">' +
                KV.esc(r.experiment) + '</div>';
          },
        },
        {
          key: 'strategy', label: '策略',
          get: function (r) { return r.strategy || ''; },
          render: function (r) {
            return r.strategy
              ? KV.esc(r.strategy)
              : '<span class="dim">落檔未記</span>';
          },
        },
        {
          key: 'cells', label: '掃了幾格', cls: 'num',
          get: function (r) { return r.cells; },
          render: function (r) {
            return r.cells + ' 格<div class="dim" style="font-size:var(--fs-xs)">' +
              r.layers + ' 層</div>';
          },
        },
        {
          key: 'objective', label: '判讀目標',
          get: function (r) { return r.objectiveLabel || ''; },
          render: function (r) {
            return KV.esc(r.objectiveLabel) +
              '<div class="dim" style="font-size:var(--fs-xs)">' +
                KV.esc(r.axisAware ? '軸型判讀' : '舊口徑') + '</div>';
          },
        },
        {
          key: 'best', label: '最佳格', cls: 'num',
          get: function (r) { return r.best ? r.best.value : -Infinity; },
          render: function (r) { return cellBlock(r, r.best); },
        },
        {
          key: 'representative', label: '代表格', cls: 'num',
          get: function (r) { return r.representative ? r.representative.value : -Infinity; },
          render: function (r) { return cellBlock(r, r.representative); },
        },
        {
          key: 'verdicts', label: '裁決',
          get: function (r) { return (r.counts['平原'] || 0) * 1000 + (r.counts['山脊'] || 0); },
          render: function (r) {
            var bits = ['平原', '山脊', '孤峰', '無效'].filter(function (v) {
              return r.counts[v];
            }).map(function (v) {
              return '<span class="tag ' + (TAG_CLASS[v] || '') + '">' +
                v + ' ' + r.counts[v] + '</span>';
            });
            return bits.length
              ? '<div style="display:flex;gap:4px;flex-wrap:wrap">' + bits.join('') + '</div>'
              : '<span class="dim">全部普通</span>';
          },
        },
      ],
    });
  }

  function toList() {
    state.sweepId = null;
    state.layer = null;
    state.data = null;
    writeHash();
    showList();
    renderList();
    KV.mountFoot({});
  }

  function toDetail(id, layer) {
    state.sweepId = id;
    state.layer = layer || null;
    mountPicker();
    load();
  }

  el.back.addEventListener('click', toList);

  /* ============================================================
     視圖二:揀哪一次掃描
     ============================================================ */
  function mountPicker() {
    el.pick.innerHTML = state.sweeps.map(function (s) {
      var bits = [];
      if (s.cells) bits.push(s.cells + ' 格');
      if (s.layers) bits.push(s.layers + ' 層');
      bits.push(s.axisAware ? '軸型判讀' : '舊口徑');
      return '<button type="button" data-id="' + KV.esc(s.id) + '" ' +
        'aria-pressed="' + (s.id === state.sweepId ? 'true' : 'false') + '" ' +
        'title="' + KV.esc(s.experiment + '　' + bits.join('・')) + '">' +
        KV.esc(s.label) + '</button>';
    }).join('');
  }

  el.pick.addEventListener('click', function (e) {
    var btn = e.target.closest('button[data-id]');
    if (!btn) return;
    var id = btn.getAttribute('data-id');
    if (id === state.sweepId) return;
    toDetail(id, null);
  });

  /* ============================================================
     取數
     ============================================================ */
  function load() {
    var token = ++state.seq;
    var sweep = null;
    state.sweeps.forEach(function (s) { if (s.id === state.sweepId) sweep = s; });
    loading('掃描 ' + (sweep ? sweep.label : state.sweepId));
    writeHash();

    var url = '/api/sweep?id=' + encodeURIComponent(state.sweepId) +
      (state.layer ? '&layer=' + encodeURIComponent(state.layer) : '');

    KV.fetchJSON(url).then(function (data) {
      if (state.seq !== token) return;
      state.data = data;
      state.layer = data.layer;
      writeHash();
      if (!data.cells.length) {
        empty('這一層沒有格',
          '掃描 <b>' + KV.esc(data.label) + '</b> 的「' + KV.esc(data.layer) +
          '」一格都沒有。', true);
        return;
      }
      showDetail();
      mountPicker();
      mountIdentity(data);
      resetAxes(data);
      mountLayers(data);
      mountSlices();
      renderAll();
      renderSmall(data);
      /* KARST-079:由策略詳情頁的熱力圖帶直達某一格(?cell=),grid 剛砌好就
         補選一次;換軸/換層之後索引可能已經對不上另一層,所以只消費一次。 */
      if (state.pendingCellIndex !== null) {
        var idx = state.pendingCellIndex;
        state.pendingCellIndex = null;
        selectByCellIndex(idx);
      }
    }).catch(function (err) {
      if (state.seq !== token) return;
      fail('讀不到掃描 ' + state.sweepId + '：' + err.message, load);
    });
  }

  /* 麵包屑(design-system 3.6a 的通用格式,經 KARST-079 推廣到掃描格這一層):
     「策略詳情 › <策略名> › 掃描 <名>」,揀定一格之後再多一節「格」。第二節連
     回策略詳情頁——策略名若解析不到(落檔沒有記低,KARST-051 舊掃描的已知
     缺口)就退一步只印實驗名,不冒充一個連結。 */
  function mountBreadcrumb(data) {
    if (!el.bcCrumb) return;
    /* data.strategy 可能是由格內運行倒查回來的(落檔的 summary.json 未記低
       策略名,api_sweep._with_strategy),不一定同 provenance.strategy 一致
       ——data.strategy 較新,先取它。 */
    var stratName = data.strategy || (data.provenance && data.provenance.strategy) || null;
    var parts = [{ label: '策略詳情' }];
    parts.push(stratName
      ? { label: stratName, href: '/strategy?id=' + encodeURIComponent(stratName) }
      : { label: data.experiment });
    parts.push({ label: '掃描 ' + data.label });
    if (state.cellPicked) parts.push({ label: '格' });
    el.bcCrumb.innerHTML = KV.breadcrumb(parts);
  }

  function mountIdentity(data) {
    var prov = data.provenance || {};
    var th = prov.thresholds || {};
    var period = (prov.period && prov.period.length === 2)
      ? prov.period[0] + ' 至 ' + prov.period[1] : '';

    state.cellPicked = false;
    mountBreadcrumb(data);

    var rows = [
      { k: '掃描', v: KV.esc(data.experiment + '　' + data.label) +
          (data.reference ? '　<span class="tag tag-type">對照</span>' : '') },
      { k: '判讀目標', v: KV.esc(data.objectiveLabel + '(' + (data.objective || '—') + ')') },
      { k: '判讀口徑', v: KV.esc(data.axisAware ? '軸型:連續軸取鄰域、選擇軸分層' : '舊口徑:全部軸當連續軸') },
      { k: '軸', v: KV.esc('連續 ' + (data.continuousAxes.join('、') || '無') +
          '　選擇 ' + (data.choiceAxes.join('、') || '無')) },
      { k: '掃描格', v: KV.esc(data.cells + ' 格・' + data.layers + ' 層') },
    ];
    if (prov.engine) rows.push({ k: '引擎', v: KV.esc(prov.engine) });
    if (prov.costs) rows.push({ k: '成本', v: KV.esc(prov.costs) });
    if (th.min_trades !== undefined) {
      rows.push({ k: '門檻', v: KV.esc('成交筆數 ≥ ' + th.min_trades +
        '　孤峰邊際 ' + th.lonely_peak_margin + '　平原分位 ' + th.plateau_quantile) });
    }
    rows.push({ k: '掃描表', v: KV.esc(prov.gridPath || '') });
    rows.push({ k: '判讀表', v: KV.esc(prov.verdictPath || '') });

    KV.runChip({
      ver: data.label,
      snapshot: prov.snapshotId || period || '—',
      rows: rows,
    });

    KV.mountFoot({
      snapshot: prov.snapshotId,
      periodFrom: prov.period && prov.period[0],
      periodTo: prov.period && prov.period[1],
    });
  }

  /* ============================================================
     揀軸:只列連續軸(選擇軸不做軸,做層)
     ============================================================ */
  function fillSelect(sel, names, picked) {
    sel.innerHTML = names.map(function (n) {
      return '<option value="' + KV.esc(n) + '"' + (n === picked ? ' selected' : '') + '>' +
        KV.esc(n) + '</option>';
    }).join('');
  }

  /* 兩條軸擺邊兩條?——揀「切完之後仲見到最多格」那一對。

     權重掃描四條軸加起來要等於 1:隨便拿頭兩條做軸、其餘兩條定住,枱面就只
     剩一個組合,成幅圖得一格。同樣一組數,換另一對做軸就見到成條對角線。
     所以不硬取頭兩條,而是逐對數一數,揀見得最多的那一對。 */
  function bestPair(data, anchor) {
    var cont = data.continuousAxes;
    var pick = null;
    for (var i = 0; i < cont.length; i++) {
      for (var j = i + 1; j < cont.length; j++) {
        var rest = cont.filter(function (n, k) { return k !== i && k !== j; });
        var seen = data.cells.filter(function (c) {
          return rest.every(function (m) {
            return !anchor || anchor[m] === undefined || c.params[m] === anchor[m];
          });
        }).length;
        if (!pick || seen > pick.seen) pick = { y: cont[i], x: cont[j], seen: seen };
      }
    }
    return pick;
  }

  function resetAxes(data) {
    var cont = data.continuousAxes;

    /* 切片預設對準代表格:一開就要見到最佳格與代表格兩個標記(D-029)。
       代表格不在這一層(換過層)就退而對準最佳格,兩個都不在就取首格。 */
    var anchor = null;
    if (data.representative && data.representative.layer === data.layer) {
      anchor = data.representative.params;
    } else if (data.best && data.best.layer === data.layer) {
      anchor = data.best.params;
    }

    el.selX.disabled = false;
    if (cont.length >= 2) {
      var pair = bestPair(data, anchor);
      state.yId = pair.y;
      state.xId = pair.x;
      el.selY.disabled = false;
      fillSelect(el.selY, cont, state.yId);
      fillSelect(el.selX, cont, state.xId);
    } else if (cont.length === 1) {
      /* 只得一條連續軸:熱力圖畫一行,縱軸無得揀——選擇軸不會被擺上軸 */
      state.yId = null;
      state.xId = cont[0];
      el.selY.disabled = true;
      el.selY.innerHTML = '<option>(只得一條連續軸)</option>';
      fillSelect(el.selX, cont, state.xId);
    } else {
      state.yId = null;
      state.xId = null;
      el.selY.disabled = true;
      el.selX.disabled = true;
      el.selY.innerHTML = '<option>(沒有連續軸)</option>';
      el.selX.innerHTML = '<option>(沒有連續軸)</option>';
    }

    state.fixed = {};
    cont.forEach(function (n) {
      var axis = axisOf(n);
      if (!axis || !axis.values.length) return;
      state.fixed[n] = (anchor && anchor[n] !== undefined) ? anchor[n] : axis.values[0];
    });
  }

  /* 兩格是不是同一格:逐條軸的取值都一樣 */
  function sameCell(params, other) {
    if (!params || !other) return false;
    var names = state.data.axes;
    for (var i = 0; i < names.length; i++) {
      if (params[names[i]] !== other[names[i]]) return false;
    }
    return true;
  }

  el.selY.addEventListener('change', function () {
    var v = el.selY.value;
    if (v === state.xId) {
      state.xId = state.yId;
      fillSelect(el.selX, state.data.continuousAxes, state.xId);
    }
    state.yId = v;
    mountSlices();
    renderAll();
  });
  el.selX.addEventListener('change', function () {
    var v = el.selX.value;
    if (v === state.yId) {
      state.yId = state.xId;
      fillSelect(el.selY, state.data.continuousAxes, state.yId);
    }
    state.xId = v;
    mountSlices();
    renderAll();
  });

  /* ============================================================
     選擇軸 → 分層按鈕(KARST-047:選擇軸不入鄰域,改為分層)
     ============================================================ */
  function layerValues(data) {
    var out = {};
    data.choiceAxes.forEach(function (n) { out[n] = []; });
    data.layerRows.forEach(function (row) {
      var map = parseLayer(row.name);
      data.choiceAxes.forEach(function (n) {
        if (map[n] !== undefined && out[n].indexOf(map[n]) < 0) out[n].push(map[n]);
      });
    });
    return out;
  }

  function mountLayers(data) {
    if (!data.choiceAxes.length) {
      el.layers.innerHTML = '<span class="section-note dim">沒有選擇軸,全格只得一層。</span>';
      return;
    }
    var values = layerValues(data);
    var picked = parseLayer(data.layer);
    el.layers.innerHTML = data.choiceAxes.map(function (n) {
      return '<div class="slice-group">' +
        '<span class="slice-label">層・' + KV.esc(n) +
          '<span class="hint" title="選擇軸:鄰格不是「一步之遙」而是「另一套做法」,' +
            '所以不入鄰域平均,改為各自成一層,判讀逐層各出一份。">?</span></span>' +
        '<div class="date-switch" role="group" aria-label="層 ' + KV.esc(n) + '">' +
          values[n].map(function (v) {
            return '<button type="button" data-layer-axis="' + KV.esc(n) + '" ' +
              'data-v="' + KV.esc(v) + '" aria-pressed="' +
              (v === picked[n] ? 'true' : 'false') + '">' + KV.esc(v) + '</button>';
          }).join('') +
        '</div>' +
      '</div>';
    }).join('');
  }

  el.layers.addEventListener('click', function (e) {
    var btn = e.target.closest('button[data-layer-axis]');
    if (!btn) return;
    var data = state.data;
    var axis = btn.getAttribute('data-layer-axis');
    var value = btn.getAttribute('data-v');
    var want = parseLayer(state.layer);
    want[axis] = value;

    /* 先找完全對得上的層;那個組合沒有掃過就退一步,取第一個在這條軸上
       對得上的層,其餘按鈕跟住撥正。 */
    var exact = null, partial = null;
    data.layerRows.forEach(function (row) {
      var map = parseLayer(row.name);
      var all = true;
      for (var k in want) if (map[k] !== want[k]) all = false;
      if (all && !exact) exact = row.name;
      if (map[axis] === value && !partial) partial = row.name;
    });

    var next = exact || partial;
    if (!next || next === state.layer) return;
    state.layer = next;
    load();
  });

  /* ============================================================
     不在軸上的連續軸 → 切片按鈕
     ============================================================ */
  function sliceIds() {
    if (!state.data) return [];
    return state.data.continuousAxes.filter(function (n) {
      return n !== state.xId && n !== state.yId;
    });
  }

  function mountSlices() {
    el.slices.innerHTML = sliceIds().map(function (n) {
      var axis = axisOf(n);
      return '<div class="slice-group">' +
        '<span class="slice-label">' + KV.esc(n) +
          '<span class="hint" title="不在軸上的連續軸:定住一格,整幅圖就是那個切面。">?</span></span>' +
        '<div class="date-switch" role="group" aria-label="切片 ' + KV.esc(n) + '">' +
          axis.values.map(function (v) {
            return '<button type="button" data-slice="' + KV.esc(n) + '" ' +
              'data-v="' + KV.esc(fmtVal(v)) + '" aria-pressed="' +
              (v === state.fixed[n] ? 'true' : 'false') + '">' + KV.esc(fmtVal(v)) + '</button>';
          }).join('') +
        '</div>' +
      '</div>';
    }).join('');
  }

  el.slices.addEventListener('click', function (e) {
    var btn = e.target.closest('button[data-slice]');
    if (!btn) return;
    var name = btn.getAttribute('data-slice');
    var axis = axisOf(name);
    var raw = btn.getAttribute('data-v');
    axis.values.forEach(function (v) { if (fmtVal(v) === raw) state.fixed[name] = v; });
    btn.parentElement.querySelectorAll('button').forEach(function (o) {
      o.setAttribute('aria-pressed', o === btn ? 'true' : 'false');
    });
    renderAll();
  });

  /* ============================================================
     整頁重畫
     ============================================================ */
  function buildGrid() {
    var data = state.data;
    var slices = sliceIds();
    state.rows = state.yId ? axisOf(state.yId).values : [null];
    state.cols = state.xId ? axisOf(state.xId).values : [null];

    var index = {};
    data.cells.forEach(function (cell) {
      var ok = true;
      slices.forEach(function (n) { if (cell.params[n] !== state.fixed[n]) ok = false; });
      if (!ok) return;
      index[(state.yId ? cell.params[state.yId] : '') + '|' +
            (state.xId ? cell.params[state.xId] : '')] = cell;
    });

    state.grid = state.rows.map(function (rv) {
      return state.cols.map(function (cv) {
        return index[(state.yId ? rv : '') + '|' + (state.xId ? cv : '')] || null;
      });
    });

    var flat = [];
    state.filled = 0;
    state.slots = 0;
    state.grid.forEach(function (row) {
      row.forEach(function (c) {
        state.slots++;
        if (c) state.filled++;
        if (c && c.value !== null && c.value !== undefined && !c.invalid) flat.push(c.value);
      });
    });
    state.min = flat.length ? Math.min.apply(null, flat) : 0;
    state.max = flat.length ? Math.max.apply(null, flat) : 1;
    state.digits = (state.max - state.min) < 5 ? 2 : 1;
  }

  function norm(v) { return (v - state.min) / ((state.max - state.min) || 1); }

  function where(cell) {
    return state.data.continuousAxes.map(function (n) {
      return n + ' ' + fmtVal(cell.params[n]);
    }).join('、');
  }

  function renderAll() {
    buildGrid();
    renderNote();
    renderVerdict();
    renderHeat();
  }

  function renderNote() {
    var data = state.data;
    var sliceTxt = sliceIds().map(function (n) {
      return n + ' ' + fmtVal(state.fixed[n]);
    }).join('、');
    var bits = ['<b>' + KV.esc(data.layer) + '</b>'];
    bits.push(state.yId
      ? KV.esc(state.yId + ' × ' + state.xId)
      : KV.esc(state.xId + '(只得一條連續軸,畫一行)'));
    if (sliceTxt) bits.push('切片 ' + KV.esc(sliceTxt));
    /* 掃描格未必掃齊整個長方格(權重掃描四條軸加起來要等於 1,定住兩條就
       只剩一個組合)。斜紋格是「沒有掃過」,不是「成績差」——這裡講清楚。 */
    var short = (state.slots && state.filled < state.slots)
      ? '　<b>' + state.filled + ' / ' + state.slots + '</b> 格掃過,斜紋格未掃。'
      : '';
    el.note.innerHTML = bits.join('、') + '。' + KV.esc(data.judgementNote) + short;
    el.tabHeat.textContent = data.objectiveLabel + '熱力圖';
  }

  function renderVerdict() {
    var data = state.data;
    var cells = data.cells;
    var scored = cells.filter(function (c) {
      return c.value !== null && c.value !== undefined && !c.invalid;
    });
    if (!scored.length) {
      el.verdict.innerHTML = '<b>這一層一格有效成績都沒有。</b>成交筆數全部低過門檻,成績不作數。';
      return;
    }

    var best = scored.reduce(function (a, b) { return b.value > a.value ? b : a; });
    var plateaus = cells.filter(function (c) { return c.verdict === '平原'; });
    var ridges = cells.filter(function (c) { return c.verdict === '山脊'; });
    var peaks = cells.filter(function (c) { return c.verdict === '孤峰'; });

    var head;
    if (best.verdict === '平原') head = '這一層的最高分,剛好就落在平原之內。';
    else if (best.verdict === '山脊') head = '最高分那格是山脊:沿連續軸站得住,換一層就塌。';
    else if (best.verdict === '孤峰') head = '全層最高分那格,不是最應該選那格。';
    else head = '這一層沒有一格判到平原。';

    var html = '<b>' + KV.esc(head) + '</b><br>' +
      '最高分 <b>' + KV.esc(where(best)) + '</b>,' + KV.esc(data.objectiveLabel) +
        ' <b class="' + KV.cls(best.value) + '">' + fmtObj(best.value) + '</b>,' +
      '鄰域平均 <b class="' + KV.cls(best.neighbourhoodMean) + '">' +
        fmtObj(best.neighbourhoodMean) + '</b>(相差 ' + fmtObjDelta(best.lift) + ',' +
        (best.validNeighbours === null ? '—' : best.validNeighbours) + ' 個有效鄰居)。<br>';

    if (plateaus.length) {
      var bp = plateaus.reduce(function (a, b) { return b.value > a.value ? b : a; });
      html += '平原 ' + plateaus.length + ' 格,最好一格 <b>' + KV.esc(where(bp)) + '</b>,' +
        '鄰域平均有 <b class="up">' + fmtObj(bp.neighbourhoodMean) + '</b>,整片一起好。<br>';
    }
    if (ridges.length) {
      var br = ridges.reduce(function (a, b) { return b.value > a.value ? b : a; });
      html += '山脊 ' + ridges.length + ' 格,例如 <b>' + KV.esc(where(br)) + '</b>:' +
        '本層 ' + fmtObj(br.value) + ',同一組連續取值換去最弱那一層只得 ' +
        fmtObj(br.weakestSiblingMean) + '(相差 ' + fmtObjDelta(br.layerDrop) + ')。' +
        '賺的是揀對了層,不是參數本身。<br>';
    }
    if (peaks.length) {
      var bk = peaks.reduce(function (a, b) { return b.value > a.value ? b : a; });
      html += '孤峰 ' + peaks.length + ' 格,最高一格 <b>' + KV.esc(where(bk)) + '</b>,' +
        '高出鄰域 ' + fmtObjDelta(bk.lift) + ',換一段時間多數消失。<br>';
    }
    /* 全掃描(不只這一層)的最佳格與代表格,永遠並列講一次。
       圖上兩個標記就是這兩格;不在眼前那一片時,這裡講得出它們在哪一層。 */
    if (data.best || data.representative) {
      html += '<span class="dim">全掃描:</span>';
      if (data.best) {
        html += '最佳格 <b>' + KV.esc(paramLine(data.best.params)) + '</b> ' +
          fmtObj(data.best.value) + '(' + KV.esc(data.best.verdict || '未判') + ')';
      }
      if (data.representative) {
        html += '　代表格 <b>' + KV.esc(paramLine(data.representative.params)) + '</b> ' +
          fmtObj(data.representative.value) +
          '(' + KV.esc(data.representative.verdict || '未判') + ',鄰域平均 ' +
          fmtObj(data.representative.neighbourhoodMean) + ')';
      }
      html += '。<br>';
    }

    html += '<b>實盤要選平原,不是孤峰。</b>';
    if (data.reference) {
      html += '<br><span class="dim">這一次掃描是<b>對照</b>:掃的是四隻 ETF 的固定比例,' +
        '而比例是驅動器每個換倉日算出來的輸出,不是策略的參數(D-029)。</span>';
    }
    el.verdict.innerHTML = html;
  }

  function renderHeat() {
    var R = state.rows.length, C = state.cols.length;
    el.heat.style.gridTemplateColumns = '110px repeat(' + C + ', minmax(48px, 1fr))';
    /* 只得一行(單一條連續軸)就不要撐滿整個面板高度——一行拉到成版高,
       格仔會變成一條條長柱,反而看不出地形。多過一行才照原型貼屏撐滿。 */
    el.heat.style.gridTemplateRows = R === 1
      ? '20px minmax(24px, 96px)'
      : '20px repeat(' + R + ', minmax(24px, 1fr))';
    el.heat.style.alignContent = R === 1 ? 'start' : 'stretch';

    var html = '<div class="heat-corner" style="display:flex;align-items:center;justify-content:center">' +
      KV.esc((state.yId || '　') + ' ＼ ' + (state.xId || '')) + '</div>';
    state.cols.forEach(function (v) {
      html += '<div class="heat-axis-label">' + KV.esc(fmtVal(v)) + '</div>';
    });

    var first = null;
    state.grid.forEach(function (row, ri) {
      html += '<div class="heat-axis-label row-label">' +
        KV.esc(state.yId ? fmtVal(state.rows[ri]) : '') + '</div>';
      row.forEach(function (cell, ci) {
        if (!cell) {
          html += '<div class="heat-cell is-blank" title="這一格沒有掃過"></div>';
          return;
        }
        if (first === null) first = [ri, ci];
        var invalid = cell.invalid || cell.value === null || cell.value === undefined;
        var t = invalid ? 0 : norm(cell.value);
        var klass = 'heat-cell';
        if (invalid) klass += ' is-invalid';
        else if (cell.verdict === '孤峰') klass += ' is-spike';
        else if (cell.verdict === '山脊') klass += ' is-ridge';
        else if (cell.verdict === '平原') klass += ' in-plateau';

        var style = invalid
          ? 'background:var(--bg-2)'
          : 'background:' + heatColor(t) + ';color:' + heatTextColor(t);

        /* 最佳格與代表格兩個標記(D-029)。永遠一齊出現——只標最佳格就會把
           孤峰當成成績。籤在左上角,與右上角的孤峰/山脊籤分邊站。 */
        var marks = '';
        var isBest = state.data.best && sameCell(cell.params, state.data.best.params);
        var isRep = state.data.representative &&
          sameCell(cell.params, state.data.representative.params);
        if (isBest) marks += '<i class="cell-mark best">最佳</i>';
        if (isRep) marks += '<i class="cell-mark rep">代表</i>';

        html += '<button class="' + klass + '" data-r="' + ri + '" data-c="' + ci + '" ' +
          'aria-pressed="false" style="' + style + '" ' +
          'aria-label="' + KV.esc(where(cell) + '，' + state.data.objectiveLabel + ' ' +
            (invalid ? '不作數' : fmtObj(cell.value)) +
            (cell.verdict ? '，' + cell.verdict : '') +
            (isBest ? '，最佳格' : '') + (isRep ? '，代表格' : '')) + '">' +
          marks + (invalid ? '—' : fmtObj(cell.value).replace('%', '')) +
        '</button>';
      });
    });
    el.heat.innerHTML = html;

    var bar = '';
    for (var i = 0; i < 40; i++) bar += '<i style="background:' + heatColor(i / 39) + '"></i>';
    el.scaleBar.innerHTML = bar;
    el.scaleMin.textContent = fmtObj(state.min);
    el.scaleMax.textContent = fmtObj(state.max);

    /* D-029:預設只顯示熱力圖連兩個標記,**不預先揀格**——個別格的曲線
       要點過先開,免得一入來就把某一格當成結論。 */
    clearCell();
  }

  function clearCell() {
    state.curveSeq++;
    el.cellBody.hidden = true;
    el.cellEmpty.hidden = false;
    el.cellTag.textContent = '';
    el.cellTag.className = 'tag';
    disposeChart();
    if (state.cellPicked) { state.cellPicked = false; mountBreadcrumb(state.data); }
  }

  function disposeChart() {
    if (state.chart) {
      try { state.chart.remove(); } catch (e) { /* 已經拆走 */ }
      state.chart = null;
    }
    el.cellChart.innerHTML = '';
  }

  /* KARST-079:?cell= 帶來的索引,指向 data.cells(當時那一層)第幾格。
     索引本身不是任何一格的身份——同一個索引換層/換軸會指去另一組參數,
     所以要靠參數比對(sameCell)在 state.grid 裡找回它真正的位置。 */
  function selectByCellIndex(idx) {
    var data = state.data;
    if (!data || !data.cells || idx < 0 || idx >= data.cells.length) return;
    var want = data.cells[idx];
    for (var ri = 0; ri < state.grid.length; ri++) {
      for (var ci = 0; ci < state.grid[ri].length; ci++) {
        var cell = state.grid[ri][ci];
        if (cell && sameCell(cell.params, want.params)) {
          select(ri, ci);
          var btn = el.heat.querySelector(
            '.heat-cell[data-r="' + ri + '"][data-c="' + ci + '"]');
          if (btn) btn.scrollIntoView({ block: 'nearest', inline: 'nearest' });
          return;
        }
      }
    }
  }

  /* ============================================================
     選中格:參數組詳情 + 鄰域穩健度(數全部由判讀表讀回,頁面不自己算)
     ============================================================ */
  function select(ri, ci) {
    var cell = state.grid[ri][ci];
    if (!cell) return;

    el.heat.querySelectorAll('.heat-cell').forEach(function (b) {
      b.setAttribute('aria-pressed',
        (+b.dataset.r === ri && +b.dataset.c === ci) ? 'true' : 'false');
    });

    el.cellEmpty.hidden = true;
    el.cellBody.hidden = false;
    el.cellTag.textContent = cell.verdict || '未判';
    el.cellTag.className = 'tag ' + (TAG_CLASS[cell.verdict] || '');
    /* KARST-079:揀定一格,麵包屑多一節「格」(design-system 3.6a 的格式) */
    if (!state.cellPicked) { state.cellPicked = true; mountBreadcrumb(state.data); }

    var data = state.data;
    var byKey = {};
    cell.metrics.forEach(function (m) { byKey[m.key] = m; });

    var params = data.axes.map(function (n) {
      var onAxis = (n === state.xId || n === state.yId);
      return '<span' + (onAxis ? ' style="color:var(--text-1);font-weight:700"' : '') + '>' +
        KV.esc(n) + ' ' + KV.esc(fmtVal(cell.params[n])) + '</span>';
    }).join('<span class="dim">　</span>');

    var rows = data.detailMetrics.map(function (key) {
      var m = byKey[key];
      if (!m) return '';
      var cls = (key === 'max_drawdown') ? 'down' : KV.cls(m.value);
      return '<dt>' + KV.esc(m.label) + '</dt><dd class="' + cls + '">' +
        fmtUnit(m.value, m.unit) + '</dd>';
    }).join('');
    rows += '<dt>交易數</dt><dd>' + (cell.trades === null ? '—' : cell.trades) + '</dd>';
    if (cell.runId) {
      rows += '<dt>運行編號</dt><dd class="mono" style="font-size:var(--fs-xs)">' +
        KV.esc(cell.runId) + '</dd>';
    }

    el.cellDetail.innerHTML =
      '<div style="font-family:var(--font-mono);font-size:var(--fs-sm);color:var(--text-2);' +
        'margin-bottom:var(--s-3);line-height:1.8">' + params + '</div>' +
      '<dl class="def-list">' + rows + '</dl>';

    renderNbhd(cell);
    loadCurve(cell);
  }

  /* ============================================================
     單格曲線(D-029:點格才開該格那一次運行的曲線)

     這是掃描格那一次真實運行的淨值,經 /api/runs/<運行編號> 讀回——與運行
     詳情頁同一條路、同一批數。掃描格的運行不入運行清單,但點得到就看得到。
     ============================================================ */
  function loadCurve(cell) {
    var token = ++state.curveSeq;
    disposeChart();

    if (!cell.runId) {
      el.curveHead.innerHTML = '<span class="dim">這一格沒有運行編號,畫不出曲線。</span>';
      return;
    }
    el.curveHead.innerHTML = '<span class="dim">載入運行 ' + KV.esc(cell.runId) + '……</span>';

    KV.fetchJSON('/api/runs/' + encodeURIComponent(cell.runId)).then(function (run) {
      if (state.curveSeq !== token) return;
      var series = run.series && run.series.strategy;
      if (!series || !series.values.length) {
        el.curveHead.innerHTML = '<span class="dim">這一次運行沒有逐日淨值。</span>';
        return;
      }

      el.curveHead.innerHTML =
        '<span><b>' + KV.esc(series.label || '策略') + '</b></span>' +
        '<span class="dim mono" style="font-size:var(--fs-xs)">' + KV.esc(cell.runId) + '</span>';

      state.chart = KV.makeChart(el.cellChart, el.cellChart.clientHeight || 150);
      var line = state.chart.addLineSeries({ color: '#26a69a', lineWidth: 2 });
      line.setData(KV.zip(series.dates, series.values));

      var bench = run.series.benchmarks || {};
      if (bench.SPY) {
        var spy = state.chart.addLineSeries({ color: '#7d869c', lineWidth: 1 });
        spy.setData(KV.zip(bench.SPY.dates, bench.SPY.values));
        el.curveHead.innerHTML += '<span class="dim">SPY</span>';
      }
      state.chart.timeScale().fitContent();
    }).catch(function (err) {
      if (state.curveSeq !== token) return;
      el.curveHead.innerHTML = '<span class="dim">讀不到這一格的運行：' +
        KV.esc(err.message) + '</span>';
    });
  }

  function renderNbhd(cell) {
    var data = state.data;
    if (cell.invalid) {
      el.nbhd.innerHTML =
        '<p class="section-note dim" style="margin:0;line-height:1.7">' +
        '無效格:成交筆數 ' + (cell.trades === null ? '—' : cell.trades) +
        ' 低過門檻,成績不作數,亦不入鄰域平均。</p>';
      return;
    }

    var rows =
      '<dt>' + KV.esc(data.objectiveLabel) + '</dt><dd class="' + KV.cls(cell.value) + '">' +
        fmtObj(cell.value) + '</dd>' +
      '<dt>鄰域平均(含本格)</dt><dd>' + fmtObj(cell.neighbourhoodMean) + '</dd>' +
      '<dt>鄰居平均(不含本格)</dt><dd>' + fmtObj(cell.neighbourMean) + '</dd>' +
      '<dt>有效鄰居</dt><dd>' +
        (cell.validNeighbours === null ? '—' : cell.validNeighbours + ' / ' + cell.neighbours) +
        ' 格</dd>' +
      '<dt>本格 減 鄰域</dt><dd class="' + KV.cls(cell.lift) + '">' +
        fmtObjDelta(cell.lift) + '</dd>';

    if (cell.layerDrop !== null && cell.layerDrop !== undefined) {
      rows += '<dt>最弱同層平均</dt><dd>' + fmtObj(cell.weakestSiblingMean) + '</dd>' +
        '<dt>換層跌幅</dt><dd class="' + KV.cls(-cell.layerDrop) + '">' +
        fmtObjDelta(-cell.layerDrop) + '</dd>';
    }

    var verdict, vcls;
    if (cell.verdict === '孤峰') {
      verdict = '孤峰:自己高出鄰域 ' + fmtObjDelta(cell.lift) + ',換一段時間好可能消失。';
      vcls = 'down';
    } else if (cell.verdict === '山脊') {
      verdict = '山脊:沿連續軸自己與鄰域都在高地,但換去最弱那一層跌 ' +
        fmtObjDelta(-cell.layerDrop) + '——賺的是「揀對了層」,不是參數穩健。';
      vcls = 'down';
    } else if (cell.verdict === '平原') {
      verdict = '穩健:鄰域平均都有 ' + fmtObj(cell.neighbourhoodMean) +
        ',參數偏離一兩格照樣站得住。';
      vcls = 'up';
    } else if (cell.verdict === '無鄰') {
      verdict = '無鄰:沿連續軸一個有效鄰居都沒有,穩不穩健這一格答不到。';
      vcls = 'dim';
    } else {
      verdict = '平平:鄰域平均只有 ' + fmtObj(cell.neighbourhoodMean) + ',這一區整體不突出。';
      vcls = 'dim';
    }

    el.nbhd.innerHTML = '<dl class="def-list">' + rows + '</dl>' +
      '<p class="section-note ' + vcls + '" style="margin:var(--s-3) 0 0;line-height:1.7">' +
      KV.esc(verdict) + '</p>';
  }

  el.heat.addEventListener('click', function (e) {
    var btn = e.target.closest('.heat-cell');
    if (btn && btn.dataset.r !== undefined) select(+btn.dataset.r, +btn.dataset.c);
  });

  /* ============================================================
     小倍數
     ============================================================ */
  function renderSmall(data) {
    var cards = data.projections || [];
    el.tabSmall.textContent = '小倍數・' + cards.length +
      (data.smallMode === 'pair' ? ' 對參數' : ' 層');

    el.smallNote.textContent = data.smallMode === 'pair'
      ? '掃描有 ' + data.continuousAxes.length + ' 條連續軸,一張圖只看得到兩條。' +
        '兩兩配對共 ' + cards.length + ' 張,其餘維度取平均(投影圖),哪一對站得住一眼看得出。' +
        '每張各自用自己的色階,只看形狀:亮的一整片 = 平原,亮的一點 = 孤峰。'
      : '連續軸只得 ' + data.continuousAxes.length + ' 條,配對出來那張就是主圖本身,' +
        '所以改為逐層並排:同一組連續取值,換一層還站不站得住。' +
        '一層亮、其餘層暗,那就是山脊,不是平原。';

    if (!cards.length) {
      el.small.innerHTML = '<div class="state-block">這次掃描沒有連續軸,畫不出小倍數。</div>';
      return;
    }

    el.small.innerHTML = cards.map(function (card) {
      var flat = [];
      card.grid.forEach(function (row) {
        row.forEach(function (v) { if (v !== null && v !== undefined) flat.push(v); });
      });
      var lo = flat.length ? Math.min.apply(null, flat) : 0;
      var hi = flat.length ? Math.max.apply(null, flat) : 1;
      var span = (hi - lo) || 1;

      var cells = '';
      card.grid.forEach(function (row, ri) {
        row.forEach(function (v, ci) {
          if (v === null || v === undefined) {
            cells += '<div class="mini-cell is-invalid"></div>';
            return;
          }
          cells += '<div class="mini-cell" title="' +
            KV.esc((card.rowAxis ? card.rowAxis + ' ' + fmtVal(card.rows[ri]) + '・' : '') +
              card.colAxis + ' ' + fmtVal(card.cols[ci]) + '：' + fmtObj(v)) + '" ' +
            'style="background:' + heatColor((v - lo) / span) + '"></div>';
        });
      });

      var title = card.title
        ? card.title
        : (card.rowAxis ? card.rowAxis + ' × ' + card.colAxis : card.colAxis);

      var note = card.best
        ? '最高 ' + fmtObj(card.best.value) + '，在 ' + paramLine(card.best.params)
        : '這一片沒有有效格。';

      return '<div class="small-card">' +
        '<div class="small-head">' +
          '<span class="small-title">' + KV.esc(title) + '</span>' +
          tag(card.verdict) +
        '</div>' +
        '<div class="small-axis">' +
          KV.esc((card.rowAxis ? '縱 ' + fmtVal(card.rows[0]) + '–' +
            fmtVal(card.rows[card.rows.length - 1]) + '　' : '') +
            '橫 ' + fmtVal(card.cols[0]) + '–' + fmtVal(card.cols[card.cols.length - 1])) +
        '</div>' +
        '<div class="mini-heat" style="grid-template-columns:repeat(' + card.cols.length + ',1fr)">' +
          cells +
        '</div>' +
        '<div class="small-note">' + KV.esc(note) + '</div>' +
      '</div>';
    }).join('');
  }

  /* ============================================================
     以現版本重掃(KARST-052)
     ------------------------------------------------------------
     彈窗照 KARST-015 原型 sweep.html 那一個:同一個標題、同一段血統說明、
     同一塊 .lineage。原型只示意「舊掃描不改寫,新掃描接上血統」,這裡真的
     會跑,並且多開放了掃描格本身讓人改——那正是重掃的用處。

     哪幾格改得動,由後端講(/api/rescan-form):驅動器、熱身期、成本、
     快照、期間、引擎全部由那幅掃描自己身上讀回,不會反問用戶,所以彈窗
     只開放掃描格。每格預填的是**當前這幅掃描的取值**,不是預設值。
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

  /* 一格:標籤 + 預填了當前取值的格 + 一句說明它是什麼軸 */
  function rescanCell(ctl) {
    var id = 'rs-' + String(ctl.name).replace(/[^A-Za-z0-9_-]/g, '_');
    return '<div class="rr-cell" data-key="' + KV.esc(ctl.name) + '">' +
      '<label for="' + id + '">' + KV.esc(ctl.label) + '</label>' +
      '<input id="' + id + '" type="text" value="' + KV.esc(ctl.value) + '" ' +
        'data-current="' + KV.esc(ctl.value) + '" spellcheck="false">' +
      (ctl.hint ? '<span class="rr-cell-hint">' + KV.esc(ctl.hint) + '</span>' : '') +
      '</div>';
  }

  function rescanBodyHTML(form) {
    var period = (form.period && form.period.length === 2)
      ? form.period[0] + ' 至 ' + form.period[1] : '—';
    var head =
      '<p>以<b>現行版本</b>重掃一次,產生一幅<b>新的掃描</b>,與本次掃描血統相連:' +
        '同一套策略、同一段期間、同一個數據快照、同一套成本,分別只在版本與你改動的掃描格。' +
        '兩幅圖可以並排比較,本次掃描不會被改寫。</p>';

    if (!form.supported) {
      return head +
        '<p class="rr-facts"><b style="color:var(--down)">這幅掃描暫時重掃不到：' +
          KV.esc(form.reason || '不知道為什麼') + '</b></p>' +
        '<p class="rr-facts">掃描 <b>' + KV.esc(form.sweepId) + '</b>・策略 <b>' +
          KV.esc(form.strategy) + '</b>・' + KV.esc(form.cells) + ' 格</p>';
    }

    return head +
      '<p>下面每一格預填的是<b>本次掃描當時的取值</b>——那是當前值,不是預設值。' +
        '一格不改就按下去,得回的會是同一組格(每一格都讀回已有的運行,不會再跑一次)。</p>' +
      '<div class="rr-grid">' +
        form.controls.map(rescanCell).join('') +
      '</div>' +
      '<p class="rr-facts">期間 <b>' + KV.esc(period) + '</b>・數據快照 <b>' +
        KV.esc(form.snapshotId) + '</b>・引擎 <b>' + KV.esc(form.engine) +
        '</b>・判讀目標 <b>' + KV.esc(form.objective) +
        '</b>　這幾件不變,所以不在這裡改。</p>' +
      '<div class="lineage">' +
        '本次掃描　<b>' + KV.esc(form.sweepId) + '</b>　' + KV.esc(form.strategy) +
          '・' + KV.esc(form.cells) + ' 格<br>' +
        '　　└─ 新掃描　<b id="rs-newid">(按下去才知道)</b>' +
      '</div>' +
      '<p class="rr-facts" id="rs-state" role="status" aria-live="polite"></p>';
  }

  function readRescanForm() {
    var controls = {};
    el.rescanBody.querySelectorAll('.rr-cell').forEach(function (cell) {
      var input = cell.querySelector('input');
      var text = input.value.trim();
      cell.classList.toggle('is-changed', text !== input.getAttribute('data-current'));
      controls[cell.getAttribute('data-key')] = text;
    });
    return controls;
  }

  function rescanSay(message, tone) {
    var box = document.getElementById('rs-state');
    if (!box) return;
    box.innerHTML = tone === 'bad'
      ? '<b style="color:var(--down)">' + KV.esc(message) + '</b>'
      : KV.esc(message);
  }

  function rescanBusy(on) {
    el.rescanGo.disabled = on;
    el.rescanBody.querySelectorAll('input').forEach(function (i) { i.disabled = on; });
  }

  function openRescan() {
    if (!state.sweepId) return;
    el.rescanBody.innerHTML = '<p class="rr-facts">讀緊這幅掃描改得動哪幾格…</p>';
    el.rescanGo.hidden = true;
    el.rescanCancel.textContent = '取消';
    if (el.rescanModal.showModal) el.rescanModal.showModal();

    KV.fetchJSON('/api/rescan-form?id=' + encodeURIComponent(state.sweepId))
      .then(function (form) {
        el.rescanBody.innerHTML = rescanBodyHTML(form);
        if (form.supported) {
          el.rescanGo.hidden = false;
          el.rescanGo.disabled = false;
        } else {
          el.rescanCancel.textContent = '知道了';
        }
      })
      .catch(function (err) {
        el.rescanBody.innerHTML = '<p class="rr-facts"><b style="color:var(--down)">' +
          KV.esc('讀不到這幅掃描的可改項：' + err.message) + '</b></p>';
        el.rescanCancel.textContent = '知道了';
      });
  }

  /* 做完了:轉去新那幅掃描。清單要重讀一次(新掃描還未在清單裡),
     所以直接把新編號寫入 hash 再重載,免得兩份清單各講各的。 */
  function rescanDone(job) {
    var idBox = document.getElementById('rs-newid');
    if (idBox) idBox.textContent = job.sweepId || '';
    rescanSay(job.note || '重掃完成,轉去新那幅掃描…');
    if (!job.sweepId) { rescanBusy(false); return; }
    location.hash = 'sweep=' + encodeURIComponent(job.sweepId);
    location.reload();
  }

  function pollRescan(jobId) {
    KV.fetchJSON('/api/job?id=' + encodeURIComponent(jobId)).then(function (job) {
      if (job.status === 'done') { rescanDone(job); return; }
      if (job.status === 'failed') {
        rescanSay('掃不完：' + (job.error || '不知道為什麼'), 'bad');
        rescanBusy(false);
        return;
      }
      rescanSay((job.status === 'queued' ? '排隊中' : '進行中') + '：' + (job.note || ''));
      setTimeout(function () { pollRescan(jobId); }, POLL_MS);
    }).catch(function (err) {
      rescanSay('查不到進度：' + err.message, 'bad');
      rescanBusy(false);
    });
  }

  function submitRescan() {
    rescanBusy(true);
    rescanSay('下單中…');
    postJSON('/api/rescan', {
      sweepId: state.sweepId,
      controls: readRescanForm(),
    }).then(function (job) {
      pollRescan(job.jobId);
    }).catch(function (err) {
      rescanSay('下不到單：' + err.message, 'bad');
      rescanBusy(false);
    });
  }

  if (el.rescanOpen) el.rescanOpen.addEventListener('click', openRescan);
  if (el.rescanGo) el.rescanGo.addEventListener('click', submitRescan);
  if (el.rescanCancel) {
    el.rescanCancel.addEventListener('click', function () { el.rescanModal.close(); });
  }
  /* 改過的格即時標出來。掛在外殼上一次就夠,彈窗內容重畫不用重新掛。 */
  if (el.rescanBody) el.rescanBody.addEventListener('input', readRescanForm);

  /* ============================================================
     開場
     ------------------------------------------------------------
     兩條入口路徑並存:
       1. hash(#sweep=&layer=)——本頁自己的重掃/換層之後留下的深連結。
       2. 查詢字串(?id=&sweep=&layer=&cell=)——KARST-079 由策略詳情頁的
          熱力圖帶直達某一格用這一條;?id= 只供麵包屑/日後核對,本頁的
          掃描不按策略過濾(倒查邏輯已在後端 api_sweep._with_strategy)。
     兩者都有時 hash 優先——那是使用者在本頁內留下的較新狀態。
     ============================================================ */
  function queryParams() {
    var out = {};
    (location.search || '').replace(/^\?/, '').split('&').forEach(function (part) {
      if (!part) return;
      var p = part.split('=');
      out[decodeURIComponent(p[0])] = decodeURIComponent(p[1] || '');
    });
    return out;
  }

  /* D-036:參數掃描不再是頂層導覽項,掛在「策略詳情」之下(與運行詳情頁
     run-view.js 同一個做法)——回上層改由麵包屑承擔。 */
  KV.mountNav('/strategy');
  KV.initTabs('.tabs');
  loading('掃描清單');

  KV.fetchJSON('/api/sweeps').then(function (list) {
    var usable = (list.sweeps || []).filter(function (s) { return !s.error; });
    state.sweeps = usable;
    if (!usable.length) {
      empty('這部機還未有掃描落檔',
        '參數掃描頁讀的是掃描落檔目錄(<span class="mono">experiments/…/掃描表.csv</span> ' +
        '連同它的判讀表)。跑過一次參數掃描並落檔之後,這一頁就有東西看。');
      return;
    }
    var hash = readHash();
    var query = queryParams();
    var wantSweep = hash.sweep || query.sweep;
    var wantLayer = hash.layer || query.layer || null;
    var found = null;
    usable.forEach(function (s) { if (s.id === wantSweep) found = s.id; });
    if (found) {
      /* ?cell= 只在查詢字串出現(hash 深連結不帶格),而且要與 ?sweep= 同一次
         導覽一併消費——換去另一次掃描就不再算數。 */
      state.pendingCellIndex = (!hash.sweep && query.cell !== undefined && query.cell !== '')
        ? parseInt(query.cell, 10) : null;
      if (isNaN(state.pendingCellIndex)) state.pendingCellIndex = null;
      toDetail(found, wantLayer);
    } else {
      toList();
    }
  }).catch(function (err) {
    fail('連不上本機服務：' + err.message, function () { location.reload(); });
  });
})();
