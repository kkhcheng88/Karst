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

})(window);
