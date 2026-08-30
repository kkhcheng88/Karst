/* ============================================================
   Karst 原型假數據 —— 批次層(KARST-086,依 D-042 / D-045)
   ------------------------------------------------------------
   人手寫、非 tools/gen-data.mjs 產生。只供 strategy-batch.html 使用。
   全部數字為合成假數據,個股代號一律虛構,不對應任何真實標的。
   基準線借用 data.js 已產生的 K.benchmarks.QQQ/SPY 與 K.weeklyDates,
   令批次示範與原型其他頁的大市走勢同一形狀,互相對得上。

   四個示範策略 = D-042 票面要求的四組畫面狀態:
     trend-swing         — 正常:有批次、其中一次運行標「現役」
     scenario-noactive   — 正常:有批次、沒有運行標「現役」
     scenario-allfailed  — 批次存在,但批內全部運行失敗
     scenario-nobatch    — 從未執行參數掃描

   2026-08-30 用戶看過原型後裁決,原話「現役設定 don't know is what」——
   用戶不認識「現役設定」這個概念,故批次門面那張「現役設定」卡已整個拿走
   (有現役／無現役兩態都拿走,不只是拿走其中一態)。這份假數據仍然保留
   active/current 這組欄位(見下面 buildStrategy 的 cfg.active、與各運行物件
   的 current 旗標),因為歷次運行表裡「現役」那個小標籤(標在某一行運行
   編號旁邊)沒有被拿走,還要靠這組欄位驅動;「現役設定」這個概念本身
   也留在詞彙表不動。只是拿走的是「批次門面」那一張獨立卡,不是整個概念。

   2026-08-30 第三輪(D-045):單次運行層改為「時點檢視」。這一版加:
     - 個股宇宙由 24 隻擴到 78 隻(D-045 要求選股快照宇宙 60–100 隻)。
     - 每隻個股一條逐週合成價格序列(供成本、浮動盈虧、進出場價計算)。
     - 每次運行一份逐筆成交紀錄(30–60 筆,買賣分開計,部分持倉留到
       運行結尾未平倉),供淨值圖上的進出場標記、時點卡「成交」頁籤、
       「持倉」頁籤(任何時點的即時持倉)使用。
     - 選股快照改為按時點即時算(snapshotAt),不再是單一代表日快照。
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

  /* ============================================================
     虛構個股宇宙(D-045:60–100 隻,這裡取 78 隻)
     ------------------------------------------------------------
     代號與名稱都用固定種子生成,非人手逐隻打;確保不重複、可重現。
     ============================================================ */
  var SECTORS = ['半導體', '雲端軟件', '支付結算', '工業自動化', '醫療器材', '原材料', '能源儲存', '物流倉儲'];
  var SYM_LETTERS = 'BCDFGHJKLMNPQRSTVWXYZ';
  var SYM_VOWELS = 'AEIOU';
  var NAME_ROOT = [
    '納特', '維迪', '克萊', '普特', '特恩', '威森', '海力', '克斯', '奧布', '利克',
    '澤尼', '斯材', '奎維', '爾帕', '爾特', '健康', '梅里', '丹康', '多爾', '費布',
    '洛克', '沃爾', '特斯', '捷羅', '公理', '索拉', '泰德', '格拉', '維科', '路明',
    '諾瓦', '布里', '斯克', '辛德', '普魯', '姆軟', '奧爾', '瓦醫', '恩泰', '格隆',
    '倍利', '安珂', '瑞森', '晶睿', '雲策', '星軌', '極光', '磐石', '曜輝', '碧禾',
  ];
  var NAME_SUFFIX = [
    '科技', '系統', '資本', '材料', '軟件', '工業', '能源', '支付', '量子', '影像',
    '自動化', '半導體', '醫療', '物流', '傳感', '晶片', '雲端', '機器人', '電池', '倉儲',
  ];

  function genSymbol(r, used) {
    var sym;
    do {
      var len = 4 + (r() < 0.5 ? 0 : 1);
      sym = '';
      for (var i = 0; i < len; i++) {
        var pool = (i === 1 || i === 3) && r() < 0.55 ? SYM_VOWELS : SYM_LETTERS;
        sym += pool.charAt(Math.floor(r() * pool.length));
      }
    } while (used[sym]);
    used[sym] = true;
    return sym;
  }
  function genName(r, used) {
    var name;
    do {
      name = NAME_ROOT[Math.floor(r() * NAME_ROOT.length)] +
        NAME_SUFFIX[Math.floor(r() * NAME_SUFFIX.length)];
    } while (used[name]);
    used[name] = true;
    return name;
  }

  function buildUniverse(count) {
    var r = rng('universe-v3-' + count);
    var usedSym = {}, usedName = {};
    var out = [];
    for (var i = 0; i < count; i++) {
      var sym = genSymbol(r, usedSym);
      var name = genName(r, usedName);
      var sector = SECTORS[i % SECTORS.length];
      var weight = i < count * 0.22 ? 3 : (i < count * 0.55 ? 1.5 : 0.6);
      out.push({ sym: sym, name: name, sector: sector, weight: weight });
    }
    return out;
  }
  var UNIVERSE_SIZE = 78;
  var SYM_UNIVERSE = buildUniverse(UNIVERSE_SIZE);
  var SYM_INDEX = {};
  SYM_UNIVERSE.forEach(function (s, i) { SYM_INDEX[s.sym] = i; });

  function weightedPick(r, count, pool0) {
    var pool = (pool0 || SYM_UNIVERSE).slice();
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

  /* ---------------- 逐隻個股一條合成逐週價格序列(供成本、浮動盈虧、進出場價) ---------------- */
  var PRICE = {};
  (function buildPrices() {
    SYM_UNIVERSE.forEach(function (s) {
      var r = rng('price#' + s.sym);
      var p = between(r, 14, 260);
      var driftW = between(r, -0.02, 0.11) / 52;
      var volW = between(r, 0.020, 0.052);
      var out = [round(p, 2)];
      for (var i = 1; i < N; i++) {
        var wr = driftW + volW * gaussOnce(r);
        p = Math.max(0.5, p * (1 + wr));
        out.push(round(p, 2));
      }
      PRICE[s.sym] = out;
    });
  })();
  function priceAt(sym, idx) {
    var arr = PRICE[sym];
    if (!arr) return null;
    return arr[clamp(idx, 0, arr.length - 1)];
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

  /* ============================================================
     一次運行的逐筆成交(D-045:30–60 筆成交分佈全期,持倉 5–15 隻)
     ------------------------------------------------------------
     每筆「成交」= 一個買入填單或一個賣出填單。以「來回」(round trip)
     為生成單位:多數來回有入場亦有出場(兩筆成交);部分入場後留到
     運行結尾仍未平倉(只有入場那一筆,構成該次運行「最後一日」的持倉)。
     ============================================================ */
  function buildTradesForRun(runId, cagr) {
    var r = rng(runId + '#trades-v3');
    var fillsTarget = Math.round(between(r, 30, 60));
    var openCount = Math.round(between(r, 5, 15));
    var closedCount = Math.max(6, Math.round((fillsTarget - openCount) / 2));

    var trades = [];
    var seq = 0;

    function pushTrade(entryIdx, exitIdx) {
      var sym = SYM_UNIVERSE[Math.floor(r() * SYM_UNIVERSE.length)];
      var entrySlip = between(r, 0.995, 1.012);
      var entryPx = round(priceAt(sym.sym, entryIdx) * entrySlip, 2);
      var sizeScore = round(between(r, 0.55, 1.85), 2);
      var t = {
        id: runId + '-t' + String(++seq).padStart(3, '0'),
        sym: sym.sym, name: sym.name, sector: sym.sector,
        entryIdx: entryIdx, entryDate: WK[entryIdx], entryPx: entryPx,
        sizeScore: sizeScore,
        shares: Math.max(10, Math.round(sizeScore * 8000 / entryPx)),
      };
      if (exitIdx != null) {
        var exitSlip = between(r, 0.99, 1.006);
        var exitPx = round(priceAt(sym.sym, exitIdx) * exitSlip, 2);
        t.exitIdx = exitIdx; t.exitDate = WK[exitIdx]; t.exitPx = exitPx;
        t.retPct = round((exitPx / entryPx - 1) * 100, 1);
        t.holdDays = Math.max(1, Math.round((exitIdx - entryIdx) * 7));
        t.reason = t.retPct >= 0 ? '止賺/目標' : '止蝕';
      } else {
        t.exitIdx = null; t.exitDate = null; t.exitPx = null;
        t.retPct = round((priceAt(sym.sym, N - 1) / entryPx - 1) * 100, 1);
        t.holdDays = Math.max(1, Math.round((N - 1 - entryIdx) * 7));
        t.reason = '運行結尾仍未平倉';
      }
      trades.push(t);
    }

    for (var i = 0; i < closedCount; i++) {
      var entryIdx = Math.round(between(r, 0.03 * N, 0.03 * N + (i + between(r, 0.15, 0.85)) / closedCount * 0.79 * N));
      entryIdx = clamp(entryIdx, 2, N - 6);
      var holdW = Math.round(between(r, 8, 55));
      var exitIdx = clamp(entryIdx + holdW, entryIdx + 3, N - 2);
      pushTrade(entryIdx, exitIdx);
    }
    for (var j = 0; j < openCount; j++) {
      var eIdx = Math.round(between(r, 0.10 * N, 0.10 * N + (j + between(r, 0.15, 0.85)) / openCount * 0.86 * N));
      eIdx = clamp(eIdx, 2, N - 2);
      pushTrade(eIdx, null);
    }

    trades.sort(function (a, b) { return a.entryIdx - b.entryIdx; });
    return trades;
  }

  /* ---------------- 逐筆成交 → 逐日合成標記(同日多筆合成一個) ---------------- */
  function buildMarksForTrades(trades) {
    var byDate = {};
    trades.forEach(function (t) {
      (byDate[t.entryDate] = byDate[t.entryDate] || { date: t.entryDate, buys: [], sells: [] }).buys.push(t);
      if (t.exitDate) {
        (byDate[t.exitDate] = byDate[t.exitDate] || { date: t.exitDate, buys: [], sells: [] }).sells.push(t);
      }
    });
    var marks = Object.keys(byDate).sort().map(function (d) {
      var m = byDate[d];
      var nb = m.buys.length, ns = m.sells.length;
      m.side = nb && ns ? 'both' : (nb ? 'buy' : 'sell');
      m.label = (nb ? '買' + nb : '') + (nb && ns ? '／' : '') + (ns ? '沽' + ns : '');
      return m;
    });
    return { marks: marks, byDate: byDate };
  }

  /* ---------------- 全期持股分布(該次運行的單次版:同一代號可能交易多次) ---------------- */
  function buildRunHoldingsSummary(trades) {
    var agg = {};
    trades.forEach(function (t) {
      var a = agg[t.sym] || (agg[t.sym] = { sym: t.sym, name: t.name, sector: t.sector, freq: 0, sumHold: 0, sumRet: 0 });
      a.freq += 1; a.sumHold += t.holdDays; a.sumRet += t.retPct;
    });
    return Object.keys(agg).map(function (sym) {
      var a = agg[sym];
      return {
        sym: a.sym, name: a.name, sector: a.sector, freq: a.freq,
        avgHoldDays: Math.round(a.sumHold / a.freq), avgCumReturn: round(a.sumRet / a.freq, 1),
      };
    }).sort(function (a, b) { return b.freq - a.freq || b.avgCumReturn - a.avgCumReturn; }).slice(0, 10);
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
    var tradesByRun = {};
    var marksByRun = {};
    var markByDateByRun = {};
    var holdingsByRun = {};
    var agg = {}; // sym -> {freq, sumHold, sumRet, name, sector} (批次層:命中頻率 = 幾多條運行持過)

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

      var trades = buildTradesForRun(runId, cagr);
      var winners = trades.filter(function (t) { return t.exitDate && t.retPct > 0; }).length;
      var closedN = trades.filter(function (t) { return t.exitDate; }).length;
      var winRate = closedN ? Math.round(winners / closedN * 100) : Math.round(clamp(48 + (cagr - 12) * 1.1, 32, 68));
      var tradesCount = trades.length;

      var marksInfo = buildMarksForTrades(trades);
      tradesByRun[runId] = trades;
      marksByRun[runId] = marksInfo.marks;
      markByDateByRun[runId] = marksInfo.byDate;

      var holdSummary = buildRunHoldingsSummary(trades);
      holdSummary.forEach(function (h) {
        var a = agg[h.sym] || (agg[h.sym] = { sym: h.sym, name: h.name, sector: h.sector, freq: 0, sumHold: 0, sumRet: 0 });
        a.freq += 1; a.sumHold += h.avgHoldDays; a.sumRet += h.avgCumReturn;
      });
      holdingsByRun[runId] = holdSummary;

      var paramsDetail = sweepCfg.axes.map(function (ax) {
        return { k: ax.label, v: round(between(r, ax.min, ax.max), ax.decimals) + ax.unit };
      });
      var paramsLabel = paramsDetail.map(function (p) { return p.k + ' ' + p.v; }).join('・');

      var run = {
        id: runId, sweepId: sweepCfg.id,
        cagr: cagr, sortino: sortino, mdd: mdd, vol: vol, winRate: winRate, trades: tradesCount,
        paramsLabel: paramsLabel, paramsDetail: paramsDetail,
        gates: sweepCfg.gates, factors: buildFactorWeights(rng(runId + '#fac')),
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

    return {
      runs: runs, curves: byRun, holdings: holdingsBatch, holdingsByRun: holdingsByRun,
      tradesByRun: tradesByRun, marksByRun: marksByRun, markByDateByRun: markByDateByRun,
    };
  }

  var _qqqCagrCache = null;
  function cagrFromQqqOnly() { return _qqqCagrCache !== null ? _qqqCagrCache : (_qqqCagrCache = cagrFromEq(QQQ_EQ)); }

  /* ---------------- 組一套策略的批次示範 ---------------- */
  function buildStrategy(cfg) {
    var sweeps = [], runsBySweep = {}, curvesBySweep = {}, holdingsBySweep = {},
      holdingsByRun = {}, tradesByRun = {}, marksByRun = {}, markByDateByRun = {};

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
      Object.assign(tradesByRun, built.tradesByRun);
      Object.assign(marksByRun, built.marksByRun);
      Object.assign(markByDateByRun, built.markByDateByRun);
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
      tradesByRun: tradesByRun,
      marksByRun: marksByRun,
      markByDateByRun: markByDateByRun,
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
    id: 'scenario-noactive', name: '批次示範・無運行標現役', en: 'Batch Demo — No Run Marked Active',
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

  var STRATEGIES = {
    'trend-swing': trendSwing,
    'scenario-noactive': noActive,
    'scenario-allfailed': allFailed,
    'scenario-nobatch': noBatch,
  };

  /* ============================================================
     時點檢視用的查詢函數(D-045)
     ------------------------------------------------------------
     全部以「策略 id + 運行 id + 時點日期(WK 裡的一個日子)」為輸入,
     不預先算好逐日結果——只在用戶真正點一個時點時才算,原型才撐得住
     60–100 隻宇宙 × 幾百條運行的規模。
     ============================================================ */

  /* 把任意日期(URL 直連或使用者輸入)校正去最近的一個 WK 交易週 */
  function snapDate(dateStr) {
    if (!dateStr) return WK[N - 1];
    if (WK.indexOf(dateStr) >= 0) return dateStr;
    var best = WK[0], bestDiff = Infinity;
    var t = Date.parse(dateStr);
    if (isNaN(t)) return WK[N - 1];
    WK.forEach(function (d) {
      var diff = Math.abs(Date.parse(d) - t);
      if (diff < bestDiff) { bestDiff = diff; best = d; }
    });
    return best;
  }
  function idxOfDate(dateStr) {
    var i = WK.indexOf(dateStr);
    return i >= 0 ? i : (N - 1);
  }

  function tradesOf(strategyId, runId) {
    var s = STRATEGIES[strategyId];
    return (s && s.tradesByRun[runId]) || [];
  }
  function marksOf(strategyId, runId) {
    var s = STRATEGIES[strategyId];
    return (s && s.marksByRun[runId]) || [];
  }

  /* 該時點的即時持倉:代號、名稱、持倉比重(%)、成本、浮動盈虧(%) */
  function positionsAt(strategyId, runId, atDate) {
    var atIdx = idxOfDate(atDate);
    var trades = tradesOf(strategyId, runId);
    var held = trades.filter(function (t) { return t.entryIdx <= atIdx && (t.exitIdx == null || t.exitIdx > atIdx); });
    var sizeSum = held.reduce(function (a, t) { return a + t.sizeScore; }, 0) || 1;
    return held.map(function (t) {
      var px = priceAt(t.sym, atIdx);
      var floatPnl = round((px / t.entryPx - 1) * 100, 1);
      return {
        sym: t.sym, name: t.name, sector: t.sector,
        weightPct: round(t.sizeScore / sizeSum * 100, 1),
        cost: t.entryPx, price: px, floatPnl: floatPnl,
        entryDate: t.entryDate, holdDaysSoFar: Math.max(1, Math.round((atIdx - t.entryIdx) * 7)),
      };
    }).sort(function (a, b) { return b.weightPct - a.weightPct; });
  }

  /* 該時點當日的成交(找不到就退去最近一個較早的成交日) */
  function tradesOnDate(strategyId, runId, atDate) {
    var marks = marksOf(strategyId, runId);
    var exact = marks.filter(function (m) { return m.date === atDate; })[0] || null;
    var mostRecent = null;
    for (var i = 0; i < marks.length; i++) {
      if (marks[i].date <= atDate) mostRecent = marks[i]; else break;
    }
    function toFills(m) {
      if (!m) return [];
      var buys = m.buys.map(function (t) {
        return { sym: t.sym, name: t.name, side: '買', shares: t.shares, price: t.entryPx };
      });
      var sells = m.sells.map(function (t) {
        return { sym: t.sym, name: t.name, side: '沽', shares: t.shares, price: t.exitPx };
      });
      return buys.concat(sells);
    }
    return {
      date: exact ? exact.date : null,
      fills: toFills(exact),
      mostRecentDate: mostRecent ? mostRecent.date : null,
    };
  }

  /* 該時點的選股快照:全宇宙逐隻分數與去留(持倉狀態與「持倉」頁籤同步) */
  function snapshotAt(strategyId, runId, atDate) {
    var s = STRATEGIES[strategyId];
    var gates = { quality: 58, momentum: 54 };
    // 找返呢條 run 屬邊個 sweep,攞返 gates
    if (s) {
      Object.keys(s.runsBySweep).some(function (sweepId) {
        var hit = s.runsBySweep[sweepId].filter(function (r) { return r.id === runId; })[0];
        if (hit) { gates = hit.gates; return true; }
        return false;
      });
    }
    var held = positionsAt(strategyId, runId, atDate);
    var heldSet = {};
    held.forEach(function (h) { heldSet[h.sym] = true; });

    var r = rng(strategyId + '#' + runId + '#snap#' + atDate);
    var techSet = {};
    Object.keys(heldSet).forEach(function (sym) { techSet[sym] = true; });
    weightedPick(r, Math.round(SYM_UNIVERSE.length * 0.22), SYM_UNIVERSE).forEach(function (x) { techSet[x.sym] = true; });

    var fundSet = {};
    Object.keys(techSet).forEach(function (sym) { fundSet[sym] = true; });
    weightedPick(r, Math.round(SYM_UNIVERSE.length * 0.38), SYM_UNIVERSE).forEach(function (x) { fundSet[x.sym] = true; });

    var rows = SYM_UNIVERSE.map(function (sy) {
      var passFund = !!fundSet[sy.sym];
      var passTech = passFund && !!techSet[sy.sym];
      var isHeld = !!heldSet[sy.sym];
      var quality = round(passFund ? between(r, 58, 94) : between(r, 20, 57), 0);
      var momentum = round(passTech ? between(r, 54, 93) : between(r, 12, 53), 0);
      var oversold = round(between(r, 10, 90), 0);
      var composite = round(quality * 0.4 + momentum * 0.4 + (100 - oversold) * 0.2, 0);
      var status = isHeld ? '持倉' : (passTech ? '入選' : (passFund ? '觀察' : '未過'));
      return {
        sym: sy.sym, name: sy.name, sector: sy.sector,
        quality: quality, momentum: momentum, oversold: oversold, composite: composite,
        passFund: passFund, passTech: passTech, status: status,
      };
    });

    var fundCount = Object.keys(fundSet).length;
    var techCount = Object.keys(techSet).length;
    var holdCount = held.length;

    return {
      atDate: atDate, gates: gates,
      funnel: [
        { label: '範圍', count: SYM_UNIVERSE.length, hint: '全宇宙(虛構個股)' },
        { label: '基本面', count: fundCount, hint: '質素 ≥ ' + gates.quality + '・供求粗篩' },
        { label: '技術', count: techCount, hint: '動量 ≥ ' + gates.momentum },
        { label: '持倉', count: holdCount, hint: '本時點實際持有' },
      ],
      rows: rows,
    };
  }

  K.batchDemo = {
    universe: SYM_UNIVERSE,
    order: [trendSwing.id, noActive.id, allFailed.id, noBatch.id],
    strategies: STRATEGIES,
    snapDate: snapDate,
    idxOfDate: idxOfDate,
    positionsAt: positionsAt,
    tradesOnDate: tradesOnDate,
    snapshotAt: snapshotAt,
  };
})(window);
