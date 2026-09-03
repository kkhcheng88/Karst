# -*- coding: utf-8 -*-
"""
KARST-168 —— 鏈位表 v2.1:主業轉向改記換鏈日期

用戶裁決 D-152 ②「照建議收貨」,當中一項是 D-151 ② 的建議:
主業轉向的成員不整家出隊,改為舊鏈一行 valid_to=轉向日、新鏈一行 valid_from=同日,
令切片日期之前的樣本仍然可用。

本腳本只讀 v2 的三個檔,不寫回 v2;輸出三個新檔:
  chain_membership_v2_1.csv (UTF-8 BOM)
  removed_v2_1.csv          (UTF-8 BOM)
  chain_stories_v2_1.md     (UTF-8)

跑法: set PYTHONUTF8=1 && python build_v2_1.py
"""

import csv
import io
import os

HERE = os.path.dirname(os.path.abspath(__file__))

SRC_MEMBERSHIP = os.path.join(HERE, "chain_membership_v2.csv")
SRC_REMOVED = os.path.join(HERE, "removed_v2.csv")
SRC_STORIES = os.path.join(HERE, "chain_stories_v2.md")

OUT_MEMBERSHIP = os.path.join(HERE, "chain_membership_v2_1.csv")
OUT_REMOVED = os.path.join(HERE, "removed_v2_1.csv")
OUT_STORIES = os.path.join(HERE, "chain_stories_v2_1.md")

# ---------------------------------------------------------------------------
# 一、轉向日與佐證(逐家一格,全部由 data/sec/10k_text 快取核出,本票沒有新抓年報)
# ---------------------------------------------------------------------------

SWITCH = {
    "MSFT": {
        "old_theme": "software_cloud",
        "new_theme": "hyperscalers",
        "switch_date": "2023-01-23",
        "basis": (
            "年報明文:FY2023 10-K 寫「In January 2023 we announced the third phase of our "
            "OpenAI strategic partnership」,轉向月份由年報確認;日取微軟該次公告日 2023-01-23,"
            "快取內核實不到日,故此欄準確度只到月。"
        ),
        "evidence": (
            "MSFT FY2023 10-K(accession 0000950170-23-035122,申報日 2023-07-27,財年結 2023-06-30)"
            "原文:「In January 2023 we announced the third phase of our OpenAI strategic partnership.」"
            "另一句:「As OpenAI's exclusive cloud provider, Azure powers all of OpenAI's workloads. "
            "We have also increased our investments in the development and deployment of specialized "
            "supercomputing systems to accelerate OpenAI's research.」"
            "邊界佐證:OpenAI 一詞在 FY2023 10-K 出現 7 次、FY2024 出現 9 次,"
            "而上一份 FY2022 10-K(0001564590-22-026876,申報日 2022-07-28)出現 0 次。"
        ),
        "approx": False,
    },
    "ORCL": {
        "old_theme": "software_cloud",
        "new_theme": "hyperscalers",
        "switch_date": "2023-06-01",
        "basis": (
            "近似:取 FY2024 財政年度首日 2023-06-01。該財年是甲骨文年報首次在業務描述開首"
            "以「用 OCI 訓練生成式 AI 模型的 AI 公司」作代表客戶的年度。"
            "票面建議的「2023 年 9 月 OCI 收入首次單獨披露」在年報快取內核實不到,故不採;"
            "removed_v2.csv 原判詞寫「自 2024 年起」,年報證據指向再早一個財年,本票採年報證據。"
            "要留意:這個日期是由 2024-06-20 才公開的年報倒推,本身帶前視成分(見誠實聲明一)。"
        ),
        "evidence": (
            "ORCL FY2024 10-K(accession 0000950170-24-075605,申報日 2024-06-20,財年結 2024-05-31)"
            "業務描述開首原文:「... an artificial intelligence (AI) product company that uses Oracle "
            "Cloud Infrastructure (OCI) to build and serve generative AI models; a global technology "
            "company that uses OCI ...」。"
            "對照:FY2023 10-K(0000950170-23-028914)與 FY2022 10-K(0001564590-22-023675)同一段"
            "只有 SaaS 功能式與風險因素式的通用 AI 字眼(「Our SaaS offerings are also designed to "
            "natively incorporate advanced technologies such as ... artificial intelligence ...」),"
            "沒有以 AI 算力客戶作代表客戶。"
        ),
        "approx": True,
    },
}

# 舊鏈那一行要補回的欄位(v2 已整行刪走,靠 v1 原行 + v2 該鏈的共同欄位重建)
OLD_ROW_FIELDS = {
    "software_cloud": {
        "role": "core",
        "story": "零邊際成本,加座位即刻加得到,沒有實體樽頸;售價由企業 IT 支出週期決定,不由供給缺口決定。",
        "position": "下游:企業訂閱制軟件與雲平台,賣給企業 IT 預算",
        "purity": "股價跟「企業 IT 支出週期」這條敘事走(至轉向日為止)",
        "valid_from_basis": "沿用 v0(舊倉 ADR-0039 鎖死名單,未改)",
        "filer_type": "10-K",
        "added_by": "v2.1",
        "src_theme_v1": "software_cloud",
    }
}

# v2 的 software_cloud purity_note 寫住「v2 剔走四家:MSFT 與 ORCL 按規則 d ...」,
# 在 v2.1 已經不成立。這是本票唯一一處超出「兩家、四行」的連帶改動,已在文件明列。
PURITY_NOTE_FIX = {
    "software_cloud": (
        "共同敘事=「企業 IT 支出週期」。"
        "v2.1 剔走兩家:PLTR 按規則 c(跟自己的政府合約與散戶估值走)、"
        "SHOP 按規則 a(它的開關是商戶 GMV 與消費支出,不是企業 IT 預算)。"
        "MSFT 與 ORCL 不再整家出隊:按 D-151 ② / D-152 ② 改記換鏈日期,"
        "轉向日之前仍屬本鏈,之後轉入 hyperscalers。"
    )
}

# ---------------------------------------------------------------------------
# 二、removed 23 行逐行覆核判詞
# ---------------------------------------------------------------------------

KEEP_REMOVED_REVIEW = {
    ("copper", "BHP"): {
        "review": (
            "維持出隊。規則 d 名下,但沒有轉向日:2022 年至今全期都是鐵礦石主導的多元化礦商,"
            "不是某日由銅轉去別處。舊倉 2026-07-21 手術已把它的 copper 出隊日追溯到 2021-11-30"
            "(走廊首個決策日 2021-12-01 之前),即量度窗內沒有一日屬 copper。"
            "而且 v2 的 65 條鏈裡沒有鐵礦石／多元化礦商那一層,沒有新鏈可換。"
        ),
        "switch_date": "",
        "evidence": (
            "v0 原行 valid_to=2021-11-30,note 原文:「2026-07-21 手術 S1 出隊:綜合礦業‧主盈利=鐵礦石"
            "(中國鋼鐵週期)‧非銅電氣化;去向=中國政策池‧棄」。BHP 是 20-F 外國申報人,"
            "10-K 全文快取沒有它的年報。"
        ),
    },
    ("copper", "RIO"): {
        "review": (
            "維持出隊。理由與 BHP 同:全期鐵礦石與鋁主導,沒有轉向日;"
            "v0 出隊日已追溯至 2021-11-30,窗內沒有一日屬 copper;v2 沒有可換的新鏈。"
        ),
        "switch_date": "",
        "evidence": "v0 原行 valid_to=2021-11-30。RIO 是 20-F 外國申報人,10-K 全文快取沒有它的年報。",
    },
    ("energy", "COP"): {
        "review": (
            "維持出隊,但出隊理由要改寫。轉向日查得到而且很早:2012-04-30 完成下游分拆(Phillips 66),"
            "自此是純上游 E&P。表的起點是 2022-01-01,即量度窗內沒有一日屬 energy(一體化油企)那一層,"
            "補回舊鏈那一行會得出一段空區間,對切片沒有用。"
            "另外要更正一件事:v0 那一行的 valid_to=2026-07-22 是舊倉的表務日期"
            "(energy 主題退役、COP 轉入 upstream_oil 那一天),不是業務轉向日。"
            "COP 本來已在 upstream_oil 現役,本項沒有樣本損失。"
        ),
        "switch_date": "2012-04-30",
        "evidence": (
            "COP FY2012 10-K(accession 0001193125-13-065426,申報日 2013-02-19,財年結 2012-12-31)"
            "原文:「On April 30, 2012, we completed the separation of our downstream businesses into an "
            "independent, publicly traded company, Phillips 66. Our refining, marketing and transportation "
            "businesses, most of our Midstream segment, our Chemicals segment ... were transferred to "
            "Phillips 66.」"
        ),
    },
    ("fintech", "HOOD"): {
        "review": (
            "維持出隊。規則 d 名下,但這一行本來處理的是同一家公司在 v1 出現兩次(fintech 與 web3_crypto)"
            "的去重,不是某日主業轉向。而且舊鏈 fintech 在 v2 已拆成 alt_lending 與 payments,"
            "券商這個位置在 v2 的 65 條鏈裡沒有對應層,沒有舊鏈可以寫 valid_to。"
        ),
        "switch_date": "",
        "evidence": (
            "chain_stories_v2.md 拆鏈表:「fintech → alt_lending / payments;HOOD 併去 crypto_exchange」。"
            "順帶記低一件本票沒有動的事:HOOD 在 crypto_exchange 那一行的 valid_from 仍是 2022-01-01,"
            "即 2022–2023 年的 HOOD 被當成加密交易所,與 MSFT/ORCL 原本那個前視問題同一類;"
            "按票面「其餘 v2 內容一字不改」,本票不改,列作未做事項。"
        ),
    },
}

GENERIC_REVIEW = "維持出隊。規則 {rule} {rule_name},不是主業轉向,不在本票的改動範圍(票面 ②)。"


def read_csv_bom(path):
    with io.open(path, "r", encoding="utf-8-sig", newline="") as f:
        rd = csv.DictReader(f)
        return list(rd), list(rd.fieldnames)


def write_csv_bom(path, fieldnames, rows):
    with io.open(path, "w", encoding="utf-8-sig", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\r\n")
        wr.writeheader()
        for r in rows:
            wr.writerow({k: r.get(k, "") for k in fieldnames})


def build_membership():
    rows, cols = read_csv_bom(SRC_MEMBERSHIP)
    new_cols = list(cols) + ["v21_change", "switch_date_basis", "switch_evidence"]

    out = []
    changed = []
    for r in rows:
        r = dict(r)
        for c in ("v21_change", "switch_date_basis", "switch_evidence"):
            r[c] = ""

        tk, th = r["ticker"], r["theme"]

        # 連帶改動:software_cloud 的逐鏈純度句
        if th in PURITY_NOTE_FIX:
            r["purity_note"] = PURITY_NOTE_FIX[th]

        # 新鏈那一行:valid_from 由 2022-01-01 改為轉向日
        if tk in SWITCH and th == SWITCH[tk]["new_theme"]:
            s = SWITCH[tk]
            old_vf = r["valid_from"]
            r["valid_from"] = s["switch_date"]
            r["valid_from_basis"] = (
                "換鏈日(v2.1,KARST-168):主業轉向日," + ("近似" if s["approx"] else "有年報明文")
            )
            r["note"] = (
                ("Azure" if tk == "MSFT" else "OCI")
                + "(v2.1:%s 起由 %s 轉入本鏈,原 v2 為與 software_cloud 雙掛)"
                % (s["switch_date"], s["old_theme"])
            )
            r["v21_change"] = "新鏈行:valid_from %s → %s" % (old_vf, s["switch_date"])
            r["switch_date_basis"] = s["basis"]
            r["switch_evidence"] = s["evidence"]
            changed.append((tk, th, r["v21_change"]))

        out.append(r)

    # 補回舊鏈那兩行,插在該鏈最後一行之後,令檔案仍然按鏈分組
    for tk, s in SWITCH.items():
        src = [r for r in out if r["ticker"] == tk and r["theme"] == s["new_theme"]][0]
        f = OLD_ROW_FIELDS[s["old_theme"]]
        row = {c: "" for c in new_cols}
        row.update(
            {
                "theme": s["old_theme"],
                "ticker": tk,
                "valid_from": "2022-01-01",
                "valid_to": s["switch_date"],
                "role": f["role"],
                "note": "v2.1 補回:v2 曾按規則 d 整家出隊,現改記為換鏈——本鏈成員至 %s 為止" % s["switch_date"],
                "story": f["story"],
                "position": f["position"],
                "purity": f["purity"],
                "purity_note": PURITY_NOTE_FIX[s["old_theme"]],
                "source_url": src["source_url"],
                "evidence_10k": src["evidence_10k"],
                "added_by": f["added_by"],
                "valid_from_basis": f["valid_from_basis"],
                "filer_type": f["filer_type"],
                "src_theme_v1": f["src_theme_v1"],
                "v21_change": "舊鏈行:v2 已刪,v2.1 補回,valid_to=%s" % s["switch_date"],
                "switch_date_basis": s["basis"],
                "switch_evidence": s["evidence"],
            }
        )
        # 插在同鏈最後一行之後
        idx = max(i for i, r in enumerate(out) if r["theme"] == s["old_theme"])
        out.insert(idx + 1, row)
        changed.append((tk, s["old_theme"], row["v21_change"]))

    write_csv_bom(OUT_MEMBERSHIP, new_cols, out)
    return out, new_cols, changed


def build_removed():
    rows, cols = read_csv_bom(SRC_REMOVED)
    new_cols = list(cols) + ["v21_review", "switch_date", "switch_evidence"]

    out = []
    dropped = []
    for r in rows:
        r = dict(r)
        key = (r["v1_theme"], r["ticker"])
        if r["ticker"] in SWITCH and r["v1_theme"] == SWITCH[r["ticker"]]["old_theme"]:
            dropped.append(key)
            continue  # 已改記換鏈日期,不再是出隊
        if key in KEEP_REMOVED_REVIEW:
            k = KEEP_REMOVED_REVIEW[key]
            r["v21_review"] = k["review"]
            r["switch_date"] = k["switch_date"]
            r["switch_evidence"] = k["evidence"]
        else:
            r["v21_review"] = GENERIC_REVIEW.format(rule=r["rule"], rule_name=r["rule_name"])
            r["switch_date"] = ""
            r["switch_evidence"] = ""
        out.append(r)

    write_csv_bom(OUT_REMOVED, new_cols, out)
    return out, dropped


def build_stories(mem_rows, changed, removed_rows, dropped):
    # newline="" 保留原檔的 CRLF,令 v2.1 與 v2 只差在真正改動的地方
    with io.open(SRC_STORIES, "r", encoding="utf-8", newline="") as f:
        text = f.read()

    n_rows = len(mem_rows)
    n_themes = len(set(r["theme"] for r in mem_rows))
    n_cos = len(set(r["ticker"] for r in mem_rows))

    section = u"""## v2.1 變更(KARST-168,2026-09-03)

> **本文件 = `chain_stories_v2.md` 全文,只加了本節。** v2 的三個檔(`chain_membership_v2.csv`、
> `chain_stories_v2.md`、`removed_v2.csv`)一字未改,仍在原處。誠實聲明沿用上面那四項。
> **凡本文件其餘部分與本節衝突,以本節與 `chain_membership_v2_1.csv` 為準**——票面規定只加一節,
> 所以下面 v2 原文那幾處還是舊數:`software_cloud` 的純度句、`hyperscalers` 成員表裡 MSFT/ORCL 的
> 入位日、以及文末出隊表的 MSFT/ORCL 兩行。

### 改了什麼、為什麼

用戶裁決 D-152 ②(原話:「照建議收貨」)收下了 D-151 ② 的建議:**主業轉向的成員不再整家出隊,
改記為換鏈日期**——舊鏈一行 `valid_to` = 轉向日、新鏈一行 `valid_from` = 同日。這樣切片日期在轉向日
之前的樣本仍然可用,不會因為公司後來轉了型就連當年那幾年一併消失。

本票逐行覆核 `removed_v2.csv` 全部 23 行,答一條問題:**這一行是不是「某一日主業轉了向」?**
答是而且兩條鏈在 v2 都存在的,改記換鏈日期;答不是的,維持出隊,但把覆核判詞寫回
`removed_v2_1.csv` 的 `v21_review` 欄。

### 改記換鏈日期的:兩家、四行

| 公司 | 舊鏈(valid_to) | 新鏈(valid_from) | 轉向日 | 準確度 | 佐證 |
|---|---|---|---|---|---|
| MSFT | `software_cloud` 2022-01-01 → **2023-01-23** | `hyperscalers` **2023-01-23** → 現役 | 2023-01-23 | 月準確 | FY2023 10-K 明文「In January 2023 we announced the third phase of our OpenAI strategic partnership」;OpenAI 一詞在 FY2022 年報 0 次、FY2023 年報 7 次 |
| ORCL | `software_cloud` 2022-01-01 → **2023-06-01** | `hyperscalers` **2023-06-01** → 現役 | 2023-06-01 | **近似** | FY2024 10-K 業務描述開首首次以「用 OCI 訓練生成式 AI 模型的 AI 公司」作代表客戶;FY2022/FY2023 同一段只有通用 AI 字眼。取該財年首日 |

兩點要講清楚:

1. **MSFT 那個日期是事前可得的**——2023 年 1 月的公告當日全世界都看得到,年報只是事後確認月份。
   **ORCL 那個不是**:它由 2024-06-20 才公開的年報倒推,本身帶前視成分。票面建議的
   「2023 年 9 月 OCI 收入首次單獨披露」在年報快取裡核實不到,所以沒有採用;
   `removed_v2.csv` 原判詞寫「自 2024 年起」,年報證據指向再早一個財年,本票採年報證據並標記近似。
2. **一處連帶改動**:`software_cloud` 的逐鏈純度句(`purity_note`)在 v2 寫住「v2 剔走四家:MSFT 與
   ORCL 按規則 d……」,在 v2.1 已經不成立,所以那一句改寫了。這是本票唯一一處超出「兩家、四行」的
   改動,在此明列。其餘 347 行的內容一個字沒有動。

### 維持出隊的:21 行

其中四行掛在規則 d 名下,但逐行看過之後都不是「某一日轉了向」:

| 公司 | 舊鏈 | 為什麼仍然出隊 | 查到的轉向日 |
|---|---|---|---|
| BHP | `copper` | 全期都是鐵礦石主導的多元化礦商,沒有轉向日;舊倉已把出隊日追溯到 2021-11-30,量度窗內沒有一日屬 `copper`;而且 v2 的 65 條鏈沒有鐵礦石那一層,沒有新鏈可換 | 無 |
| RIO | `copper` | 同 BHP | 無 |
| COP | `energy` | 轉向日查得到而且很早:**2012-04-30 完成下游分拆(Phillips 66)**,自此是純上游。表的起點是 2022-01-01,補回舊鏈那一行只會得出一段空區間。順帶更正:v0 那一行的 `valid_to=2026-07-22` 是舊倉的表務日期,不是業務轉向日 | 2012-04-30(有年報明文) |
| HOOD | `fintech` | 這一行本來是同一家公司在 v1 出現兩次的去重,不是轉向;而且 `fintech` 在 v2 已拆散,券商這個位置沒有對應層,沒有舊鏈可以寫 `valid_to` | 無 |

其餘 17 行中的分別是規則 a(位置不同)、b(定價機制不同)、c(單一資產主導)其中之一,
按票面 ② 維持出隊,判詞逐行寫在 `removed_v2_1.csv`。

### 數

| | v2 | v2.1 |
|---|---:|---:|
| 鏈數 | 65 | **{n_themes}** |
| 成員行數 | 347 | **{n_rows}** |
| 不重覆公司數 | 343 | **{n_cos}** |
| 出隊行數 | 23 | **{n_removed}** |
| 本票新抓年報 | — | **0 份**(MSFT / ORCL / COP 的佐證全部在 `data/sec/10k_text` 快取內) |

`chain_membership_v2_1.csv` 比 v2 多三個欄:`v21_change`(這一行在 v2.1 改了什麼)、
`switch_date_basis`(轉向日的依據)、`switch_evidence`(佐證原文與 accession)。沒有改動的行三欄留空。
`removed_v2_1.csv` 多三個欄:`v21_review`(本票的覆核判詞)、`switch_date`、`switch_evidence`。

### 本票沒有做的

1. **同一類前視問題在 v2 其他地方仍然存在,本票按票面沒有動。** 最明顯兩處:
   HOOD 在 `crypto_exchange` 的 `valid_from` 仍是 2022-01-01(它 2022–2023 年還是散戶券商);
   `ai_hpc_hosting` 那四家(CORZ / IREN / WULF / CIFR)由 `crypto_mining` 轉去 AI 託管是 2024 年起的事,
   但它們的 `valid_from` 同樣是 2022 年初。要一併按換鏈日期處理的話,是另一張票。
2. 純度判斷仍然全屬人手,**沒有任何統計量度背書**;本票是改表票,不出成績。
3. `valid_from` 近似的比例沒有改善(本票只精確化了兩行,其中一行還是近似)。

---

"""
    section = section.format(
        n_themes=n_themes, n_rows=n_rows, n_cos=n_cos, n_removed=len(removed_rows)
    )

    # 只動標題那兩行 + 插一節,其餘一字不改
    old_h1 = u"# 鏈層人手表 v2 —— 純度版(KARST-161 交審稿)"
    new_h1 = u"# 鏈層人手表 v2.1 —— 純度版 + 換鏈日期(KARST-168)"
    assert old_h1 in text
    text = text.replace(old_h1, new_h1, 1)

    anchor = u"## 出隊規則(v2 統一用這四條)"
    assert anchor in text
    text = text.replace(anchor, section.replace("\n", "\r\n") + anchor, 1)

    with io.open(OUT_STORIES, "w", encoding="utf-8", newline="") as f:
        f.write(text)


def main():
    mem, cols, changed = build_membership()
    removed, dropped = build_removed()
    build_stories(mem, changed, removed, dropped)

    print("membership v2.1: %d rows, %d themes, %d companies"
          % (len(mem), len(set(r["theme"] for r in mem)), len(set(r["ticker"] for r in mem))))
    print("removed v2.1: %d rows (dropped from removed: %s)" % (len(removed), dropped))
    for c in changed:
        print("  changed:", c)


if __name__ == "__main__":
    main()
