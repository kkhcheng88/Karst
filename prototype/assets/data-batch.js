/* ============================================================
   Karst 原型假數據 —— 批次層(KARST-086,依 D-042)
   ------------------------------------------------------------
   人手寫、非 tools/gen-data.mjs 產生。只供 strategy-batch.html 使用。
   全部數字為合成假數據;個股代號一律虛構,不對應任何真實標的。
   基準線借用 data.js 已產生的 K.benchmarks.QQQ/SPY 與 K.weeklyDates,
   令批次示範與原型其他頁的大市走勢同一形狀,互相對得上。

   四個示範策略 = D-042 票面要求的四組畫面狀態:
     trend-swing         — 正常:有批次、有現役設定(現役不等於最佳批次)
     scenario-noactive   — 正常:有批次、無現役設定
     scenario-allfailed  — 批次存在,但批內全部運行失敗
     scenario-nobatch    — 從未執行參數掃描
   ============================================================ */
(function (g) {
  'use strict';
  var K = g.KARST;
  if (!K) return;

  /* ---------------- 固定種子偽亂數(同 data-ext.js 手法) ---------------- */
  function hashStr(s) {
    var h = 2166136261 >>> 0;
    for (var i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 16777619) >>> 0; }
    return h >>> 0;
  }
  function rng(seed) {
    var a = (typeof seed === 'string' ? hashStr(seed) : seed) >>> 0;
    return function () {
      a = (a + 0x6D2B79F5) >>> 0;
      var t = Math.imul(a ^ (a >>> 15), 1 | a);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }
  function between(r, lo, hi) { return lo + r() * (hi - lo); }
  function gaussOnce(r) {
    var u = 0, v = 0, s = 0;
    do { u = r() * 2 - 1; v = r() * 2 - 1; s = u * u + v * v; } while (s === 0 || s >= 1);
    return u * Math.sqrt(-2 * Math.log(s) / s);
  }
  function round(v, d) { var p = Math.pow(10, d === undefined ? 1 : d); return Math.round(v * p) / p; }
  function clamp(v, lo, hi) { return Math.max(lo, Math.min(hi, v)); }

  var WK = K.weeklyDates;
  var N = WK.length;
  var QQQ_EQ = K.benchmarks.QQQ.equity;
  var SPY_EQ = K.benchmarks.SPY.equity;
  var QQQ_RET = [0];
  for (var i = 1; i < N; i++) QQQ_RET.push(QQQ_EQ[i] / QQQ_EQ[i - 1] - 1);

  /* ---------------- 指標 ---------------- */
  function cagrFromEq(eq) {
    var years = (N - 1) / 52;
    return (Math.pow(eq[eq.length - 1] / eq[0], 1 / years) - 1) * 100;
  }
  function maxDDFromEq(eq) {
    var peak = eq[0], dd = 0;
    for (var i = 0; i < eq.length; i++) {
      peak = Math.max(peak, eq[i]);
      dd = Math.min(dd, (eq[i] - peak) / peak);
    }
    return dd * 100;
  }
  function weeklyRets(eq) {
    var out = [];
    for (var i = 1; i < eq.length; i++) out.push(eq[i] / eq[i - 1] - 1);
    return out;
  }
  function sortinoFromRets(rets) {
    var mean = rets.reduce(function (a, b) { return a + b; }, 0) / rets.length;
    var down = rets.filter(function (r) { return r < 0; });
    if (!down.length) return 2.5;
    var dvar = down.reduce(function (a, b) { return a + b * b; }, 0) / down.length;
    var dstd = Math.sqrt(dvar);
    if (dstd === 0) return 2.5;
    return clamp((mean * 52) / (dstd * Math.sqrt(52)), 0.1, 4.5);
  }

  /* ---------------- 虛構個股宇宙(24 隻,行業循環標記) ---------------- */
  var SECTORS = ['半導體', '雲端軟件', '支付結算', '工業自動化', '醫療器材', '原材料'];
  var SYM_UNIVERSE = [
    ['NALTX', '納特科技'], ['VRDIX', '維迪影像'], ['KLPTX', '克萊普特'], ['TRNWX', '特恩威'],
    ['HELXO', '海力克斯'], ['OBLIQ', '奧布利克'], ['ZENTH', '澤尼斯材料'], ['QUIVR', '奎維爾'],
    ['PALTH', '帕爾特健康'], ['MERDN', '梅里丹'], ['CONDR', '康多爾自動化'], ['FYBRK', '費布洛克'],
    ['WOLTX', '沃爾特斯'], ['GYROX', '捷羅克斯'], ['AXIOM', '公理半導體'], ['SOLRA', '索拉能源'],
    ['TIDEX', '泰德材料'], ['GRAVX', '格拉維科技'], ['LUMEN', '路明系統'], ['NOVAQ', '諾瓦量子'],
    ['BRISK', '布里斯克支付'], ['CINDR', '辛德工業'], ['PLUME', '普魯姆軟件'], ['ORVAL', '奧爾瓦醫療'],
  ].map(function (p, idx) {
    return { sym: p[0], name: p[1], sector: SECTORS[idx % SECTORS.length], weight: idx < 8 ? 3 : (idx < 16 ? 1.5 : 0.6) };
  });

  function weightedPick(r, count) {
    var pool = SYM_UNIVERSE.slice();
    var out = [];
    for (var k = 0; k < count && pool.length; k++) {
      var total = pool.reduce(function (a, s) { return a + s.weight; }, 0);
      var t = r() * total, acc = 0, pick = 0;
      for (var i = 0; i < pool.length; i++) { acc += pool[i].weight; if (t <= acc) { pick = i; break; } }
      out.push(pool[pick]);
      pool.splice(pick, 1);
    }
    return out;
  }

  /* ---------------- 一次運行的淨值曲線 ---------------- */
  function buildRunCurve(beta, driftAdjAnnual, idioVolWeekly, r) {
    var eq = [100];
    for (var i = 1; i < N; i++) {
      var wr = QQQ_RET[i] * beta + driftAdjAnnual / 5200 + idioVolWeekly * gaussOnce(r);
      eq.push(eq[i - 1] * (1 + wr));
    }
    return eq;
  }

  /* ---------------- 一次運行的持股(供批次層頻率彙整、單次層排名用) ---------------- */
  function buildHoldingsForRun(runId, cagr) {
    var r = rng(runId + '#hold');
    var count = Math.round(between(r, 8, 12));
    var picks = weightedPick(r, count);
    return picks.map(function (s) {
      var holdDays = Math.round(between(r, 18, 255));
      var cumReturn = round(between(r, -3.5, 5.5) + cagr * 0.32 + gaussOnce(r) * 3.2, 1);
      return { sym: s.sym, name: s.name, sector: s.sector, holdDays: holdDays, cumReturn: cumReturn };
    }).sort(function (a, b) { return b.holdDays - a.holdDays; });
  }

  /* ---------------- 一次運行的選股快照(單一代表日,批次頁不設逐日回捲) ---------------- */
  function buildSnapshotForRun(runId, holdings, gates, asOfDate) {
    var r = rng(runId + '#snap');
    var holdSet = {};
    holdings.forEach(function (h) { holdSet[h.sym] = true; });

    var techExtra = weightedPick(r, 3).filter(function (s) { return !holdSet[s.sym]; });
    var techSet = {};
    holdings.forEach(function (h) { techSet[h.sym] = true; });
    techExtra.forEach(function (s) { techSet[s.sym] = true; });

    var fundExtra = weightedPick(r, 4).filter(function (s) { return !techSet[s.sym]; });
    var fundSet = {};
    Object.keys(techSet).forEach(function (s) { fundSet[s] = true; });
    fundExtra.forEach(function (s) { fundSet[s.sym] = true; });

    var rows = SYM_UNIVERSE.map(function (s) {
      var passFund = !!fundSet[s.sym];
      var passTech = passFund && !!techSet[s.sym];
      var held = !!holdSet[s.sym];
      var quality = round(passFund ? between(r, 60, 93) : between(r, 22, 58), 0);
      var momentum = round(passTech ? between(r, 55, 92) : between(r, 15, 54), 0);
      var oversold = round(between(r, 12, 88), 0);
      var composite = round(quality * 0.4 + momentum * 0.4 + (100 - oversold) * 0.2, 0);
      var status = held ? '持倉' : (passTech ? '入選' : (passFund ? '觀察' : '未過'));
      return {
        sym: s.sym, name: s.name, sector: s.sector,
        quality: quality, momentum: momentum, oversold: oversold, composite: composite,
        passFund: passFund, passTech: passTech, status: status,
      };
    });

    var fundCount = Object.keys(fundSet).length;
    var techCount = Object.keys(techSet).length;
    var holdCount = holdings.length;

    return {
      asOfDate: asOfDate,
      gates: gates,
      funnel: [
        { label: '範圍', count: SYM_UNIVERSE.length, hint: '全宇宙(虛構個股)' },
        { label: '基本面', count: fundCount, hint: '質素 ≥ ' + gates.quality + '・供求粗篩' },
        { label: '技術', count: techCount, hint: '動量 ≥ ' + gates.momentum },
        { label: '持倉', count: holdCount, hint: '本次運行實際持有' },
      ],
      rows: rows,
    };
  }

  /* ---------------- 因子與參數摺疊區用的因子清單 ---------------- */
  var FACTOR_NAMES = K.factorRegistry || [];

  function buildFactorWeights(r) {
    if (!FACTOR_NAMES.length) return [];
    var raw = FACTOR_NAMES.map(function () { return between(r, 0.6, 1.4); });
    var sum = raw.reduce(function (a, b) { return a + b; }, 0);
    return FACTOR_NAMES.map(function (f, i) {
      return { id: f.id, name: f.name, ver: f.current, weightPct: Math.round(raw[i] / sum * 100) };
    });
  }

  /* ---------------- 建一個掃描批次(sweep)裡全部達標運行 ---------------- */
  function buildSweepRuns(strategyId, sweepCfg) {
    var runs = [];
    var byRun = {};
    var holdingsByRun = {};
    var snapshotByRun = {};
    var agg = {}; // sym -> {freq, sumHold, sumRet, name, sector}

    for (var k = 0; k < sweepCfg.passedCount; k++) {
      var runId = strategyId + '-' + sweepCfg.id + '-r' + String(k + 1).padStart(3, '0');
      var r = rng(runId);
      var beta = clamp(between(r, 0.55, 1.55), 0.4, 1.7);
      var driftAdj = sweepCfg.cagrCenter - cagrFromQqqOnly() + gaussOnce(r) * sweepCfg.cagrSpread;
      var idioVol = between(r, 0.010, 0.018);
      var eq = buildRunCurve(beta, driftAdj, idioVol, r);
      var rets = weeklyRets(eq);
      var cagr = round(cagrFromEq(eq), 1);
      var mdd = round(maxDDFromEq(eq), 1);
      var sortino = round(sortinoFromRets(rets), 2);
      var vol = round((rets.reduce(function (a, b) { return a + b * b; }, 0) / rets.length) ** 0.5 * Math.sqrt(52) * 100, 1);
      var winRate = Math.round(clamp(48 + (cagr - 12) * 1.1 + between(r, -6, 6), 32, 68));
      var trades = Math.round(between(r, 42, 148));

      var paramsDetail = sweepCfg.axes.map(function (ax) {
        return { k: ax.label, v: round(between(r, ax.min, ax.max), ax.decimals) + ax.unit };
      });
      var paramsLabel = paramsDetail.map(function (p) { return p.k + ' ' + p.v; }).join('・');

      var holdings = buildHoldingsForRun(runId, cagr);
      holdings.forEach(function (h) {
        var a = agg[h.sym] || (agg[h.sym] = { sym: h.sym, name: h.name, sector: h.sector, freq: 0, sumHold: 0, sumRet: 0 });
        a.freq += 1; a.sumHold += h.holdDays; a.sumRet += h.cumReturn;
      });
      holdingsByRun[runId] = holdings.slice(0, 10);

      var gates = sweepCfg.gates;
      snapshotByRun[runId] = buildSnapshotForRun(runId, holdings, gates, WK[N - 1]);

      var run = {
        id: runId, sweepId: sweepCfg.id,
        cagr: cagr, sortino: sortino, mdd: mdd, vol: vol, winRate: winRate, trades: trades,
        paramsLabel: paramsLabel, paramsDetail: paramsDetail,
        gates: gates, factors: buildFactorWeights(rng(runId + '#fac')),
        snapshot: strategyId.slice(0, 4).toUpperCase() + '-' + sweepCfg.id.slice(-4),
      };
      runs.push(run);
      byRun[runId] = eq;
    }

    var holdingsBatch = Object.keys(agg).map(function (sym) {
      var a = agg[sym];
      return {
        sym: a.sym, name: a.name, sector: a.sector,
        freq: a.freq, freqPct: round(a.freq / (sweepCfg.passedCount || 1) * 100, 0),
        avgHoldDays: Math.round(a.sumHold / a.freq), avgCumReturn: round(a.sumRet / a.freq, 1),
      };
    }).sort(function (a, b) { return b.freq - a.freq; }).slice(0, 10);

    return { runs: runs, curves: byRun, holdings: holdingsBatch, holdingsByRun: holdingsByRun, snapshotByRun: snapshotByRun };
  }

  var _qqqCagrCache = null;
  function cagrFromQqqOnly() { return _qqqCagrCache !== null ? _qqqCagrCache : (_qqqCagrCache = cagrFromEq(QQQ_EQ)); }

  /* ---------------- 組一套策略的批次示範 ---------------- */
  function buildStrategy(cfg) {
    var sweeps = [], runsBySweep = {}, curvesBySweep = {}, holdingsBySweep = {}, holdingsByRun = {}, snapshotByRun = {};

    cfg.sweeps.forEach(function (sc) {
      var built = buildSweepRuns(cfg.id, sc);
      var cagrs = built.runs.map(function (r) { return r.cagr; }).sort(function (a, b) { return a - b; });
      var sortinos = built.runs.map(function (r) { return r.sortino; }).sort(function (a, b) { return a - b; });
      var mdds = built.runs.map(function (r) { return r.mdd; }).sort(function (a, b) { return a - b; });
      function median(arr) { return arr.length ? arr[Math.floor(arr.length / 2)] : null; }
      var bestRun = built.runs.reduce(function (best, r) { return (!best || r.cagr > best.cagr) ? r : best; }, null);

      sweeps.push({
        id: sc.id, label: sc.label, date: sc.date, cells: sc.cells,
        passedCount: sc.passedCount, failedCount: sc.cells - sc.passedCount,
        passRate: round(sc.passedCount / sc.cells * 100, 0),
        medianCagr: median(cagrs), medianSortino: median(sortinos), medianMdd: median(mdds),
        bestRunId: bestRun ? bestRun.id : null,
      });
      runsBySweep[sc.id] = built.runs;
      curvesBySweep[sc.id] = built.curves;
      holdingsBySweep[sc.id] = built.holdings;
      Object.assign(holdingsByRun, built.holdingsByRun);
      Object.assign(snapshotByRun, built.snapshotByRun);
    });

    var bestSweep = sweeps.reduce(function (best, s) {
      if (!s.passedCount) return best;
      return (!best || s.medianCagr > best.medianCagr) ? s : best;
    }, null);

    return {
      id: cfg.id, name: cfg.name, en: cfg.en,
      dates: WK, spy: SPY_EQ, qqq: QQQ_EQ,
      hasActiveSetup: !!cfg.active,
      active: cfg.active || null,
      sweeps: sweeps,
      runsBySweep: runsBySweep,
      curvesBySweep: curvesBySweep,
      holdingsBySweep: holdingsBySweep,
      holdingsByRun: holdingsByRun,
      snapshotByRun: snapshotByRun,
      bestSweepId: bestSweep ? bestSweep.id : null,
    };
  }

  /* ============================================================
     四個示範情境
     ============================================================ */
  var trendSwing = buildStrategy({
    id: 'trend-swing', name: '趨勢波段', en: 'Trend Swing',
    active: { sweepId: 'sw-2026-06', runIndex: 0.4 },
    sweeps: [
      { id: 'sw-2026-06', label: '2026-06 掃描・止蝕×倉位', date: '2026-06-02', cells: 118, passedCount: 71,
        cagrCenter: 13.5, cagrSpread: 3.2, gates: { quality: 58, momentum: 54 },
        axes: [{ label: '止蝕', unit: '%', min: 4, max: 10, decimals: 1 },
               { label: '倉位上限', unit: '%', min: 8, max: 20, decimals: 0 }] },
      { id: 'sw-2026-07', label: '2026-07 掃描・週期×賠率門檻', date: '2026-07-14', cells: 132, passedCount: 93,
        cagrCenter: 17.9, cagrSpread: 2.6, gates: { quality: 60, momentum: 56 },
        axes: [{ label: '突破 N', unit: '日', min: 12, max: 55, decimals: 0 },
               { label: '賠率門檻', unit: 'R', min: 1.2, max: 2.6, decimals: 1 }] },
      { id: 'sw-2026-08', label: '2026-08 掃描・止蝕×目標', date: '2026-08-20', cells: 104, passedCount: 76,
        cagrCenter: 11.2, cagrSpread: 2.9, gates: { quality: 57, momentum: 53 },
        axes: [{ label: '止蝕', unit: '%', min: 5, max: 9, decimals: 1 },
               { label: '目標', unit: 'R', min: 1.5, max: 3.5, decimals: 1 }] },
    ],
  });
  // 現役設定刻意揀非最佳批次那一格,示範「現役設定不冒充門面」
  (function () {
    var s = trendSwing.sweeps.filter(function (s) { return s.id === trendSwing.active.sweepId; })[0];
    var list = trendSwing.runsBySweep[trendSwing.active.sweepId];
    var idx = Math.min(list.length - 1, Math.floor(list.length * trendSwing.active.runIndex));
    trendSwing.active.runId = list[idx].id;
    list[idx].current = true;
  })();

  var noActive = buildStrategy({
    id: 'scenario-noactive', name: '批次示範・無現役設定', en: 'Batch Demo — No Active Setup',
    active: null,
    sweeps: [
      { id: 'sw-a', label: '2026-05 掃描・回望期×持倉數', date: '2026-05-10', cells: 96, passedCount: 62,
        cagrCenter: 10.8, cagrSpread: 2.4, gates: { quality: 55, momentum: 50 },
        axes: [{ label: '回望期', unit: '週', min: 8, max: 26, decimals: 0 },
               { label: '持倉數', unit: '隻', min: 6, max: 14, decimals: 0 }] },
      { id: 'sw-b', label: '2026-07 掃描・因子權重', date: '2026-07-22', cells: 140, passedCount: 99,
        cagrCenter: 14.6, cagrSpread: 2.1, gates: { quality: 59, momentum: 55 },
        axes: [{ label: '質素權重', unit: '%', min: 20, max: 55, decimals: 0 },
               { label: '動量權重', unit: '%', min: 20, max: 55, decimals: 0 }] },
    ],
  });

  var allFailed = buildStrategy({
    id: 'scenario-allfailed', name: '批次示範・批次全失敗', en: 'Batch Demo — All Batches Failed',
    active: null,
    sweeps: [
      { id: 'sw-x', label: '2026-04 掃描・止蝕×目標', date: '2026-04-18', cells: 54, passedCount: 0,
        cagrCenter: 0, cagrSpread: 0, gates: { quality: 60, momentum: 55 },
        axes: [{ label: '止蝕', unit: '%', min: 4, max: 10, decimals: 1 },
               { label: '目標', unit: 'R', min: 1.2, max: 2.4, decimals: 1 }] },
      { id: 'sw-y', label: '2026-08 掃描・重試(仍全失敗)', date: '2026-08-05', cells: 40, passedCount: 0,
        cagrCenter: 0, cagrSpread: 0, gates: { quality: 60, momentum: 55 },
        axes: [{ label: '回望期', unit: '週', min: 10, max: 30, decimals: 0 },
               { label: '持倉數', unit: '隻', min: 5, max: 12, decimals: 0 }] },
    ],
  });

  var noBatch = buildStrategy({
    id: 'scenario-nobatch', name: '批次示範・未曾掃描', en: 'Batch Demo — No Sweep Yet',
    active: null,
    sweeps: [],
  });

  K.batchDemo = {
    universe: SYM_UNIVERSE,
    order: [trendSwing.id, noActive.id, allFailed.id, noBatch.id],
    strategies: {
      'trend-swing': trendSwing,
      'scenario-noactive': noActive,
      'scenario-allfailed': allFailed,
      'scenario-nobatch': noBatch,
    },
  };
})(window);
