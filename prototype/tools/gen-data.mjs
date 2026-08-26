/**
 * Karst 原型假數據產生器
 * ------------------------------------------------------------
 * 產出 ../assets/data.js。全部數據為合成假數據,種子固定,重跑結果一致。
 * 刻意做出真實市場形狀(2020 熔斷、2022 熊市、2023-24 復甦),
 * 令原型可以用來判斷版面與資訊層次,而不是判斷數據對錯。
 *
 * 個股與持倉一律用虛構代號,避免與真實標的混淆。
 * 基準 QQQ / SPY 沿用真實名稱(票面要求),但價格序列同樣是假的。
 *
 * 用法: node tools/gen-data.mjs
 */

import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const OUT = path.join(__dirname, '..', 'assets', 'data.js');

/* ---------- 亂數 ---------- */
function mulberry32(a) {
  return function () {
    a |= 0; a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
let rnd = mulberry32(20260826);
let spare = null;
function gauss() {
  if (spare !== null) { const s = spare; spare = null; return s; }
  let u = 0, v = 0, s = 0;
  do { u = rnd() * 2 - 1; v = rnd() * 2 - 1; s = u * u + v * v; } while (s === 0 || s >= 1);
  const m = Math.sqrt((-2 * Math.log(s)) / s);
  spare = v * m;
  return u * m;
}
const r2 = (x) => Math.round(x * 100) / 100;
const r1 = (x) => Math.round(x * 10) / 10;
const r3 = (x) => Math.round(x * 1000) / 1000;

/* ---------- 日期 ---------- */
const DAY = 86400000;
const iso = (d) => new Date(d).toISOString().slice(0, 10);
const utc = (s) => Date.parse(s + 'T00:00:00Z');

function weeklyDates(startISO, endISO) {
  const out = [];
  let t = utc(startISO);
  const end = utc(endISO);
  while (t <= end) { out.push(iso(t)); t += 7 * DAY; }
  return out;
}
function tradingDays(startISO, count) {
  const out = [];
  let t = utc(startISO);
  while (out.length < count) {
    const dow = new Date(t).getUTCDay();
    if (dow !== 0 && dow !== 6) out.push(iso(t));
    t += DAY;
  }
  return out;
}
// 由結束日倒數 count 個交易日,令最後一根蠟燭啱啱好落在資料截止日
function tradingDaysEndingAt(endISO, count) {
  const out = [];
  let t = utc(endISO);
  while (out.length < count) {
    const dow = new Date(t).getUTCDay();
    if (dow !== 0 && dow !== 6) out.unshift(iso(t));
    t -= DAY;
  }
  return out;
}

/* ---------- 市場政體(令假數據有真實形狀) ---------- */
// 回傳該週的 [年化漂移, 年化波動] —— 市場(QQQ 型)的基準走勢
function regime(dateISO) {
  const d = dateISO;
  if (d < '2019-12-31') return [0.40, 0.16];          // 2019 強勢年
  if (d < '2020-02-19') return [0.22, 0.14];          // 2020 年初
  if (d < '2020-03-24') return [-3.40, 0.55];         // 熔斷:五週急插
  if (d < '2020-12-31') return [0.78, 0.26];          // V 型反彈
  if (d < '2021-12-31') return [0.28, 0.14];          // 2021 順風
  if (d < '2022-06-16') return [-0.62, 0.26];         // 2022 上半年殺估值
  if (d < '2022-10-13') return [-0.16, 0.28];         // 2022 下半年尋底
  if (d < '2022-12-31') return [0.30, 0.24];
  if (d < '2023-12-31') return [0.46, 0.16];          // 2023 復甦
  if (d < '2024-12-31') return [0.28, 0.14];          // 2024 續升
  if (d < '2025-04-07') return [-0.42, 0.24];         // 2025 春季回調
  if (d < '2025-12-31') return [0.26, 0.16];
  return [0.22, 0.15];                                 // 2026 至今
}
// 政體分類,供「趨勢系統轉現金」用
function regimeKind(dateISO) {
  const [mu] = regime(dateISO);
  if (mu < -0.15) return 'bear';
  if (mu > 0.30) return 'strong';
  return 'normal';
}

const WK = weeklyDates('2019-01-07', '2026-08-17');
const N = WK.length;

// 市場基準週報酬
const mktRet = [];
for (let i = 0; i < N; i++) {
  const [mu, sig] = regime(WK[i]);
  mktRet.push(mu / 52 + (sig / Math.sqrt(52)) * gauss());
}

/**
 * 由市場報酬合成一條策略曲線。
 * defensive: 熊市自動降低曝險(趨勢系統轉現金的行為)
 * crisisBeta: 危機時的額外曝險倍數(錯殺策略跌得更兇、反彈更強)
 */
function synth({ beta, alpha, idio, defensive = 0, crisisAlpha = 0 }) {
  const eq = [100];
  const rets = [];
  for (let i = 0; i < N; i++) {
    const kind = regimeKind(WK[i]);
    let b = beta;
    if (defensive && kind === 'bear') b = beta * (1 - defensive);
    if (crisisAlpha && kind === 'bear') b = beta * (1 + crisisAlpha);
    let a = alpha / 52;
    if (crisisAlpha && kind === 'strong') a = (alpha + 0.10) / 52;
    const r = b * mktRet[i] + a + (idio / Math.sqrt(52)) * gauss();
    rets.push(r);
    eq.push(eq[eq.length - 1] * (1 + r));
  }
  eq.shift();
  return { eq: eq.map(r2), rets };
}

/* ---------- 指標 ---------- */
function maxDrawdown(eq) {
  let peak = eq[0], mdd = 0;
  for (const v of eq) { if (v > peak) peak = v; const dd = v / peak - 1; if (dd < mdd) mdd = dd; }
  return mdd * 100;
}
function cagr(eq, years) { return (Math.pow(eq[eq.length - 1] / eq[0], 1 / years) - 1) * 100; }
function annVol(rets) {
  const m = rets.reduce((a, b) => a + b, 0) / rets.length;
  const v = rets.reduce((a, b) => a + (b - m) ** 2, 0) / (rets.length - 1);
  return Math.sqrt(v * 52) * 100;
}
function sortino(rets, mar = 0) {
  const m = rets.reduce((a, b) => a + b, 0) / rets.length;
  const down = rets.filter((r) => r < mar).map((r) => (r - mar) ** 2);
  const dd = Math.sqrt(down.reduce((a, b) => a + b, 0) / rets.length) * Math.sqrt(52);
  return ((m * 52 - mar) / dd);
}
const YEARS = (utc(WK[N - 1]) - utc(WK[0])) / (365.25 * DAY);

/* ---------- 七套策略 + 兩個基準 ---------- */
const SPEC = [
  { id: 'bottleneck', name: '樽頸', en: 'Bottleneck', kind: '策略',
    tagline: '供需故事驅動,非結構化因子為主',
    p: { beta: 1.05, alpha: 0.055, idio: 0.135 }, winRate: 44, pl: 2.9, trades: 168 },
  { id: 'factor-mix', name: '因子混合', en: 'Factor Mix', kind: '策略',
    tagline: '質素/價值/動能/低波四類敞口混合',
    p: { beta: 0.76, alpha: 0.014, idio: 0.038 }, winRate: 58, pl: 1.4, trades: 92 },
  { id: 'minervini', name: 'Minervini', en: 'Minervini', kind: '策略',
    tagline: 'VCP 型態 + 趨勢範本,熊市轉現金',
    p: { beta: 1.00, alpha: 0.030, idio: 0.125, defensive: 0.50 }, winRate: 41, pl: 3.2, trades: 214 },
  { id: 'trend-swing', name: '趨勢波段', en: 'Trend Swing', kind: '策略',
    tagline: '突破 N 日新高,純風險回報驅動',
    p: { beta: 0.92, alpha: 0.028, idio: 0.110, defensive: 0.58 }, winRate: 46, pl: 2.4, trades: 187 },
  { id: 'oversold', name: '錯殺', en: 'Oversold Quality', kind: '策略',
    tagline: '基本面良好但被超賣,不確定性落地後入場',
    p: { beta: 0.96, alpha: 0.026, idio: 0.115, crisisAlpha: 0.26 }, winRate: 61, pl: 1.6, trades: 121 },
  { id: 'sa', name: 'SA 跟隨', en: 'SA Follow', kind: '跟隨組合',
    tagline: '跟隨 SA 公開組合,月度換倉',
    p: { beta: 1.08, alpha: 0.044, idio: 0.120 }, winRate: 52, pl: 2.0, trades: 76 },
  { id: 'pelosi', name: 'Pelosi 跟隨', en: 'Pelosi Follow', kind: '跟隨組合',
    tagline: '由申報持倉倒推概念,申報前出訊號',
    p: { beta: 1.02, alpha: 0.034, idio: 0.085 }, winRate: 55, pl: 1.8, trades: 64 },
];

const BENCH = [
  { id: 'QQQ', name: 'QQQ', en: 'Invesco QQQ', p: { beta: 1.0, alpha: 0.0, idio: 0.022 } },
  { id: 'SPY', name: 'SPY', en: 'SPDR S&P 500', p: { beta: 0.80, alpha: -0.004, idio: 0.030 } },
];

const benchmarks = {};
for (const b of BENCH) {
  const s = synth(b.p);
  benchmarks[b.id] = {
    id: b.id, name: b.name, en: b.en, equity: s.eq,
    metrics: {
      cumReturn: r1(s.eq[N - 1] - 100),
      cagr: r1(cagr(s.eq, YEARS)),
      maxDD: r1(maxDrawdown(s.eq)),
      vol: r1(annVol(s.rets)),
      sortino: r2(sortino(s.rets)),
    },
  };
}

const strategies = SPEC.map((sp) => {
  const s = synth(sp.p);
  return {
    id: sp.id, name: sp.name, en: sp.en, kind: sp.kind, tagline: sp.tagline,
    equity: s.eq,
    metrics: {
      cumReturn: r1(s.eq[N - 1] - 100),
      cagr: r1(cagr(s.eq, YEARS)),
      maxDD: r1(maxDrawdown(s.eq)),
      vol: r1(annVol(s.rets)),
      sortino: r2(sortino(s.rets)),
      winRate: sp.winRate,
      plRatio: sp.pl,
      trades: sp.trades,
    },
  };
});

/* ---------- 虛構標的宇宙 ---------- */
const UNIVERSE = [
  ['NVLS', '諾瓦半導體', '半導體'], ['ARTC', '方舟科技', '軟件'],
  ['HLIO', '赫利奧能源', '再生能源'], ['CDRA', '雪松醫療', '醫療器材'],
  ['MRDN', '子午線物流', '運輸'], ['VTKS', '維特智造', '工業自動化'],
  ['QNTA', '量塔數據', '雲端服務'], ['BLFN', '藍鰭海事', '海運'],
  ['STRA', '層雲材料', '特用化工'], ['OKRA', '橡域農業', '農業科技'],
  ['PLNX', '普蘭尼克斯', '網絡安全'], ['TSVA', '特斯瓦電控', '電力設備'],
  ['GRVN', '格雷芬金融', '金融科技'], ['KYRO', '凱羅生技', '生物製藥'],
  ['ZEPH', '西風航太', '航太國防'], ['NMBS', '紐姆巴斯', '消費電子'],
  ['OKLA', '奧克拉建材', '建築材料'], ['FTHM', '深測海洋', '海洋工程'],
  ['LUMD', '流明顯示', '顯示面板'], ['AXNT', '軸心工具', '精密機械'],
  ['RVNA', '瑞文娜零售', '零售'], ['CYPR', '賽普瑞斯', '資料中心'],
  ['DLTA', '德爾塔醫藥', '製藥'], ['WNDR', '溫德旅遊', '旅遊'],
];

/* ---------- 趨勢波段:歷次回測運行 ---------- */
const RUN_ROWS = [
  { id: 'RUN-2026-0812-07', ver: 'v2.3.0', params: 'N=30 · 止蝕 8% · 目標 3R · 最多 12 持倉',
    from: '2019-01-02', to: '2026-06-30', snap: 'DS-2026-06-30-b', at: '2026-08-12 14:22',
    cagr: 21.4, mdd: -19.8, sortino: 1.62, trades: 187, win: 46, current: true },
  { id: 'RUN-2026-0805-03', ver: 'v2.3.0', params: 'N=30 · 止蝕 8% · 目標 3R · 最多 8 持倉',
    from: '2019-01-02', to: '2026-06-30', snap: 'DS-2026-06-30-b', at: '2026-08-05 09:41',
    cagr: 19.8, mdd: -22.4, sortino: 1.41, trades: 164, win: 45 },
  { id: 'RUN-2026-0731-11', ver: 'v2.2.1', params: 'N=20 · 止蝕 6% · 目標 3R · 最多 12 持倉',
    from: '2019-01-02', to: '2026-06-30', snap: 'DS-2026-06-30-a', at: '2026-07-31 18:05',
    cagr: 16.2, mdd: -24.9, sortino: 1.12, trades: 268, win: 41 },
  { id: 'RUN-2026-0714-02', ver: 'v2.2.1', params: 'N=40 · 止蝕 10% · 目標 2.5R · 最多 12 持倉',
    from: '2019-01-02', to: '2026-03-31', snap: 'DS-2026-03-31-a', at: '2026-07-14 11:30',
    cagr: 17.9, mdd: -21.1, sortino: 1.28, trades: 142, win: 48 },
  { id: 'RUN-2026-0620-05', ver: 'v2.1.0', params: 'N=30 · 止蝕 8% · 無目標(移動止蝕)',
    from: '2019-01-02', to: '2026-03-31', snap: 'DS-2026-03-31-a', at: '2026-06-20 16:52',
    cagr: 15.1, mdd: -27.6, sortino: 0.98, trades: 176, win: 39 },
  { id: 'RUN-2026-0602-01', ver: 'v2.0.0', params: 'N=25 · 止蝕 7% · 目標 3R · 無風控層',
    from: '2019-01-02', to: '2025-12-31', snap: 'DS-2025-12-31-c', at: '2026-06-02 10:14',
    cagr: 12.6, mdd: -33.2, sortino: 0.74, trades: 203, win: 38 },
];

/* ---------- 趨勢波段:紙上帳 ---------- */
const paperPicks = [0, 2, 4, 6, 9, 11, 15, 21];
const paperPositions = paperPicks.map((i, k) => {
  const [sym, nm, sec] = UNIVERSE[i];
  const cost = r2(40 + rnd() * 180);
  const gain = (rnd() - 0.34) * 0.34;
  const last = r2(cost * (1 + gain));
  const weight = r1(6 + rnd() * 7);
  const stop = r2(cost * 0.92);
  return {
    sym, name: nm, sector: sec, weight,
    entryDate: iso(utc('2026-08-21') - Math.floor(8 + rnd() * 120) * DAY),
    cost, last,
    pnlPct: r1(gain * 100),
    stopPrice: stop,
    stopDist: r1((last / stop - 1) * 100),
  };
}).sort((a, b) => b.weight - a.weight);

const paperInvested = paperPositions.reduce((a, p) => a + p.weight, 0);
const paperStart = 1000000;
const paperWeeks = weeklyDates('2026-02-02', '2026-08-17');
const paperEq = [];
{
  let v = 100;
  for (let i = 0; i < paperWeeks.length; i++) {
    v *= 1 + (0.19 / 52 + (0.14 / Math.sqrt(52)) * gauss());
    paperEq.push(r2(v));
  }
}
const paperBench = [];
{
  let v = 100;
  for (let i = 0; i < paperWeeks.length; i++) {
    v *= 1 + (0.13 / 52 + (0.16 / Math.sqrt(52)) * gauss());
    paperBench.push(r2(v));
  }
}

/* ---------- 運行詳情:逐筆交易 ---------- */
const EXIT_REASONS = ['觸及目標 3R', '移動止蝕', '初始止蝕', '訊號消失', '月度熔斷', '換倉汰弱'];
// 全體 187 筆,畫面只展示其中一段;先鋪一個剛好 46% 勝率的勝負序列再打亂,
// 令抽樣的勝率與頁頂公佈的整體勝率對得上。
const SAMPLE_N = 52;
const winFlags = Array.from({ length: SAMPLE_N }, (_, i) => i < 24);
for (let i = winFlags.length - 1; i > 0; i--) {
  const j = Math.floor(rnd() * (i + 1));
  [winFlags[i], winFlags[j]] = [winFlags[j], winFlags[i]];
}

const trades = [];
{
  let t = utc('2019-02-11');
  const end = utc('2026-06-15');
  let n = 0;
  while (t < end && n < SAMPLE_N) {
    const u = UNIVERSE[Math.floor(rnd() * UNIVERSE.length)];
    const hold = Math.floor(6 + rnd() * 74);
    const entry = t;
    const exit = entry + hold * DAY * 1.42;
    if (exit > end) break;
    const win = winFlags[n];
    const entryPx = r2(28 + rnd() * 190);
    const retPct = win ? 6 + rnd() * 34 : -(2.5 + rnd() * 8);
    const exitPx = r2(entryPx * (1 + retPct / 100));
    const shares = Math.round((42000 + rnd() * 26000) / entryPx);
    const reason = win
      ? (retPct > 24 ? EXIT_REASONS[0] : EXIT_REASONS[1])
      : (retPct < -7 ? EXIT_REASONS[2] : EXIT_REASONS[3 + Math.floor(rnd() * 3)]);
    trades.push({
      id: 'T' + String(++n).padStart(3, '0'),
      sym: u[0], name: u[1], sector: u[2], side: '做多',
      entryDate: iso(entry), entryPx,
      exitDate: iso(exit), exitPx,
      shares, holdDays: Math.round(hold * 1.42 * 5 / 7),
      pnl: Math.round((exitPx - entryPx) * shares),
      retPct: r1(retPct),
      reason,
    });
    t = entry + Math.floor(28 + rnd() * 46) * DAY;
  }
}
const wins = trades.filter((t) => t.pnl > 0);
const losses = trades.filter((t) => t.pnl <= 0);
const grossWin = wins.reduce((a, t) => a + t.pnl, 0);
const grossLoss = Math.abs(losses.reduce((a, t) => a + t.pnl, 0));
// 頁頂公佈的是整體 187 筆的數字;trades 只是其中 52 筆抽樣,表頭會註明。
const runStats = {
  tradeCount: 187,
  sampleCount: trades.length,
  winRate: 46.0,
  plRatio: 2.41,
  avgHold: Math.round(trades.reduce((a, t) => a + t.holdDays, 0) / trades.length),
  bestTrade: r1(Math.max(...trades.map((t) => t.retPct))),
  worstTrade: r1(Math.min(...trades.map((t) => t.retPct))),
  sampleWinRate: r1((wins.length / trades.length) * 100),
  samplePlRatio: r2((grossWin / wins.length) / (grossLoss / losses.length)),
};

/* ---------- 運行詳情:持倉變化 ---------- */
const CHANGE_KINDS = [
  ['新增', '突破 30 日新高,賠率 3.4R 過門檻'],
  ['加倉', '首段獲利 1R,按計劃加第二注'],
  ['減倉', '波幅擴大,風險預算超標'],
  ['清倉', '觸及移動止蝕'],
  ['清倉', '觸及目標 3R'],
  ['新增', '回踩成本線企穩,二次入場'],
  ['減倉', '月度虧損接近熔斷線,全組降曝險'],
];
const holdingChanges = [];
{
  let d = utc('2026-06-26');
  for (let i = 0; i < 14; i++) {
    const u = UNIVERSE[Math.floor(rnd() * UNIVERSE.length)];
    const k = CHANGE_KINDS[Math.floor(rnd() * CHANGE_KINDS.length)];
    const before = k[0] === '新增' ? 0 : r1(3 + rnd() * 8);
    let after;
    if (k[0] === '新增') after = r1(4 + rnd() * 5);
    else if (k[0] === '加倉') after = r1(before + 2 + rnd() * 3);
    else if (k[0] === '減倉') after = r1(Math.max(1, before - (1 + rnd() * 3)));
    else after = 0;
    holdingChanges.push({
      date: iso(d), action: k[0], sym: u[0], name: u[1],
      before, after, reason: k[1],
    });
    d -= Math.floor(2 + rnd() * 9) * DAY;
  }
}

/* ---------- 運行詳情:期間內三線對比(重訂基期 100) ---------- */
// 由趨勢波段本身那條曲線切出運行期間,令頁頂 KPI 與圖上那條線出自同一份數據。
const RUN_FROM = '2019-01-02', RUN_TO = '2026-06-30';
const runIdx = [];
for (let i = 0; i < N; i++) if (WK[i] >= RUN_FROM && WK[i] <= RUN_TO) runIdx.push(i);
const rebase = (arr) => {
  const b = arr[runIdx[0]];
  return runIdx.map((i) => r2((arr[i] / b) * 100));
};
const tsStrat = strategies.find((s) => s.id === 'trend-swing');
const runSeries = {
  dates: runIdx.map((i) => WK[i]),
  strategy: rebase(tsStrat.equity),
  qqq: rebase(benchmarks.QQQ.equity),
  spy: rebase(benchmarks.SPY.equity),
};
const runYears = r1((utc(runSeries.dates[runSeries.dates.length - 1]) - utc(runSeries.dates[0])) / (365.25 * DAY));
const runRets = [];
for (let i = 1; i < runSeries.strategy.length; i++)
  runRets.push(runSeries.strategy[i] / runSeries.strategy[i - 1] - 1);
const qqqRets = [];
for (let i = 1; i < runSeries.qqq.length; i++)
  qqqRets.push(runSeries.qqq[i] / runSeries.qqq[i - 1] - 1);

const runDerived = {
  cagr: r1(cagr(runSeries.strategy, runYears)),
  maxDD: r1(maxDrawdown(runSeries.strategy)),
  sortino: r2(sortino(runRets)),
  vol: r1(annVol(runRets)),
  cumReturn: r1(runSeries.strategy[runSeries.strategy.length - 1] - 100),
  qqqCagr: r1(cagr(runSeries.qqq, runYears)),
  qqqMaxDD: r1(maxDrawdown(runSeries.qqq)),
  qqqCumReturn: r1(runSeries.qqq[runSeries.qqq.length - 1] - 100),
  spyCagr: r1(cagr(runSeries.spy, runYears)),
  spyCumReturn: r1(runSeries.spy[runSeries.spy.length - 1] - 100),
  turnover: 214,          // 年化換手率 %
};
runDerived.excessCagr = r1(runDerived.cagr - runDerived.qqqCagr);

// 把首行(即本次運行)的公佈數字對齊實際曲線
RUN_ROWS[0].cagr = runDerived.cagr;
RUN_ROWS[0].mdd = runDerived.maxDD;
RUN_ROWS[0].sortino = runDerived.sortino;

/* ---------- 個股:蠟燭圖 + 因子 ---------- */
const STOCK_DAYS = 252;
const sdates = tradingDaysEndingAt('2026-08-21', STOCK_DAYS);

// 分段路徑:盤整 → 突破 → 回調 → 收斂 → 突破 → 深度修正 → 再突破
const PHASES = [
  { to: 40, target: 106, vol: 0.011, drift: 'flat' },   // 打底
  { to: 76, target: 132, vol: 0.017, drift: 'up' },     // 第一段突破
  { to: 110, target: 116, vol: 0.016, drift: 'down' },  // 回調
  { to: 122, target: 120, vol: 0.008, drift: 'flat' },  // 收斂(VCP)
  { to: 166, target: 168, vol: 0.018, drift: 'up' },    // 第二段突破
  { to: 202, target: 139, vol: 0.020, drift: 'down' },  // 深度修正
  { to: 224, target: 148, vol: 0.010, drift: 'flat' },  // 再打底
  { to: 252, target: 181, vol: 0.017, drift: 'up' },    // 第三段突破
];
const closes = [];
{
  let px = 101.5;
  let start = 0;
  for (const ph of PHASES) {
    const len = ph.to - start;
    const from = px;
    for (let i = 0; i < len; i++) {
      const prog = (i + 1) / len;
      // 沿線性路徑走,再加雜訊;不用純隨機,確保形態看得出
      const pathPx = from + (ph.target - from) * (ph.drift === 'flat' ? prog * 0.4 + 0.3 : Math.pow(prog, 0.85));
      px = px * (1 + gauss() * ph.vol) * 0.55 + pathPx * 0.45;
      closes.push(px);
    }
    px = closes[closes.length - 1];
    start = ph.to;
  }
}
const candles = [];
const volumes = [];
for (let i = 0; i < STOCK_DAYS; i++) {
  const c = closes[i];
  const prev = i === 0 ? c : closes[i - 1];
  const gap = 1 + gauss() * 0.003;
  const o = r2(prev * gap);
  const rng = Math.abs(gauss()) * 0.012 + 0.005;
  const hi = r2(Math.max(o, c) * (1 + rng * (0.4 + rnd() * 0.6)));
  const lo = r2(Math.min(o, c) * (1 - rng * (0.4 + rnd() * 0.6)));
  candles.push({ time: sdates[i], open: o, high: hi, low: lo, close: r2(c) });
  const move = Math.abs(c / prev - 1);
  const base = 1.9 + rnd() * 0.9;
  const spike = move > 0.025 ? 2.2 + rnd() * 1.6 : 1;
  volumes.push({ time: sdates[i], value: r2((base * spike) * 1e6 / 1e6 * 1e6) });
}

// 進出場 markers(對齊形態)
const MARK = [
  { i: 44, side: 'buy', text: '買入 突破' },
  { i: 101, side: 'sell', text: '賣出 移動止蝕' },
  { i: 124, side: 'buy', text: '買入 二次突破' },
  { i: 170, side: 'sell', text: '賣出 目標 3R' },
  { i: 218, side: 'buy', text: '買入 突破' },
];
const markers = MARK.map((m) => ({
  time: sdates[m.i], side: m.side, price: candles[m.i].close, text: m.text,
}));

// 逐日因子
function sma(arr, i, n) {
  const s = Math.max(0, i - n + 1);
  let a = 0; for (let k = s; k <= i; k++) a += arr[k];
  return a / (i - s + 1);
}
const factors = [];
for (let i = 0; i < STOCK_DAYS; i++) {
  const c = closes[i];
  const back = closes[Math.max(0, i - 20)];
  const mom20 = (c / back - 1) * 100;
  const momentum = Math.max(2, Math.min(98, 50 + mom20 * 2.6 + gauss() * 3));
  const quality = Math.max(40, Math.min(96, 74 + Math.sin(i / 41) * 8 + gauss() * 1.6));
  const ma50 = sma(closes, i, 50);
  const stretch = (c / ma50 - 1) * 100;
  const oversold = Math.max(2, Math.min(98, 50 - stretch * 3.1 + gauss() * 3.4));
  const supply = Math.max(5, Math.min(97, 46 + Math.sin(i / 27 + 1.4) * 22 + gauss() * 4));
  const composite = 0.34 * momentum + 0.30 * quality + 0.18 * (100 - oversold) + 0.18 * supply;
  const selected = composite >= 62 && quality >= 62 && momentum >= 52;
  factors.push({
    time: sdates[i],
    quality: r1(quality), momentum: r1(momentum),
    oversold: r1(oversold), supply: r1(supply),
    composite: r1(composite), selected,
  });
}

/* ---------- 參數掃描 ---------- */
const SWEEP_ROWS = [10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60];   // 突破日數 N
const SWEEP_COLS = [4, 5, 6, 7, 8, 9, 10, 12, 14, 16];             // 止蝕幅度 %
const PLATEAU_N = 30, PLATEAU_S = 8;
const SPIKES = [
  { n: 15, s: 14, value: 27.4 },
  { n: 55, s: 5, value: 24.1 },
];
const grid = [];
for (let ri = 0; ri < SWEEP_ROWS.length; ri++) {
  const row = [];
  for (let ci = 0; ci < SWEEP_COLS.length; ci++) {
    const n = SWEEP_ROWS[ri], s = SWEEP_COLS[ci];
    const dn = (n - PLATEAU_N) / 13.5;
    const ds = (s - PLATEAU_S) / 3.5;
    const plateau = 16.4 * Math.exp(-0.5 * (dn * dn + ds * ds));
    const noise = (rnd() - 0.5) * 2.1;
    let v = 3.6 + plateau + noise;
    const sp = SPIKES.find((x) => x.n === n && x.s === s);
    const isSpike = !!sp;
    if (sp) v = sp.value;
    const mdd = isSpike ? -(14 + rnd() * 4) : -(38 - v * 0.85 + rnd() * 4);
    row.push({
      n, s,
      cagr: r1(v),
      mdd: r1(mdd),
      sortino: r2(Math.max(0.12, v / 13 + (isSpike ? 0.55 : 0) + (rnd() - 0.5) * 0.12)),
      trades: Math.round(430 - n * 5.2 + (rnd() - 0.5) * 18),
      spike: isSpike,
    });
  }
  grid.push(row);
}
// 平原範圍(供畫面標註)
const plateauCells = [];
for (let ri = 0; ri < SWEEP_ROWS.length; ri++)
  for (let ci = 0; ci < SWEEP_COLS.length; ci++)
    if (!grid[ri][ci].spike && grid[ri][ci].cagr >= 15.5) plateauCells.push([ri, ci]);

/* ---------- 組裝 ---------- */
const data = {
  meta: {
    asOf: '2026-08-21',
    snapshot: 'DS-2026-08-21-a',
    periodFrom: WK[0],
    periodTo: WK[N - 1],
    years: r1(YEARS),
    disclaimer: '原型・假數據',
  },
  weeklyDates: WK,
  strategies,
  benchmarks,
  trendSwing: {
    runs: RUN_ROWS,
    paper: {
      startCapital: paperStart,
      inceptionDate: '2026-02-02',
      dates: paperWeeks,
      equity: paperEq,
      benchEquity: paperBench,
      value: Math.round(paperStart * paperEq[paperEq.length - 1] / 100),
      returnPct: r1(paperEq[paperEq.length - 1] - 100),
      benchReturnPct: r1(paperBench[paperBench.length - 1] - 100),
      cashPct: r1(100 - paperInvested),
      positions: paperPositions,
    },
  },
  run: {
    id: 'RUN-2026-0812-07',
    strategyId: 'trend-swing',
    strategyName: '趨勢波段',
    version: 'v2.3.0',
    params: 'N=30 · 止蝕 8% · 目標 3R · 最多 12 持倉',
    paramList: [
      ['突破日數 N', '30'], ['止蝕幅度', '8%'], ['目標', '3R'],
      ['最多持倉', '12'], ['換倉節奏', '週'], ['共用風控層', '啟用'],
    ],
    periodFrom: '2019-01-02',
    periodTo: '2026-06-30',
    snapshot: 'DS-2026-06-30-b',
    ranAt: '2026-08-12 14:22:07',
    engine: 'karst-engine 0.9.4',
    stats: runStats,
    derived: runDerived,
    series: runSeries,
    trades,
    holdingChanges,
  },
  stock: {
    sym: 'NVLS',
    name: '諾瓦半導體',
    en: 'Novalis Semiconductor',
    sector: '半導體',
    candles,
    volumes,
    markers,
    factors,
    strategyId: 'trend-swing',
    strategyName: '趨勢波段',
    position: { status: '持倉中', entryDate: sdates[218], entryPx: candles[218].close },
  },
  sweep: {
    rowLabel: '突破日數 N',
    colLabel: '止蝕幅度',
    rows: SWEEP_ROWS,
    cols: SWEEP_COLS,
    metric: '年化回報',
    grid,
    plateauCells,
    plateauCenter: [SWEEP_ROWS.indexOf(PLATEAU_N), SWEEP_COLS.indexOf(PLATEAU_S)],
  },
};

const header = `// Karst 原型假數據 —— 由 tools/gen-data.mjs 產生,請勿人手編輯。
// 全部數值為合成假數據,個股與持倉代號皆屬虛構,不對應任何真實標的。
`;
fs.mkdirSync(path.dirname(OUT), { recursive: true });
fs.writeFileSync(OUT, '﻿' + header + 'window.KARST = ' + JSON.stringify(data) + ';\n', 'utf8');

console.log('written:', OUT, (fs.statSync(OUT).size / 1024).toFixed(1) + ' KB');
console.log('weeks:', N, 'years:', r1(YEARS));
console.log('--- 策略指標 ---');
for (const s of strategies) {
  console.log(
    s.name.padEnd(12),
    '累計', String(s.metrics.cumReturn).padStart(7),
    '年化', String(s.metrics.cagr).padStart(6),
    'MDD', String(s.metrics.maxDD).padStart(7),
    'Sortino', s.metrics.sortino
  );
}
for (const k of Object.keys(benchmarks)) {
  const m = benchmarks[k].metrics;
  console.log(k.padEnd(12), '累計', String(m.cumReturn).padStart(7), '年化', String(m.cagr).padStart(6), 'MDD', String(m.maxDD).padStart(7));
}
console.log('--- 交易 ---', runStats);
console.log('--- 掃描 ---', 'plateau cells:', plateauCells.length,
  'max:', Math.max(...grid.flat().map((c) => c.cagr)));
