"""Self-contained, escaped HTML. No scripts, remote assets, or model calls."""
from html import escape
from importlib.resources import files
import json
from urllib.parse import urlparse

from ..calculations import sma
from ..packet import confined

VERSION = "0.2.0"
LAYERS = {"L1": "市場與宏觀", "L2": "產業與價值鏈", "L3": "公司基本面",
          "L4": "估值與預期", "L5": "技術與市場行為", "L6": "投資綜合"}
HEADLINES = {"recommendation": "目前建議", "main_reason": "主要理由",
             "key_assumption": "關鍵假設", "strongest_counter": "最強反證",
             "change_conditions": "改變行動的條件", "change_since_last": "與上次相比"}
SCENARIOS = {"bear": "審慎", "base": "基準", "bull": "樂觀"}


def e(value):
    return escape(str(value), quote=True)


def number(value, suffix=""):
    return "未提供" if value is None else f"{value:,.2f}{suffix}"


def percentage(value):
    return "未提供" if value is None else f"{value * 100:,.1f}%"


def statement(value):
    links = " ".join(f'<a class="cite" href="#source-{e(c["evidence_id"])}">'
                     f'{e(c["evidence_id"])} · {e(c["locator"])}</a>' for c in value["citations"])
    return f'<p>{e(value["text"])} <span>{links}</span></p>'


def statements(values):
    return "".join(statement(value) for value in values) or '<p class="muted">未提供</p>'


def chart(bars, timeframe, levels):
    complete = [bar for bar in bars if bar["complete"]]
    if not complete:
        return '<p class="muted">沒有已收定的價格資料。</p>'
    visible = complete[-90:]
    low = min(b["low"] for b in visible)
    high = max(b["high"] for b in visible)
    relevant = [level for level in levels if level["timeframe"] == timeframe]
    moving = [sma(complete[:len(complete)-len(visible)+i+1]) for i in range(len(visible))]
    extras = [v for v in moving if v is not None] if timeframe == "D" else []
    extras += [value for level in relevant for value in (level["lower"], level["upper"])]
    low, high = min([low] + extras), max([high] + extras)
    span = high-low or 1
    low, high = low-span*.07, high+span*.07
    def y(value):
        return 20 + (high-value)/(high-low)*230
    def x(index):
        return 64 + (index+.5)*716/len(visible)
    width = max(1, 716/len(visible)*.55)
    body = []
    for i in range(5):
        value = low + (high-low)*i/4
        body.append(f'<path d="M58 {y(value):.2f}H788" stroke="#dde5e9"/>'
                    f'<text x="4" y="{y(value)+4:.2f}">{value:.2f}</text>')
    for level in relevant:
        body.append(f'<rect x="58" y="{y(level["upper"]):.2f}" width="730" '
                    f'height="{max(1,y(level["lower"])-y(level["upper"])):.2f}" fill="#e6b65a" opacity=".22"/>')
    max_volume = max(b["volume"] for b in visible) or 1
    for i, bar in enumerate(visible):
        color = "#137769" if bar["close"] >= bar["open"] else "#be5950"
        body.append(f'<path d="M{x(i):.2f} {y(bar["high"]):.2f}V{y(bar["low"]):.2f}" stroke="{color}"/>'
                    f'<rect x="{x(i)-width/2:.2f}" y="{y(max(bar["open"],bar["close"])):.2f}" '
                    f'width="{width:.2f}" height="{max(1,abs(y(bar["open"])-y(bar["close"]))):.2f}" fill="{color}"/>'
                    f'<rect x="{x(i)-width/2:.2f}" y="{300-bar["volume"]/max_volume*32:.2f}" '
                    f'width="{width:.2f}" height="{bar["volume"]/max_volume*32:.2f}" fill="{color}" opacity=".4"/>')
    if timeframe == "D":
        points = " ".join(f'{x(i):.2f},{y(value):.2f}' for i, value in enumerate(moving) if value is not None)
        body.append(f'<polyline points="{points}" fill="none" stroke="#556fc4" stroke-width="2"/>')
    body.append(f'<text x="58" y="325">{e(visible[0]["at"][:10])}</text>'
                f'<text x="690" y="325">{e(visible[-1]["at"][:10])}</text>')
    return '<svg viewBox="0 0 800 340" role="img" aria-label="價格、成交量及已確認關鍵區域">' + "".join(body) + '</svg>'


def render(packet, records, research, calculated, root):
    security, valuation, technical, plan = (packet["security"], research["valuation"],
                                           research["technical"], research["plan"])
    css = files("karst").joinpath("page/style.css").read_text(encoding="utf-8")
    mode = {"synthetic_demo": "合成資料示範 · 非真實股票研究",
            "integration_example": "真實資料接線示例 · 判斷為測試輸入，非正式投研結論",
            "offline_replay": "已保存研究重播 · 以列明截止時間為準"}[research["mode"]]
    base = calculated["valuation"].get("base", {}).get("fair_value_per_share")
    target = next((v["price"] for v in valuation["target_prices"] if v["name"] == "base"), None)
    out = [f'<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8">'
           f'<meta name="viewport" content="width=device-width,initial-scale=1">'
           f'<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'; img-src data:; base-uri \'none\'; form-action \'none\'">'
           f'<title>{e(security["ticker"])} · Karst</title><style>{css}</style></head><body>'
           f'<div class="banner">{mode}</div><main><header><div class="brand">KARST / RESEARCH WORKBENCH</div>'
           f'<h1>{e(security["ticker"])} <span>{e(security["name"])}</span></h1>'
           f'<p class="muted">資料截止 {e(packet["as_of"])} · 目標期限 {e(research["target_date"])} · {e(security["currency"])}</p>'
           f'<p class="muted">價格時間 {e(research["market"]["at"])} · 研究生成 {e(research["created_at"])}</p></header>']
    out.append('<section class="metrics">')
    metrics = [("參考價格", number(research["market"]["price"])),
               ("當日內在價值 · 基準", number(base)),
               ("期限目標價 · 基準", number(target)),
               ("相對基準價值折讓", percentage(calculated["price_to_value_gap"]))]
    for label, value in metrics:
        out.append(f'<div><small>{label}</small><strong>{value}</strong></div>')
    out.append('</section><section class="summary"><h2>投資判斷</h2><dl>')
    for key, label in HEADLINES.items():
        out.append(f'<dt>{label}</dt><dd>{statement(research["headline"][key])}</dd>')
    out.append('</dl></section>')
    gaps = list(research["open_questions"]) + list(packet["pending_updates"])
    gaps += [r["reason"] for r in packet["requirements"] if r["status"] in ("partial", "missing")]
    gaps += [r["question"] for r in packet["supplement_requests"] if r["status"] == "pending"]
    gaps += [r["status_reason"] for r in records if r.get("status", "ok") != "ok"]
    if gaps:
        out.append('<aside><h3>仍需補查</h3><ul>' + ''.join(f'<li>{e(gap)}</li>' for gap in gaps) + '</ul></aside>')
    out.append(f'<section><h2>估值與市場預期</h2><p class="muted">內在價值日期 {e(valuation["valuation_date"])}；基準情境由假設推導，並非高低價的平均。</p>')
    if calculated["valuation"]:
        out.append('<div class="table"><table><thead><tr><th>情境</th><th>每股內在價值</th><th>期限目標價</th><th>終值 / 企業價值</th></tr></thead><tbody>')
        for name, label in SCENARIOS.items():
            row = calculated["valuation"][name]
            target_row = next((r["price"] for r in valuation["target_prices"] if r["name"] == name), None)
            out.append(f'<tr><td>{label}</td><td>{number(row["fair_value_per_share"])}</td><td>{number(target_row)}</td><td>{percentage(row["terminal_share_of_enterprise_value"])}</td></tr>')
        out.append('</tbody></table></div>')
    else:
        out.append(f'<p>{e(valuation["gap_reason"])}</p>')
    for label, key in (("方法為何適合", "method_rationale"), ("另一估值視角", "alternative_view"),
                       ("相對上次的變化", "change_attribution"), ("現價要求什麼", "implied_requirements")):
        out.append(f'<h3>{label}</h3>{statement(valuation[key])}')
    out.append('<h3>關鍵假設</h3>' + statements(valuation["top_assumptions"]))
    for row in valuation["scenarios"]:
        inp, value = row["calculation"], calculated["valuation"][row["name"]]
        out.append(f'<details><summary>{SCENARIOS[row["name"]]}情境：計算與假設</summary>{statement(row["rationale"])}'
                   '<p>年末 FCFF 折現 + 終值折現 = 企業價值；加現金與非經營資產，減債務與其他索償，再除攤薄股數。</p>'
                   f'<p>FCFF（逐年、{e(inp["currency"])}絕對金額）：{e(", ".join(number(f) for f in inp["cashflows"]))}<br>'
                   f'WACC {percentage(inp["discount_rate"])} · 永續增長 {percentage(inp["terminal_growth"])}<br>'
                   f'現金 {number(inp["cash"])} · 非經營資產 {number(inp["nonoperating_assets"])} · 債務 {number(inp["debt"])} · 其他索償 {number(inp["other_claims"])}<br>'
                   f'攤薄股數 {number(inp["diluted_shares"])} · 企業價值 {number(value["enterprise_value"])} · 股權價值 {number(value["equity_value"])}</p></details>')
    for row in valuation["target_prices"]:
        out.append(f'<h3>{SCENARIOS[row["name"]]}目標價如何橋接</h3>{statement(row["rationale"])}')
    out.append('</section><section><h2>技術結構與關鍵價位</h2>')
    out.append(statement(technical["reading"]))
    out.append(f'<p>200 日 SMA：{number(calculated["ma200"])}（K 線口徑）；報價口徑：{number(calculated["ma200_quote_basis"])}。</p>'
               f'<p class="muted">K 線口徑：{e(technical["price_basis"])} · 報價 × {number(technical["quote_to_bar_factor"])} = K 線價格。只畫已收定的 K 線；下方為成交量，藍線為日線 SMA200。</p>')
    for timeframe, label in (("D", "日線"), ("W", "週線"), ("M", "月線")):
        out.append(f'<details {"open" if timeframe == "D" else ""}><summary>{label}</summary>{chart(technical["views"][timeframe], timeframe, technical["key_levels"])}</details>')
    for level in technical["key_levels"]:
        out.append(f'<h3>{"支撐" if level["kind"] == "support" else "阻力"} {number(level["lower"])}–{number(level["upper"])} · {e(level["timeframe"])}</h3>'
                   f'{statement(level["rationale"])}<p class="muted">確認於 {e(level["confirmed_at"])}</p>')
    out.append(''.join(f'<p class="muted">{e(gap)}</p>' for gap in technical["gaps"]))
    out.append('</section><section><h2>條件式投資計劃</h2>')
    out.append(f'<p>入場 {number(plan["entry_price"])} → 退出參考 {number(plan["exit_price"])} / 目標 {number(plan["target_price"])}；每股來回成本 {number(plan["round_trip_cost_per_share"])}。</p>')
    for key, label in (("risk_reward", "計劃入場"), ("current_price_risk_reward", "按參考現價")):
        rr = calculated[key]
        out.append(f'<h3>{label}</h3>')
        if rr["available"]:
            out.append(f'<p>回報 / 風險 {number(rr["ratio"])} 倍 · 潛在回報 {percentage(rr["reward_return"])} · 計劃價格損失 {percentage(rr["planned_loss_return"])}<br>'
                       f'若跳空至壓力價 {number(plan["stress_price"])}，每股損失 {number(rr["stress_loss_per_share"])}。退出參考價不保證成交。</p>')
        else:
            out.append(f'<p>{e(rr["reason"])}</p>')
    out.append(statement(plan["execution_rule"]) + '<h3>推翻條件</h3>' + statements(plan["invalidators"]))
    out.append(f'<p class="muted">下次覆核 {e(plan["next_review_at"])}</p></section><section><h2>六層研究</h2>')
    for key, label in LAYERS.items():
        layer = research["layers"][key]
        out.append(f'<details><summary>{key} / {label}</summary>{statement(layer["conclusion"])}'
                   f'<p class="muted">本層判斷時間 {e(layer["assessed_at"])} · 讀取來源 {e(", ".join(layer["read_evidence_ids"]) or "未提供")}</p>'
                   f'<h3>依賴假設</h3>{statements(layer["assumptions"])}<h3>最強反證</h3>{statement(layer["strongest_counter"])}'
                   + ''.join(f'<p>缺口：{e(gap)}</p>' for gap in layer["gaps"]) + '</details>')
    out.append('</section><section><h2>相位與攻擊問題</h2>')
    for phase in research["phases"]:
        out.append(f'<h3>{e(phase["dimension"])} · {e(phase["timeframe"])} · {e(phase["state"])}</h3>'
                   f'<p class="muted">{e(phase["status"])} · 確認時間 {e(phase["confirmed_at"] or "尚未確認")}</p>{statement(phase["basis"])}')
    for module in research["modules"]:
        out.append(f'<h3>{e(module["name"])}</h3>{statement(module["activation_reason"])}<ul>'
                   + ''.join(f'<li>{e(q)}</li>' for q in module["questions"]) + '</ul>')
    out.append('</section><section><h2>證據、原文與取得紀錄</h2>')
    for record in records:
        url = record["source_url"]
        link = f'<a href="{e(url)}" target="_blank" rel="noopener noreferrer">來源網站</a>' if url and urlparse(url).scheme in ("http", "https") else "合成／離線來源"
        out.append(f'<details id="source-{e(record["evidence_id"])}"><summary>{e(record["evidence_id"])} · {e(record["source"])} · {e(record["kind"])}</summary>'
                   f'<p>{link} · 發布 {e(record["published_at"] or "未知")} · 取得 {e(record["fetched_at"])}<br>'
                   f'版本 {e(record["source_version"])} · SHA256 {e(record["artifact"]["sha256"])}</p>')
        for field, label in (("published_at", "公開時間"), ("data_as_of", "資料截至")):
            precision = record.get(field + "_precision", "datetime" if record[field] else "unknown")
            zone = record.get(field + "_timezone")
            out.append(f'<p>{label}：{e(record[field] or "未知")} · 精度 {e(precision)}'
                       f' · 日期時區 {e(zone or "未提供／時刻內含偏移")}'
                       f'<br>{e(record.get(field + "_basis", "未提供"))}</p>')
        status = record.get("status", "ok")
        if status != "ok":
            out.append(f'<p><strong>{"取得失敗" if status == "error" else "查詢回空"}</strong>：{e(record["status_reason"])}。此紀錄不能作為公司事實引用。</p>')
        if record.get("coverage") is not None:
            out.append('<p>來源原始期間／涵蓋描述</p><pre>' + e(json.dumps(record["coverage"], ensure_ascii=False, indent=2)) + '</pre>')
        out.append(''.join(f'<p>來源缺口：{e(g)}</p>' for g in record["known_gaps"]))
        data = confined(root, record["artifact"]["path"]).read_bytes()
        try:
            text = data.decode("utf-8")
            out.append('<pre>' + '\n'.join(f'{i:>4}  {e(line)}' for i, line in enumerate(text.splitlines(), 1)) + '</pre>')
        except UnicodeDecodeError:
            out.append('<p>二進位原檔保存在發布包 inputs/；本頁不解析其內容。</p>')
        out.append('</details>')
    out.append(f'</section><footer>Packet {e(packet["packet_id"])} · Research {e(research["research_id"])}<br>'
               f'策略 {e(research["strategy_version"])} · 方法 {e(research["method_version"])} · Renderer {VERSION}<br>'
               '本頁呈現傳入的研究判斷；程式只負責驗證、計算與發布。</footer></main></body></html>')
    return ''.join(out)
