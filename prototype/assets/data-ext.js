/* ============================================================
   Karst 原型 —— 第二版假數據補充
   ------------------------------------------------------------
   data.js 是第一版原型的假數據,這裡只做「加」,不改它。
   全部用固定種子的偽亂數生成,所以每次開頁的數字都一模一樣,
   方便對住實物討論,不會今日一個樣、明日另一個樣。

   本檔加入四樣東西:
     1. K.groups / K.allStrategies —— 總覽的分組表(20 行示意密度)
     2. K.picks                    —— 策略頁的「選股快照」(三個示意日期)
     3. K.tradeSeries(trade)       —— 運行頁逐筆交易的蠟燭圖與因子序列
     4. K.sweepAxes / K.sweepSlice / K.sweepSmall —— 掃描頁的切片與小倍數
   ============================================================ */
(function (g) {
  'use strict';

  var K = g.KARST;
  if (!K) return;

  /* ---------------- 固定種子偽亂數 ---------------- */
  function hashStr(s) {
    var h = 2166136261 >>> 0;
    for (var i = 0; i < s.length; i++) {
      h ^= s.charCodeAt(i);
      h = Math.imul(h, 16777619) >>> 0;
    }
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
  function round(v, d) { var p = Math.pow(10, d === undefined ? 1 : d); return Math.round(v * p) / p; }
  function clamp(v, lo, hi) { return Math.max(lo, Math.min(hi, v)); }

  var YEARS = K.meta.years;
  var QQQ = K.benchmarks.QQQ.metrics;

  /* ============================================================
     一、策略總覽:分組 + 示意策略
     ============================================================ */
  K.groups = [
    { id: 'funnel', name: '基本面漏斗', note: '先用基本面收窄範圍,再落技術關' },
    { id: 'tech',   name: '純技術',     note: '只看價與量,不看賬目' },
    { id: 'follow', name: '跟隨組合',   note: '跟別人的持倉,自己不選股' },
    { id: 'event',  name: '事件驅動',   note: '等一件事發生才動手' },
  ];

  var GROUP_OF = {
    'bottleneck': 'funnel', 'factor-mix': 'funnel', 'oversold': 'funnel',
    'minervini': 'tech', 'trend-swing': 'tech',
    'sa': 'follow', 'pelosi': 'follow',
  };

  /* 示意策略只為撐出密度,證明「幾百套都排得下」。名字刻意寫成示意,不冒充真策略。 */
  var DEMO_PLAN = [
    { group: 'funnel', tagline: '現金流穩定 + 估值回落,兩關都要過' },
    { group: 'funnel', tagline: '毛利率連續改善,行業內排前四分一' },
    { group: 'funnel', tagline: '負債比低於同業中位,再揀動量最強那批' },
    { group: 'tech',   tagline: '週線突破前高,日線回踩不破就入' },
    { group: 'tech',   tagline: '成交量放大配合價格收窄,等待方向' },
    { group: 'tech',   tagline: '兩條均線黃金交叉,趨勢確認才跟' },
    { group: 'tech',   tagline: '相對強度排名前 5%,每月換馬一次' },
    { group: 'follow', tagline: '跟隨三個公開組合的交集持倉' },
    { group: 'follow', tagline: '基金季度申報變化,加碼那批才跟' },
    { group: 'event',  tagline: '業績公布後跳空,順跳空方向做' },
    { group: 'event',  tagline: '納入指數前後的資金流,做提前量' },
    { group: 'event',  tagline: '大股東增持申報,一週內入場' },
    { group: 'event',  tagline: '回購計劃啟動後的持續買盤' },
  ];

  /* 用目標年化倒推一條週線淨值,終點對得上累計回報,中間有起有伏 */
  function makeEquity(r, n, cumReturnPct, volPct) {
    var target = Math.log(1 + cumReturnPct / 100);
    var step = volPct / 100 / Math.sqrt(52);
    var raw = [], acc = 0, mom = 0;
    for (var i = 0; i < n - 1; i++) {
      var shock = (r() + r() + r() - 1.5) * step * 2.2;
      mom = mom * 0.72 + shock * 0.28;
      var v = shock + mom;
      raw.push(v);
      acc += v;
    }
    var adj = (target - acc) / (n - 1);
    var eq = [100];
    for (i = 0; i < n - 1; i++) eq.push(round(eq[i] * Math.exp(raw[i] + adj), 2));
    return eq;
  }

  function maxDrawdown(eq) {
    var peak = eq[0], worst = 0;
    for (var i = 1; i < eq.length; i++) {
      if (eq[i] > peak) peak = eq[i];
      var dd = (eq[i] / peak - 1) * 100;
      if (dd < worst) worst = dd;
    }
    return round(worst, 1);
  }

  var demoRows = DEMO_PLAN.map(function (d, i) {
    var n = String(i + 1).padStart(2, '0');
    var r = rng('demo-strategy-' + n);
    var cagr = round(between(r, 4.5, 27.5), 1);
    var vol = round(between(r, 13, 27), 1);
    var cum = round((Math.pow(1 + cagr / 100, YEARS) - 1) * 100, 1);
    var eq = makeEquity(rng('demo-eq-' + n), K.weeklyDates.length, cum, vol);
    var mdd = maxDrawdown(eq);
    return {
      id: 'demo-' + n,
      name: '示意策略 ' + n,
      en: 'Demo Strategy ' + n,
      kind: d.group === 'follow' ? '跟隨組合' : '策略',
      group: d.group,
      tagline: d.tagline,
      demo: true,
      equity: eq,
      metrics: {
        cumReturn: cum,
        cagr: cagr,
        maxDD: mdd,
        vol: vol,
        sortino: round(between(r, 0.5, 2.3), 2),
        winRate: Math.round(between(r, 36, 64)),
        plRatio: round(between(r, 1.1, 3.4), 1),
        trades: Math.round(between(r, 45, 320)),
      },
    };
  });

  /* 真名七套排先,示意策略排後,同一張表分不出兩種血統才是重點 */
  K.allStrategies = K.strategies.map(function (s) {
    return {
      id: s.id, name: s.name, en: s.en, kind: s.kind,
      group: GROUP_OF[s.id] || 'tech',
      tagline: s.tagline, demo: false,
      equity: s.equity, metrics: s.metrics,
      href: s.id === 'trend-swing' ? 'strategy.html' : null,
    };
  }).concat(demoRows);

  /* 預設置頂:紙上交易那套排頭,另外兩套是長期分數最高那批 */
  K.pinnedDefault = ['trend-swing', 'minervini', 'oversold'];

  /* ============================================================
     二、選股快照(策略頁)
     ============================================================ */
  var UNIVERSE = [
    { sym: 'NVLS', name: '諾瓦半導體', sector: '半導體' },
    { sym: 'CYPR', name: '賽普瑞斯', sector: '資料中心' },
    { sym: 'VTKS', name: '維特智造', sector: '工業自動化' },
    { sym: 'TSVA', name: '特斯瓦電控', sector: '電力設備' },
    { sym: 'HLIO', name: '赫利奧能源', sector: '再生能源' },
    { sym: 'PLNX', name: '普蘭尼克斯', sector: '網絡安全' },
    { sym: 'ARTC', name: '方舟科技', sector: '軟件' },
    { sym: 'QNTA', name: '量塔數據', sector: '雲端服務' },
    { sym: 'KYRO', name: '凱羅生技', sector: '生物製藥' },
    { sym: 'DLTA', name: '德爾塔醫藥', sector: '製藥' },
    { sym: 'STRA', name: '層雲材料', sector: '特用化工' },
    { sym: 'AXNT', name: '軸心工具', sector: '精密機械' },
    { sym: 'ZEPH', name: '西風航太', sector: '航太國防' },
    { sym: 'MRDN', name: '子午線物流', sector: '運輸' },
    { sym: 'BLFN', name: '藍鰭海事', sector: '海運' },
    { sym: 'FTHM', name: '深測海洋', sector: '海洋工程' },
    { sym: 'GRVN', name: '格雷芬金融', sector: '金融科技' },
    { sym: 'LUMD', name: '流明顯示', sector: '顯示面板' },
    { sym: 'NMBS', name: '紐姆巴斯', sector: '消費電子' },
    { sym: 'OKLA', name: '奧克拉建材', sector: '建築材料' },
    { sym: 'OKRA', name: '橡域農業', sector: '農業科技' },
    { sym: 'WNDR', name: '溫德旅遊', sector: '旅遊' },
    { sym: 'CDRA', name: '雪松醫療', sector: '醫療服務' },
    { sym: 'RVNA', name: '瑞文娜零售', sector: '零售' },
    { sym: 'BRDX', name: '廣基指數 ETF', sector: 'ETF・大盤' },
    { sym: 'SEMX', name: '半導體指數 ETF', sector: 'ETF・行業' },
  ];

  var HELD = {};
  K.trendSwing.paper.positions.forEach(function (p) { HELD[p.sym] = true; });

  var PICK_DATES = [
    { date: '2026-08-21', label: '2026-08-21(最新)', scope: 500, fund: 82, tech: 24, held: 10 },
    { date: '2026-08-14', label: '2026-08-14', scope: 500, fund: 91, tech: 31, held: 11 },
    { date: '2026-08-07', label: '2026-08-07', scope: 498, fund: 76, tech: 19, held: 9 },
  ];

  K.picks = {
    dates: PICK_DATES,
    /* 三層關卡的門檻,寫死在這裡,表格與漏斗都指得回同一組數 */
    gates: { quality: 60, momentum: 62 },
    byDate: {},
  };

  PICK_DATES.forEach(function (d) {
    var rows = UNIVERSE.map(function (u) {
      var r = rng('pick-' + d.date + '-' + u.sym);
      var quality = round(between(r, 22, 96), 1);
      var momentum = round(between(r, 18, 95), 1);
      var oversold = round(between(r, 2, 88), 1);
      var passFund = quality >= K.picks.gates.quality;
      var passTech = passFund && momentum >= K.picks.gates.momentum;
      /* 現時持有的照樣每日重新評分。今日不過關不等於即刻沽,所以狀態仍然是「持倉」。 */
      var isHeld = !!HELD[u.sym];
      var status = isHeld ? '持倉' : (passTech ? '入選' : (passFund ? '觀察' : '未過'));
      return {
        sym: u.sym, name: u.name, sector: u.sector,
        quality: quality, momentum: momentum, oversold: oversold,
        composite: round(quality * 0.4 + momentum * 0.45 + oversold * 0.15, 1),
        passFund: passFund, passTech: passTech, status: status,
      };
    });
    /* 綜合分高的排前,一眼睇到頂上那批就是入選那批 */
    rows.sort(function (a, b) { return b.composite - a.composite; });
    K.picks.byDate[d.date] = {
      funnel: [
        { label: '範圍', hint: '當日可交易的全部標的', count: d.scope },
        { label: '過基本面關', hint: '質素分達 ' + K.picks.gates.quality + ' 分', count: d.fund },
        { label: '過技術關', hint: '再要動量分達 ' + K.picks.gates.momentum + ' 分', count: d.tech },
        { label: '持倉', hint: '扣除倉位上限與風控後實際持有', count: d.held },
      ],
      rows: rows,
    };
  });

  /* ============================================================
     三、逐筆交易的蠟燭圖與因子(運行頁鑽入用)
     ------------------------------------------------------------
     點一筆先生成一筆,不預先造 52 套,開頁快得多。
     ============================================================ */
  var seriesCache = {};

  function addDays(iso, n) {
    var d = new Date(iso + 'T00:00:00Z');
    d.setUTCDate(d.getUTCDate() + n);
    return d.toISOString().slice(0, 10);
  }
  function tradingDays(fromISO, toISO) {
    var out = [], cur = fromISO;
    var guard = 0;
    while (cur <= toISO && guard++ < 4000) {
      var wd = new Date(cur + 'T00:00:00Z').getUTCDay();
      if (wd !== 0 && wd !== 6) out.push(cur);
      cur = addDays(cur, 1);
    }
    return out;
  }

  /* 由 startV 走到 endV 的一段路,中間有波動,兩端對得準 */
  function pathBetween(r, n, startV, endV, volPct) {
    if (n <= 1) return [endV];
    var step = volPct / 100;
    var raw = [], acc = 0;
    for (var i = 0; i < n - 1; i++) {
      var v = (r() + r() - 1) * step * 1.6;
      raw.push(v); acc += v;
    }
    var adj = (Math.log(endV / startV) - acc) / (n - 1);
    var out = [startV];
    for (i = 0; i < n - 1; i++) out.push(out[i] * Math.exp(raw[i] + adj));
    return out;
  }

  K.tradeSeries = function (t) {
    if (seriesCache[t.id]) return seriesCache[t.id];

    var r = rng('trade-' + t.id + '-' + t.sym);
    var winFrom = addDays(t.entryDate, -62);
    var winTo = addDays(t.exitDate, 38);
    var days = tradingDays(winFrom, winTo);

    var iEntry = 0, iExit = days.length - 1, i;
    for (i = 0; i < days.length; i++) {
      if (days[i] <= t.entryDate) iEntry = i;
      if (days[i] <= t.exitDate) iExit = i;
    }
    if (iExit <= iEntry) iExit = Math.min(days.length - 1, iEntry + 1);

    var vol = clamp(Math.abs(t.retPct) / Math.max(6, t.holdDays) * 6 + 1.4, 1.4, 3.6);

    /* 進場前:由一個較低的位置爬上進場價,做出「突破」的樣 */
    var pre = pathBetween(r, iEntry + 1, t.entryPx * between(r, 0.78, 0.94), t.entryPx, vol);
    var mid = pathBetween(r, iExit - iEntry + 1, t.entryPx, t.exitPx, vol);
    var post = pathBetween(r, days.length - iExit, t.exitPx, t.exitPx * between(r, 0.9, 1.12), vol);

    var closes = pre.concat(mid.slice(1)).concat(post.slice(1));

    var candles = [], volumes = [];
    for (i = 0; i < days.length; i++) {
      var c = closes[i];
      var prevC = i ? closes[i - 1] : c * (1 - between(r, -0.01, 0.01));
      var open = prevC * (1 + (r() - 0.5) * 0.012);
      var hi = Math.max(open, c) * (1 + r() * 0.014);
      var lo = Math.min(open, c) * (1 - r() * 0.014);
      candles.push({
        time: days[i],
        open: round(open, 2), high: round(hi, 2), low: round(lo, 2), close: round(c, 2),
      });
      var base = 900000 + Math.floor(r() * 700000);
      if (i === iEntry || i === iExit) base = Math.floor(base * between(r, 1.8, 2.6));
      volumes.push({ time: days[i], value: base });
    }

    var markers = [
      { time: days[iEntry], side: 'buy', price: round(t.entryPx, 2), text: '買入 進場' },
      { time: days[iExit], side: 'sell', price: round(t.exitPx, 2), text: '賣出 ' + t.reason },
    ];

    /* 因子:動量在進場前爬升、出場前回落;超賣度反向;質素與供求慢變 */
    var factors = days.map(function (day, idx) {
      var fr = rng('factor-' + t.id + '-' + idx);
      var phase = (idx - iEntry) / Math.max(6, iExit - iEntry);
      var mom = clamp(46 + 34 * Math.sin(clamp(phase, -1.2, 1.6) * 1.5) + (fr() - 0.5) * 12, 4, 98);
      var qual = clamp(58 + 22 * Math.sin(idx / 26 + 1.1) + (fr() - 0.5) * 8, 6, 97);
      var over = clamp(96 - mom + (fr() - 0.5) * 16, 2, 96);
      var sup = clamp(50 + 26 * Math.sin(idx / 17) + (fr() - 0.5) * 10, 5, 95);
      var comp = qual * 0.4 + mom * 0.45 + over * 0.15;
      return {
        time: day,
        quality: round(qual, 1), momentum: round(mom, 1),
        oversold: round(over, 1), supply: round(sup, 1),
        composite: round(comp, 1),
        selected: idx >= iEntry && idx <= iExit,
      };
    });

    var out = {
      trade: t, days: days, candles: candles, volumes: volumes,
      markers: markers, factors: factors,
      entryIndex: iEntry, exitIndex: iExit,
    };
    seriesCache[t.id] = out;
    return out;
  };

  /* ============================================================
     四、參數掃描:切片選擇器 + 小倍數
     ============================================================ */
  K.sweepAxes = [
    { id: 'risk', label: '風險比例', hint: '每筆交易願意輸掉的組合百分比',
      values: [0.5, 0.75, 1.0, 1.5], def: 1.0, fmt: function (v) { return v + '%'; } },
    { id: 'ma', label: '均線長度', hint: '判斷大市方向那條均線的日數',
      values: [50, 100, 150, 200], def: 150, fmt: function (v) { return v + ' 日'; } },
  ];

  function neighbourMean(grid, ri, ci) {
    var sum = 0, n = 0;
    for (var dr = -1; dr <= 1; dr++) {
      for (var dc = -1; dc <= 1; dc++) {
        if (!dr && !dc) continue;
        var r2 = ri + dr, c2 = ci + dc;
        if (r2 < 0 || c2 < 0 || r2 >= grid.length || c2 >= grid[0].length) continue;
        sum += grid[r2][c2].cagr; n++;
      }
    }
    return n ? sum / n : 0;
  }

  var baseSlice = null;

  K.sweepSlice = function (risk, ma) {
    var isBase = (risk === 1.0 && ma === 150);

    if (isBase) {
      if (baseSlice) return baseSlice;
      var plateauSet = {};
      K.sweep.plateauCells.forEach(function (p) { plateauSet[p[0] + ',' + p[1]] = true; });
      var spikePos = null;
      K.sweep.grid.forEach(function (row, ri) {
        row.forEach(function (c, ci) { if (c.spike) spikePos = [ri, ci]; });
      });
      baseSlice = {
        grid: K.sweep.grid,
        plateauSet: plateauSet,
        plateauCenter: K.sweep.plateauCenter,
        spikePos: spikePos,
        isBase: true,
      };
      return baseSlice;
    }

    var key = 'slice-' + risk + '-' + ma;
    if (seriesCache[key]) return seriesCache[key];

    var r = rng(key);
    var R = K.sweep.rows.length, C = K.sweep.cols.length;

    /* 換了切片,好的那一區會搬位、整體水平會升降 —— 這正是要示意的事 */
    var r0 = Math.floor(between(r, 1, R - 2));
    var c0 = Math.floor(between(r, 1, C - 2));
    var amp = between(r, 7, 13);
    var damp = between(r, 0.45, 0.8);
    var lift = between(r, -3.5, 3.5);

    var grid = [], flatVals = [];
    for (var ri = 0; ri < R; ri++) {
      var row = [];
      for (var ci = 0; ci < C; ci++) {
        var b = K.sweep.grid[ri][ci];
        var bump = amp * Math.exp(-(Math.pow(ri - r0, 2) / 5.5 + Math.pow(ci - c0, 2) / 4.5));
        var noise = (rng(key + '-' + ri + '-' + ci)() - 0.5) * 2.4;
        var cagr = round(b.cagr * damp + bump + lift + noise, 1);
        row.push({
          n: b.n, s: b.s, cagr: cagr,
          mdd: round(clamp(b.mdd * between(r, 0.85, 1.2), -58, -12), 1),
          sortino: round(clamp(0.35 + cagr / 16, 0.2, 2.6), 2),
          trades: b.trades,
          spike: false,
        });
        flatVals.push(cagr);
      }
      grid.push(row);
    }

    /* 找平原:鄰域平均最高那格 */
    var bestMean = -1e9, pc = [1, 1];
    for (ri = 1; ri < R - 1; ri++) {
      for (ci = 1; ci < C - 1; ci++) {
        var m = neighbourMean(grid, ri, ci);
        if (m > bestMean) { bestMean = m; pc = [ri, ci]; }
      }
    }
    var plateauSet2 = {};
    var centreVal = grid[pc[0]][pc[1]].cagr;
    for (ri = 0; ri < R; ri++) {
      for (ci = 0; ci < C; ci++) {
        if (Math.abs(ri - pc[0]) <= 2 && Math.abs(ci - pc[1]) <= 1 &&
            grid[ri][ci].cagr >= centreVal - 3) {
          plateauSet2[ri + ',' + ci] = true;
        }
      }
    }

    /* 種一個孤峰在離平原遠的地方,方便對照 */
    var sr = (pc[0] + Math.floor(R / 2)) % R;
    var sc = (pc[1] + Math.floor(C / 2)) % C;
    if (plateauSet2[sr + ',' + sc]) { sc = (sc + 2) % C; }
    grid[sr][sc].cagr = round(neighbourMean(grid, sr, sc) + between(r, 6.5, 9.5), 1);
    grid[sr][sc].sortino = round(clamp(0.35 + grid[sr][sc].cagr / 16, 0.2, 2.6), 2);
    grid[sr][sc].spike = true;

    var out = {
      grid: grid, plateauSet: plateauSet2, plateauCenter: pc,
      spikePos: [sr, sc], isBase: false,
    };
    seriesCache[key] = out;
    return out;
  };

  /* ---- 小倍數:四個參數兩兩配對,共六張 ---- */
  var SMALL_PAIRS = [
    { row: '突破日數 N', col: '止蝕幅度',  rows: [15, 25, 30, 40, 50], cols: [5, 6, 8, 10, 14], cur: [2, 2] },
    { row: '突破日數 N', col: '風險比例',  rows: [15, 25, 30, 40, 50], cols: [0.5, 0.75, 1.0, 1.25, 1.5], cur: [2, 2] },
    { row: '突破日數 N', col: '均線長度',  rows: [15, 25, 30, 40, 50], cols: [50, 100, 150, 200, 250], cur: [2, 2] },
    { row: '止蝕幅度',   col: '風險比例',  rows: [5, 6, 8, 10, 14], cols: [0.5, 0.75, 1.0, 1.25, 1.5], cur: [2, 2] },
    { row: '止蝕幅度',   col: '均線長度',  rows: [5, 6, 8, 10, 14], cols: [50, 100, 150, 200, 250], cur: [2, 2] },
    { row: '風險比例',   col: '均線長度',  rows: [0.5, 0.75, 1.0, 1.25, 1.5], cols: [50, 100, 150, 200, 250], cur: [2, 2] },
  ];

  K.sweepSmall = SMALL_PAIRS.map(function (p, idx) {
    var r = rng('small-' + idx);
    var R = p.rows.length, C = p.cols.length;
    /* 一半做成平原、一半做成孤峰,示意「六張圖裡通常只有兩三張站得住」 */
    var wantSpike = idx === 1 || idx === 4;
    var r0 = between(r, 0.6, R - 1.6), c0 = between(r, 0.6, C - 1.6);
    var amp = wantSpike ? between(r, 3, 5) : between(r, 7, 10);
    var spread = wantSpike ? 0.9 : 4.2;
    var grid = [];
    for (var ri = 0; ri < R; ri++) {
      var row = [];
      for (var ci = 0; ci < C; ci++) {
        var bump = amp * Math.exp(-(Math.pow(ri - r0, 2) + Math.pow(ci - c0, 2)) / spread);
        var noise = (rng('small-' + idx + '-' + ri + '-' + ci)() - 0.5) * 2.2;
        row.push(round(clamp(9 + bump + noise, 2, 32), 1));
      }
      grid.push(row);
    }
    if (wantSpike) {
      var sr = Math.round(clamp(r0, 0, R - 1)), sc = Math.round(clamp(c0, 0, C - 1));
      grid[sr][sc] = round(grid[sr][sc] + between(r, 7, 10), 1);
    }
    return {
      rowLabel: p.row, colLabel: p.col,
      rows: p.rows, cols: p.cols,
      cur: p.cur, grid: grid,
      verdict: wantSpike ? '孤峰' : '平原',
      note: wantSpike
        ? '只有一格特別好,四周即刻跌落 —— 這一對參數靠不住。'
        : '好的那一片連成一整塊,參數偏一格照樣賺錢。',
    };
  });

  /* ============================================================
     五、版本冊:因子現行版本 + 每次運行綁定的版本
     ------------------------------------------------------------
     一次運行綁死當時的策略版本與因子版本。之後因子計法更新了,
     舊運行的數字**不會**自動跟上 —— 這一點要在畫面上講明,
     否則看的人會當那個數字仍然代表現在的計法。
     ============================================================ */
  K.factorRegistry = [
    { id: 'supply',   name: '供求因子', en: 'Supply-Demand Factor',
      current: 'v1.3', updatedAt: '2026-08-20',
      whatChanged: '改用成交金額加權,取代原本的成交股數加權' },
    { id: 'momentum', name: '動量因子', en: 'Momentum Factor',
      current: 'v2.0', updatedAt: '2026-05-11',
      whatChanged: '加入 12-1 動量,剔除最近一個月的反轉' },
    { id: 'quality',  name: '質素因子', en: 'Quality Factor',
      current: 'v1.1', updatedAt: '2026-03-02',
      whatChanged: '自由現金流改用四季滾動' },
  ];

  var FACTOR_BY_ID = {};
  K.factorRegistry.forEach(function (f) { FACTOR_BY_ID[f.id] = f; });

  function verNums(v) {
    return String(v).replace(/^v/, '').split('.').map(function (x) { return parseInt(x, 10) || 0; });
  }
  function verOlder(a, b) {
    var x = verNums(a), y = verNums(b);
    for (var i = 0; i < Math.max(x.length, y.length); i++) {
      var xa = x[i] || 0, ya = y[i] || 0;
      if (xa !== ya) return xa < ya;
    }
    return false;
  }

  K.strategyCurrentVer = 'v2.3.0';

  /* 這次運行綁定的版本 —— 供求因子停在 v1.2,現行已是 v1.3 */
  K.run.binding = {
    strategyVer: 'v2.3.0',
    factors: [
      { id: 'supply',   ver: 'v1.2' },
      { id: 'momentum', ver: 'v2.0' },
      { id: 'quality',  ver: 'v1.1' },
    ],
  };

  /* 這次掃描綁定的版本 —— 策略同因子都落後了 */
  K.sweep.binding = {
    strategyVer: 'v2.2.0',
    factors: [
      { id: 'supply',   ver: 'v1.2' },
      { id: 'momentum', ver: 'v2.0' },
      { id: 'quality',  ver: 'v1.1' },
    ],
  };

  /**
   * 查一個綁定有沒有落後於現行版本。
   * 回傳 { stale: bool, items: [{kind,name,was,now,updatedAt,whatChanged}] }
   */
  K.staleCheck = function (binding) {
    var items = [];
    if (verOlder(binding.strategyVer, K.strategyCurrentVer)) {
      items.push({
        kind: '策略', name: '趨勢波段',
        was: binding.strategyVer, now: K.strategyCurrentVer,
        updatedAt: '2026-08-12', whatChanged: '倉位上限由 8 個放寬到 12 個',
      });
    }
    binding.factors.forEach(function (f) {
      var reg = FACTOR_BY_ID[f.id];
      if (reg && verOlder(f.ver, reg.current)) {
        items.push({
          kind: '因子', name: reg.name,
          was: f.ver, now: reg.current,
          updatedAt: reg.updatedAt, whatChanged: reg.whatChanged,
        });
      }
    });
    return { stale: items.length > 0, items: items };
  };

  /** 把綁定的因子版本寫成一行,例如「供求因子 v1.2・動量因子 v2.0」 */
  K.factorLine = function (binding) {
    return binding.factors.map(function (f) {
      var reg = FACTOR_BY_ID[f.id];
      return (reg ? reg.name : f.id) + ' ' + f.ver;
    }).join('・');
  };

  /* ============================================================
     六、選股快照的版本切換
     ------------------------------------------------------------
     同一日、不同算法版本,漏斗會收得不同鬆緊。
     ============================================================ */
  K.picks.versions = [
    { id: 'v2.3.0', label: '現役設定 v2.3.0', runId: 'RUN-2026-0812-07', live: true,
      params: 'N=30・止蝕 8%・目標 3R・最多 12 持倉',
      gates: { quality: 60, momentum: 62 }, scale: 1.00 },
    { id: 'v2.2.1', label: '歷史運行 v2.2.1', runId: 'RUN-2026-0731-11', live: false,
      params: 'N=20・止蝕 6%・目標 3R・最多 12 持倉',
      gates: { quality: 55, momentum: 58 }, scale: 1.32 },
    { id: 'v2.1.0', label: '歷史運行 v2.1.0', runId: 'RUN-2026-0620-05', live: false,
      params: 'N=30・止蝕 8%・無目標(移動止蝕)',
      gates: { quality: 68, momentum: 71 }, scale: 0.64 },
  ];

  var VER_BY_ID = {};
  K.picks.versions.forEach(function (v) { VER_BY_ID[v.id] = v; });

  var snapCache = {};

  /**
   * 某個版本、某一日的選股快照。
   * 版本換了,分數與門檻都不同,所以漏斗同表格一齊變。
   */
  K.picks.snapshot = function (verId, dateStr) {
    var key = verId + '|' + dateStr;
    if (snapCache[key]) return snapCache[key];

    var V = VER_BY_ID[verId] || K.picks.versions[0];
    var D = null;
    PICK_DATES.forEach(function (d) { if (d.date === dateStr) D = d; });
    /* 圖上可以點任何一日,不在三個示意日期之內就即場生一組 */
    if (!D) {
      var dr = rng('funnel-' + dateStr);
      var scope = 480 + Math.floor(dr() * 40);
      var fund = Math.round(scope * between(dr, 0.11, 0.22));
      var tech = Math.round(fund * between(dr, 0.24, 0.42));
      D = { date: dateStr, scope: scope, fund: fund, tech: tech,
            held: Math.max(4, Math.min(12, Math.round(tech * between(dr, 0.34, 0.55)))) };
    }

    var rows = UNIVERSE.map(function (u) {
      var r = rng('pick-' + verId + '-' + dateStr + '-' + u.sym);
      var quality = round(between(r, 22, 96), 1);
      var momentum = round(between(r, 18, 95), 1);
      var oversold = round(between(r, 2, 88), 1);
      var passFund = quality >= V.gates.quality;
      var passTech = passFund && momentum >= V.gates.momentum;
      var isHeld = !!HELD[u.sym];
      var status = isHeld ? '持倉' : (passTech ? '入選' : (passFund ? '觀察' : '未過'));
      return {
        sym: u.sym, name: u.name, sector: u.sector,
        quality: quality, momentum: momentum, oversold: oversold,
        composite: round(quality * 0.4 + momentum * 0.45 + oversold * 0.15, 1),
        passFund: passFund, passTech: passTech, status: status,
      };
    });
    rows.sort(function (a, b) { return b.composite - a.composite; });

    var fund = Math.max(8, Math.round(D.fund * V.scale));
    var tech = Math.max(4, Math.round(D.tech * V.scale));
    var held = Math.max(3, Math.min(12, Math.round(D.held * V.scale)));

    var out = {
      version: V,
      funnel: [
        { label: '範圍', hint: '當日可交易的全部標的', count: D.scope },
        { label: '過基本面關', hint: '質素分達 ' + V.gates.quality + ' 分', count: fund },
        { label: '過技術關', hint: '再要動量分達 ' + V.gates.momentum + ' 分', count: tech },
        { label: '持倉', hint: '扣除倉位上限與風控後實際持有', count: held },
      ],
      rows: rows,
    };
    snapCache[key] = out;
    return out;
  };

  /* ============================================================
     七、總覽右欄詳情卡要用的每套策略摘要
     ============================================================ */
  var REAL_META = {
    'trend-swing': { ver: 'v2.3.0', params: 'N=30・止蝕 8%・目標 3R・最多 12 持倉', lastRun: '2026-08-12' },
    'minervini':   { ver: 'v1.8.2', params: '八項趨勢範本・止蝕 7%・最多 10 持倉', lastRun: '2026-08-11' },
    'bottleneck':  { ver: 'v0.9.1', params: '供需缺口 ≥ 2 季・止蝕 12%・最多 8 持倉', lastRun: '2026-08-06' },
    'oversold':    { ver: 'v1.4.0', params: '質素前 30%・RSI < 30・最多 15 持倉', lastRun: '2026-08-09' },
    'factor-mix':  { ver: 'v2.0.3', params: '四因子等權・月度換倉・最多 25 持倉', lastRun: '2026-08-10' },
    'sa':          { ver: 'v1.1.0', params: '評級 ≥ 4.2・跟隨延遲 2 日・最多 20 持倉', lastRun: '2026-08-08' },
    'pelosi':      { ver: 'v1.0.4', params: '申報後 5 日內入場・最多 12 持倉', lastRun: '2026-07-30' },
  };

  /* ============================================================
     八、版本沿革(git log 形態)
     ------------------------------------------------------------
     版本是這個平台的核心:每一版改了什麼、誰改的、之下跑過幾次,
     全部要指得回去。現役那一版高亮。
     ============================================================ */
  K.strategyHistory = [
    { ver: 'v2.3.0', date: '2026-08-12', by: '用戶', byKind: 'human', runs: 2, current: true,
      summary: '倉位上限由 8 個放寬到 12 個' },
    { ver: 'v2.2.1', date: '2026-07-28', by: 'agent', byKind: 'agent', runs: 2,
      summary: '止蝕由 10% 收緊到 8%' },
    { ver: 'v2.2.0', date: '2026-07-05', by: 'agent', byKind: 'agent', runs: 1,
      summary: '供求因子改用 v1.2 計法' },
    { ver: 'v2.1.0', date: '2026-06-18', by: '用戶', byKind: 'human', runs: 1,
      summary: '撤走固定目標,改為全程移動止蝕' },
    { ver: 'v2.0.0', date: '2026-05-30', by: '用戶', byKind: 'human', runs: 1,
      summary: '加入共用風控層,單日虧損上限 3%' },
    { ver: 'v1.4.0', date: '2026-04-11', by: 'agent', byKind: 'agent', runs: 3,
      summary: '突破日數由 20 日改為 30 日' },
    { ver: 'v1.2.0', date: '2026-03-09', by: 'agent', byKind: 'agent', runs: 2,
      summary: '加入成交量放大確認' },
    { ver: 'v1.0.0', date: '2026-02-02', by: '用戶', byKind: 'human', runs: 5,
      summary: '策略開帳' },
  ];

  K.factorHistory = [
    { id: 'supply', name: '供求因子', versions: [
      { ver: 'v1.3', date: '2026-08-20', current: true, summary: '改用成交金額加權' },
      { ver: 'v1.2', date: '2026-06-30', summary: '剔除停牌日' },
      { ver: 'v1.1', date: '2026-04-02', summary: '首個可用版本' },
    ] },
    { id: 'momentum', name: '動量因子', versions: [
      { ver: 'v2.0', date: '2026-05-11', current: true, summary: '改用 12-1 動量' },
      { ver: 'v1.0', date: '2026-01-20', summary: '簡單 12 個月動量' },
    ] },
    { id: 'quality', name: '質素因子', versions: [
      { ver: 'v1.1', date: '2026-03-02', current: true, summary: '自由現金流改四季滾動' },
      { ver: 'v1.0', date: '2026-01-20', summary: '首個可用版本' },
    ] },
  ];

  var DEMO_PARAM_BITS = [
    ['入選門檻 前 20%', '入選門檻 前 10%', '入選門檻 前 30%'],
    ['止蝕 6%', '止蝕 8%', '止蝕 10%', '止蝕 12%'],
    ['月度換倉', '週度換倉', '季度換倉'],
    ['最多 8 持倉', '最多 12 持倉', '最多 20 持倉'],
  ];

  K.allStrategies.forEach(function (s) {
    if (REAL_META[s.id]) {
      s.ver = REAL_META[s.id].ver;
      s.paramSummary = REAL_META[s.id].params;
      s.lastRun = REAL_META[s.id].lastRun;
    } else {
      var r = rng('meta-' + s.id);
      s.ver = 'v' + Math.floor(between(r, 0, 3)) + '.' + Math.floor(between(r, 0, 9)) +
        '.' + Math.floor(between(r, 0, 5));
      s.paramSummary = DEMO_PARAM_BITS.map(function (bits) {
        return bits[Math.floor(r() * bits.length)];
      }).join('・');
      var day = Math.floor(between(r, 1, 26));
      s.lastRun = '2026-08-' + String(day).padStart(2, '0');
    }
  });

  /* ============================================================
     九、策略類型(總覽頁的篩選維度)
     舊的「分組」只有四類、名字綁死了這七套真策略的做法;
     類型改用通用名,策略由二十套加到幾百套都不用改這張表。
     一套策略只屬一個類型。
     ============================================================ */
  K.strategyTypes = [
    { id: 'fundamental', name: '基本面選股' },
    { id: 'technical',   name: '技術趨勢' },
    { id: 'multifactor', name: '多因子' },
    { id: 'event',       name: '事件驅動' },
    { id: 'meanrev',     name: '均值回歸' },
    { id: 'follow',      name: '組合跟隨' },
    { id: 'macro',       name: '宏觀配置' },
    { id: 'options',     name: '期權策略' },
  ];

  var TYPE_OF = {
    bottleneck: 'fundamental', 'demo-01': 'fundamental', 'demo-02': 'fundamental',
    minervini: 'technical', 'trend-swing': 'technical', 'demo-04': 'technical', 'demo-05': 'technical',
    'factor-mix': 'multifactor', 'demo-03': 'multifactor', 'demo-07': 'multifactor',
    'demo-10': 'event', 'demo-11': 'event',
    oversold: 'meanrev', 'demo-06': 'meanrev',
    sa: 'follow', pelosi: 'follow', 'demo-08': 'follow', 'demo-09': 'follow',
    'demo-12': 'macro',
    'demo-13': 'options',
  };

  var TYPE_NAME = {};
  K.strategyTypes.forEach(function (t) { TYPE_NAME[t.id] = t.name; });

  K.allStrategies.forEach(function (s) {
    s.type = TYPE_OF[s.id] || 'fundamental';
    s.typeName = TYPE_NAME[s.type];

    /* 詳情卡底部「最近運行」三行要用 */
    if (s.id === 'trend-swing') {
      s.lastRunId = K.run.id;
      s.lastRunSnap = K.run.snapshot;
      s.runCount = K.trendSwing.runs.length;
    } else {
      var rr = rng('runmeta-' + s.id);
      var mm = s.lastRun.slice(5, 7), dd = s.lastRun.slice(8, 10);
      s.lastRunId = 'RUN-2026-' + mm + dd + '-' + String(Math.floor(between(rr, 1, 20))).padStart(2, '0');
      s.lastRunSnap = 'DS-' + s.lastRun + '-' + 'abc'.charAt(Math.floor(rr() * 3));
      s.runCount = Math.floor(between(rr, 1, 24));
    }
  });

  /* ============================================================
     十、持倉帶與交易日標記(運行頁左欄圖區)
     兩者都由同一批逐筆交易推出來,所以帶上的色塊、曲線上的標記、
     右欄表格那一行,講的一定是同一件事。
     ============================================================ */
  var BAND_COLORS = [
    '#4a9eff', '#26a69a', '#f0a83c', '#b07de0', '#ef5350',
    '#7fc8a9', '#e08a5d', '#6fa8dc', '#c9b458', '#8f9bb3',
  ];

  /* 淨值序列是週線,交易日多數落在兩點之間;一律對到最接近的一個序列日子,
     持倉帶同標記才會與曲線對得準(否則圖表庫會答不出座標,那一段就不見了) */
  var SNAP_DATES = K.run.series.dates;
  var SNAP_TS = SNAP_DATES.map(function (d) { return Date.parse(d); });
  function snapToSeries(d) {
    var x = Date.parse(d), best = 0, bd = Infinity;
    for (var i = 0; i < SNAP_TS.length; i++) {
      var g = Math.abs(SNAP_TS[i] - x);
      if (g < bd) { bd = g; best = i; }
    }
    return SNAP_DATES[best];
  }

  (function buildBand() {
    var trades = K.run.trades;
    var bySym = {};
    trades.forEach(function (t) {
      if (!bySym[t.sym]) bySym[t.sym] = { sym: t.sym, name: t.name, spells: [] };
      bySym[t.sym].spells.push(t);
    });

    var syms = Object.keys(bySym).sort(function (a, b) {
      var d = bySym[b].spells.length - bySym[a].spells.length;
      if (d) return d;
      return a.localeCompare(b);
    });

    var top = syms.slice(0, 10);
    var lanes = top.map(function (sym, i) {
      var g = bySym[sym];
      var lr = rng('band-' + sym);
      return {
        sym: sym,
        name: g.name,
        color: BAND_COLORS[i % BAND_COLORS.length],
        spells: g.spells.map(function (t) {
          return {
            from: snapToSeries(t.entryDate),
            to: snapToSeries(t.exitDate),
            /* 佔組合的比重:原型用種子亂數,但同一筆交易每次都是同一個數 */
            weight: round(between(lr, 4, 14), 1),
            tradeId: t.id,
          };
        }).sort(function (a, b) { return a.from < b.from ? -1 : 1; }),
      };
    });

    K.holdingsBand = {
      from: K.run.series.dates[0],
      to: K.run.series.dates[K.run.series.dates.length - 1],
      maxWeight: 14,
      lanes: lanes,
      shownOf: syms.length,
      coveredTrades: lanes.reduce(function (a, l) { return a + l.spells.length; }, 0),
    };
  })();

  /* 把交易日對到淨值序列最接近的一個日子,標記才落得準 */
  (function buildMarks() {
    var snap = snapToSeries;
    var byDate = {};
    K.run.trades.forEach(function (t) {
      var a = snap(t.entryDate), b = snap(t.exitDate);
      (byDate[a] = byDate[a] || { date: a, buys: [], sells: [] }).buys.push(t);
      (byDate[b] = byDate[b] || { date: b, buys: [], sells: [] }).sells.push(t);
    });

    K.tradeMarks = Object.keys(byDate).sort().map(function (d) {
      var m = byDate[d];
      var nb = m.buys.length, ns = m.sells.length;
      m.side = nb && ns ? 'both' : (nb ? 'buy' : 'sell');
      m.label = (nb ? '買' + nb : '') + (nb && ns ? '／' : '') + (ns ? '沽' + ns : '');
      return m;
    });
    K.tradeMarkByDate = byDate;
  })();

  /* ============================================================
     十一、掃描:四個參數任揀兩個做軸
     ------------------------------------------------------------
     掃描一共四個參數,一幅圖只畫得出兩個。以前寫死「突破日數 × 止蝕」,
     現在任揀兩個做軸,餘下兩個變成切片。預設那一幅(突破日數 × 止蝕、
     風險比例 1%、均線 150 日)照舊沿用第一版原數據,畫面不變。
     ============================================================ */
  K.sweepParams = [
    { id: 'n', label: '突破日數 N', short: 'N',
      hint: '突破多少日的高位才當作訊號',
      values: K.sweep.rows, def: 30,
      fmt: function (v) { return String(v); } },
    { id: 'stop', label: '止蝕幅度', short: '止蝕',
      hint: '離進場價多遠就認輸離場',
      values: K.sweep.cols, def: 8,
      fmt: function (v) { return v + '%'; } },
    { id: 'risk', label: '風險比例', short: '風險',
      hint: '每筆交易願意輸掉的組合百分比',
      values: [0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0], def: 1.0,
      fmt: function (v) { return v + '%'; } },
    { id: 'ma', label: '均線長度', short: '均線',
      hint: '判斷大市方向那條均線的日數',
      values: [20, 50, 80, 100, 150, 200, 250, 300], def: 150,
      fmt: function (v) { return v + ' 日'; } },
  ];

  K.sweepParamById = {};
  K.sweepParams.forEach(function (p) { K.sweepParamById[p.id] = p; });

  var gridCache = {};

  /* 一格的附帶指標由年化推出來,免得四個數字各自亂走、對不上 */
  function cellFrom(vals, cagr, r) {
    return {
      vals: vals,
      n: vals.n, s: vals.stop,
      cagr: cagr,
      mdd: round(clamp(-14 - (30 - cagr) * 0.75 - between(r, 0, 9), -58, -12), 1),
      sortino: round(clamp(0.35 + cagr / 16, 0.2, 2.6), 2),
      trades: Math.round(between(r, 90, 260)),
      spike: false,
    };
  }

  /* 找平原(鄰域平均最高那一格)同孤峰(自己高出鄰域最多那一格) */
  function judge(grid) {
    var R = grid.length, C = grid[0].length;
    var lo = R > 2 ? 1 : 0, hiR = R > 2 ? R - 1 : R, hiC = C > 2 ? C - 1 : C;
    var bestMean = -1e9, pc = [0, 0];
    for (var ri = lo; ri < hiR; ri++) {
      for (var ci = (C > 2 ? 1 : 0); ci < hiC; ci++) {
        var m = neighbourMean(grid, ri, ci);
        if (m > bestMean) { bestMean = m; pc = [ri, ci]; }
      }
    }
    var set = {}, centre = grid[pc[0]][pc[1]].cagr;
    for (ri = 0; ri < R; ri++) {
      for (ci = 0; ci < C; ci++) {
        if (Math.abs(ri - pc[0]) <= 1 && Math.abs(ci - pc[1]) <= 1 &&
            grid[ri][ci].cagr >= centre - 3.5) set[ri + ',' + ci] = true;
      }
    }
    var bestGap = -1e9, sp = null;
    for (ri = 0; ri < R; ri++) {
      for (ci = 0; ci < C; ci++) {
        if (set[ri + ',' + ci]) continue;
        var gap = grid[ri][ci].cagr - neighbourMean(grid, ri, ci);
        if (gap > bestGap) { bestGap = gap; sp = [ri, ci]; }
      }
    }
    if (sp) grid[sp[0]][sp[1]].spike = true;
    return { plateauSet: set, plateauCenter: pc, spikePos: sp };
  }

  function isBaseAsk(yId, xId, fixed) {
    return ((yId === 'n' && xId === 'stop') || (yId === 'stop' && xId === 'n')) &&
      fixed.risk === 1.0 && fixed.ma === 150;
  }

  /**
   * 揀兩個參數做軸,餘下兩個定住,砌出一幅熱力圖。
   * yId / xId:縱軸、橫軸的參數 id;fixed:餘下兩個參數的值。
   */
  K.sweepGrid = function (yId, xId, fixed) {
    var key = 'g|' + yId + '|' + xId + '|' +
      K.sweepParams.map(function (p) { return p.id + '=' + fixed[p.id]; }).join(',');
    if (gridCache[key]) return gridCache[key];

    var yp = K.sweepParamById[yId], xp = K.sweepParamById[xId];
    var rowVals = yp.values, colVals = xp.values;
    var R = rowVals.length, C = colVals.length;
    var out, grid = [], ri, ci;

    if (isBaseAsk(yId, xId, fixed)) {
      /* 預設那一幅照舊用第一版原數據,一個數字都不改 */
      var flip = (yId === 'stop');
      for (ri = 0; ri < R; ri++) {
        var row = [];
        for (ci = 0; ci < C; ci++) {
          var src = flip ? K.sweep.grid[ci][ri] : K.sweep.grid[ri][ci];
          row.push({
            vals: { n: src.n, stop: src.s, risk: 1.0, ma: 150 },
            n: src.n, s: src.s,
            cagr: src.cagr, mdd: src.mdd, sortino: src.sortino,
            trades: src.trades, spike: src.spike,
          });
        }
        grid.push(row);
      }
      var pset = {}, pcen = K.sweep.plateauCenter, spos = null;
      K.sweep.plateauCells.forEach(function (p) {
        pset[(flip ? p[1] + ',' + p[0] : p[0] + ',' + p[1])] = true;
      });
      if (flip) pcen = [K.sweep.plateauCenter[1], K.sweep.plateauCenter[0]];
      /* 孤峰用原圖的座標找,再按需要轉置,免得掃描次序不同就答出兩個位置 */
      K.sweep.grid.forEach(function (rw, a) {
        rw.forEach(function (c, b) { if (c.spike && !spos) spos = flip ? [b, a] : [a, b]; });
      });
      out = { grid: grid, rowVals: rowVals, colVals: colVals,
              plateauSet: pset, plateauCenter: pcen, spikePos: spos, isBase: true };
      gridCache[key] = out;
      return out;
    }

    /* 其餘組合:同一條種子生同一幅圖,揀來揀去都對得上 */
    var r = rng(key);
    var r0 = between(r, R * 0.25, R * 0.75);
    var c0 = between(r, C * 0.25, C * 0.75);
    var amp = between(r, 8, 13);
    var base = between(r, 6, 12);
    var spreadR = Math.max(1.6, R / 3.2), spreadC = Math.max(1.6, C / 3.2);

    for (ri = 0; ri < R; ri++) {
      var rw2 = [];
      for (ci = 0; ci < C; ci++) {
        var cr = rng(key + '|' + ri + '|' + ci);
        var bump = amp * Math.exp(-(
          Math.pow(ri - r0, 2) / (2 * spreadR * spreadR) +
          Math.pow(ci - c0, 2) / (2 * spreadC * spreadC)));
        var noise = (cr() - 0.5) * 2.6;
        var vals = { n: fixed.n, stop: fixed.stop, risk: fixed.risk, ma: fixed.ma };
        vals[yId] = rowVals[ri];
        vals[xId] = colVals[ci];
        rw2.push(cellFrom(vals, round(clamp(base + bump + noise, 1.5, 34), 1), cr));
      }
      grid.push(rw2);
    }

    var j = judge(grid);

    /* 種一個孤峰在離平原遠的地方,好等「最高分不等於最應該選」這件事每幅圖都睇得到 */
    var sr = (j.plateauCenter[0] + Math.floor(R / 2)) % R;
    var sc = (j.plateauCenter[1] + Math.floor(C / 2)) % C;
    if (j.plateauSet[sr + ',' + sc]) sc = (sc + 2) % C;
    var sCell = grid[sr][sc];
    sCell.cagr = round(neighbourMean(grid, sr, sc) + between(r, 6.5, 9.5), 1);
    sCell.sortino = round(clamp(0.35 + sCell.cagr / 16, 0.2, 2.6), 2);
    var j2 = judge(grid);
    grid.forEach(function (rw3) { rw3.forEach(function (c) { c.spike = false; }); });
    grid[sr][sc].spike = true;

    out = { grid: grid, rowVals: rowVals, colVals: colVals,
            plateauSet: j2.plateauSet, plateauCenter: j2.plateauCenter,
            spikePos: [sr, sc], isBase: false };
    gridCache[key] = out;
    return out;
  };

  /* ============================================================
     十、每次運行自己的一條線(策略頁「檢視運行」用)
     ------------------------------------------------------------
     之前只有現役那一次運行有日序列與逐筆交易;策略頁要做到
     「換一次運行,全頁跟著換」,所以每次運行都要有自己的序列、
     自己的交易、自己的交易日標記。現役那次沿用原有數據,
     其餘五次按各自的年化與最大回撤生成,數字對得回歷次運行表。
     ============================================================ */

  /* 缺了 v2.0.0 的選股版本,補一個,否則揀到最舊那次運行會跌回現役設定 */
  var V200 = {
    id: 'v2.0.0', label: '歷史運行 v2.0.0', runId: 'RUN-2026-0602-01', live: false,
    params: 'N=25・止蝕 7%・目標 3R・無風控層',
    gates: { quality: 72, momentum: 74 }, scale: 0.46,
  };
  K.picks.versions.push(V200);
  VER_BY_ID[V200.id] = V200;

  function gauss(r) {
    var u = Math.max(1e-9, r()), v = r();
    return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v);
  }
  var runViewCache = {};

  /**
   * 一次運行的完整檢視資料:日序列(策略、QQQ、SPY)、逐筆交易、交易日標記。
   * 序列一律以期間第一日為基期 100。
   */
  K.runView = function (runId) {
    if (runViewCache[runId]) return runViewCache[runId];

    var run = null;
    K.trendSwing.runs.forEach(function (x) { if (x.id === runId) run = x; });
    if (!run) run = K.trendSwing.runs[0];

    /* 由全域週序列切出這次運行的期間,基準線與策略線用同一段日期 */
    var i0 = 0, i1 = K.weeklyDates.length - 1;
    while (i0 < i1 && K.weeklyDates[i0] < run.from) i0++;
    while (i1 > i0 && K.weeklyDates[i1] > run.to) i1--;
    var dates = K.weeklyDates.slice(i0, i1 + 1);
    var n = dates.length;

    function slice100(arr) {
      var b = arr[i0];
      return arr.slice(i0, i1 + 1).map(function (v) { return round(v / b * 100, 3); });
    }
    var qqqLine = slice100(K.benchmarks.QQQ.equity);
    var spyLine = slice100(K.benchmarks.SPY.equity);

    var stratLine;
    var S = K.strategies.filter(function (x) { return x.id === 'trend-swing'; })[0];
    if (run.current) {
      /* 現役那次沿用原有的策略曲線,預設畫面同上一版一模一樣 */
      stratLine = slice100(S.equity);
    } else {
      /* 其餘:先造一條零漂移隨機遊走,再把漂移調到目標年化,
         最後二分搜尋波幅倍數,令最大回撤落在該次運行報稱的數字上 */
      var r = rng('runview-' + run.id);
      var years = (n - 1) / 52;
      var eps = [];
      for (var i = 0; i < n; i++) eps.push(gauss(r));
      var mean = eps.reduce(function (a, b) { return a + b; }, 0) / n;
      eps = eps.map(function (e) { return e - mean; });

      var drift = Math.log(1 + run.cagr / 100) / 52;
      function build(scale) {
        var out = [100];
        for (var j = 1; j < n; j++) out.push(out[j - 1] * Math.exp(drift + eps[j] * scale));
        var last = out[out.length - 1];
        /* 漂移會被波幅拖歪,收尾拉直,令年化剛好等於報稱值 */
        var target = 100 * Math.pow(1 + run.cagr / 100, years);
        var fix = Math.pow(target / last, 1 / Math.max(1, n - 1));
        var fixed = [100];
        for (var k = 1; k < n; k++) fixed.push(fixed[k - 1] * (out[k] / out[k - 1]) * fix);
        return fixed;
      }
      var lo = 0.004, hi = 0.09, mid = 0.02, line = build(mid);
      for (var pass = 0; pass < 26; pass++) {
        mid = (lo + hi) / 2;
        line = build(mid);
        if (maxDrawdown(line) < run.mdd) hi = mid; else lo = mid;
      }
      stratLine = line.map(function (v) { return round(v, 3); });
    }

    /* ---- 逐筆交易 ---- */
    var trades;
    if (run.current) {
      trades = K.run.trades;
    } else {
      var tr = rng('runtrades-' + run.id);
      var want = Math.max(24, Math.round((run.trades || 180) * 0.28));
      /* 贏輸用配額而不是逐筆擲骰,抽樣的勝率才會等於歷次運行表上報稱那個 */
      var flags = [];
      var winCount = Math.round(want * run.win / 100);
      for (var q = 0; q < want; q++) flags.push(q < winCount);
      for (var q2 = flags.length - 1; q2 > 0; q2--) {
        var j2 = Math.floor(tr() * (q2 + 1));
        var tmp = flags[q2]; flags[q2] = flags[j2]; flags[j2] = tmp;
      }

      trades = [];
      for (var t = 0; t < want; t++) {
        var u = UNIVERSE[Math.floor(tr() * UNIVERSE.length)];
        var ei = Math.floor(between(tr, 0, n - 4));
        var hold = Math.round(between(tr, 12, 96));
        var xi = Math.min(n - 1, ei + Math.max(2, Math.round(hold / 7)));
        var wins = flags[t];
        var retPct = round(wins ? between(tr, 2.5, 34) : between(tr, -11, -1.2), 1);
        var entryPx = round(between(tr, 22, 260), 2);
        var shares = Math.round(between(tr, 60, 620));
        trades.push({
          id: run.id.slice(-5) + '-T' + String(t + 1).padStart(3, '0'),
          sym: u.sym, name: u.name, sector: u.sector, side: '做多',
          entryDate: dates[ei], entryPx: entryPx,
          exitDate: dates[xi], exitPx: round(entryPx * (1 + retPct / 100), 2),
          shares: shares, holdDays: hold,
          pnl: Math.round(entryPx * shares * retPct / 100),
          retPct: retPct,
          reason: retPct <= 0 ? (retPct < -7 ? '觸及止蝕' : '月度熔斷')
                              : (retPct > 20 ? '達目標 3R' : '移動止蝕帶出'),
        });
      }
      trades.sort(function (a, b) { return a.entryDate < b.entryDate ? -1 : 1; });
    }

    /* ---- 交易日標記:同一日的買賣併成一格 ---- */
    var byDate = {};
    function put(d, kind, t) {
      if (!byDate[d]) byDate[d] = { date: d, buys: [], sells: [] };
      byDate[d][kind].push(t);
    }
    trades.forEach(function (t) { put(t.entryDate, 'buys', t); put(t.exitDate, 'sells', t); });
    var marks = Object.keys(byDate).sort().map(function (d) {
      var m = byDate[d];
      m.side = m.buys.length && m.sells.length ? 'both' : (m.buys.length ? 'buy' : 'sell');
      m.label = (m.buys.length ? '買' + m.buys.length : '') +
                (m.buys.length && m.sells.length ? '・' : '') +
                (m.sells.length ? '沽' + m.sells.length : '');
      return m;
    });

    var view = {
      run: run, dates: dates, strategy: stratLine, qqq: qqqLine, spy: spyLine,
      trades: trades, marks: marks, markByDate: byDate,
    };
    runViewCache[runId] = view;
    return view;
  };

  /**
   * 檢視視窗:由 fromISO 起重設基準為 100,並按這一段重算指標。
   * 這不是重跑 —— 同一次運行、同一條線,只是換一個起點看。
   */
  K.windowStats = function (view, fromISO) {
    var i0 = 0;
    while (i0 < view.dates.length - 3 && view.dates[i0] < fromISO) i0++;

    function reb(arr) {
      var b = arr[i0];
      return arr.slice(i0).map(function (v) { return round(v / b * 100, 3); });
    }
    var dates = view.dates.slice(i0);
    var st = reb(view.strategy), qq = reb(view.qqq), sp = reb(view.spy);
    var years = Math.max(0.12, (dates.length - 1) / 52);

    function cum(a) { return round(a[a.length - 1] - 100, 1); }
    function cagr(a) { return round((Math.pow(a[a.length - 1] / 100, 1 / years) - 1) * 100, 1); }

    /* 週報酬:波幅與 Sortino 都由這一段自己算 */
    var rets = [];
    for (var i = 1; i < st.length; i++) rets.push(st[i] / st[i - 1] - 1);
    var mu = rets.reduce(function (a, b) { return a + b; }, 0) / Math.max(1, rets.length);
    var varSum = 0, downSum = 0, downN = 0;
    rets.forEach(function (x) {
      varSum += (x - mu) * (x - mu);
      if (x < 0) { downSum += x * x; downN++; }
    });
    var vol = round(Math.sqrt(varSum / Math.max(1, rets.length)) * Math.sqrt(52) * 100, 1);
    var dvol = Math.sqrt(downSum / Math.max(1, downN)) * Math.sqrt(52);
    var sortino = round(dvol > 0 ? (Math.pow(st[st.length - 1] / 100, 1 / years) - 1) / dvol : 0, 2);

    /* 交易:出場日落在視窗之內的才算 */
    var from = dates[0];
    var trades = view.trades.filter(function (t) { return t.exitDate >= from; });
    var wins = trades.filter(function (t) { return t.retPct > 0; });
    var losses = trades.filter(function (t) { return t.retPct <= 0; });
    function avg(a, f) { return a.length ? a.reduce(function (s, x) { return s + f(x); }, 0) / a.length : 0; }
    var avgWin = avg(wins, function (t) { return t.retPct; });
    var avgLoss = Math.abs(avg(losses, function (t) { return t.retPct; }));

    return {
      from: from, to: dates[dates.length - 1], years: round(years, 1),
      dates: dates, strategy: st, qqq: qq, spy: sp,
      trades: trades,
      marks: view.marks.filter(function (m) { return m.date >= from; }),
      isFull: i0 === 0,
      metrics: {
        cumReturn: cum(st), cagr: cagr(st),
        maxDD: round(maxDrawdown(st), 1), vol: vol, sortino: sortino,
        winRate: trades.length ? Math.round(wins.length / trades.length * 100) : 0,
        plRatio: avgLoss > 0 ? round(avgWin / avgLoss, 1) : 0,
        trades: trades.length,
        qqqCum: cum(qq), qqqCagr: cagr(qq), qqqMaxDD: round(maxDrawdown(qq), 1),
        spyCum: cum(sp),
      },
    };
  };

  /* ============================================================
     十一、因子版本改為「具體定義」
     ------------------------------------------------------------
     「動量」「質素」都不是單一定義 —— 同一族之下可以有幾個算法,
     各自有自己的版本線。命名一律「族名・具體定義」,
     策略現時綁哪一個,寫明「現用」。
     ============================================================ */
  K.factorHistory = [
    { id: 'mom-12-1', family: '動量', def: '12-1 月', en: 'Momentum · 12-1M', used: true,
      versions: [
        { ver: 'v1.2', date: '2026-05-11', current: true, summary: '剔除最近一個月的反轉' },
        { ver: 'v1.1', date: '2026-02-18', summary: '改用對數報酬' },
        { ver: 'v1.0', date: '2026-01-20', summary: '首個可用版本' },
      ] },
    { id: 'mom-6', family: '動量', def: '6 月', en: 'Momentum · 6M', used: false,
      versions: [
        { ver: 'v1.0', date: '2026-01-20', current: true, summary: '首個可用版本,未有策略採用' },
      ] },
    { id: 'qual-gpa-roe', family: '質素', def: '毛利率 ROE 合成', en: 'Quality · GP/A + ROE', used: true,
      versions: [
        { ver: 'v2.0', date: '2026-03-02', current: true, summary: '自由現金流改四季滾動' },
        { ver: 'v1.0', date: '2026-01-20', summary: '首個可用版本' },
      ] },
    { id: 'sup-turnover', family: '供求', def: '成交金額加權', en: 'Supply-Demand · Turnover-weighted', used: true,
      versions: [
        { ver: 'v1.3', date: '2026-08-20', current: true, summary: '取代成交股數加權' },
        { ver: 'v1.2', date: '2026-06-30', summary: '剔除停牌日' },
        { ver: 'v1.1', date: '2026-04-02', summary: '首個可用版本' },
      ] },
  ];

})(window);
