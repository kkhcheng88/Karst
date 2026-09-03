# -*- coding: utf-8 -*-
"""KARST-169 —— 鏈位表 v2.2:ai_hpc_hosting 四家按換鏈日期改記,HOOD 入位日核實

D-152 ② 收下 D-151 ② 的做法:主業轉向的成員不整家出隊,改記換鏈日期——
舊鏈一行 valid_to = 轉向日、新鏈一行 valid_from = 同日。v2.1 已對 MSFT / ORCL 做過,
本票對 ai_hpc_hosting 四家(CORZ / IREN / WULF / CIFR)做同一件事,並核實 HOOD 在
crypto_exchange 的入位日。

本腳本只讀 v2.1 的三個檔,不寫回;輸出三個新檔:
  chain_membership_v2_2.csv (UTF-8 BOM)
  removed_v2_2.csv          (UTF-8 BOM)
  chain_stories_v2_2.md     (UTF-8)

轉向日的判準(跑數前寫死,見文件「怎樣定轉向日」一節):
  取**首次公開宣佈 AI/HPC 客戶合約的當日**。理由:那一日全世界都看得到,
  是事前可得的;而只宣佈買 GPU / 宣佈策略、未有客戶合約的,不算轉向。

跑法: set PYTHONUTF8=1 && python build_v2_2.py
"""

import csv
import io
import os

HERE = os.path.dirname(os.path.abspath(__file__))

SRC_MEMBERSHIP = os.path.join(HERE, "chain_membership_v2_1.csv")
SRC_REMOVED = os.path.join(HERE, "removed_v2_1.csv")
SRC_STORIES = os.path.join(HERE, "chain_stories_v2_1.md")

OUT_MEMBERSHIP = os.path.join(HERE, "chain_membership_v2_2.csv")
OUT_REMOVED = os.path.join(HERE, "removed_v2_2.csv")
OUT_STORIES = os.path.join(HERE, "chain_stories_v2_2.md")

NEW_COLS = ["v22_change", "v22_switch_basis", "v22_switch_evidence"]

# ---------------------------------------------------------------------------
# 一、四家礦商的轉向日與佐證
# ---------------------------------------------------------------------------

SWITCH = {
    "CORZ": {
        "old_theme": "crypto_mining",
        "new_theme": "ai_hpc_hosting",
        "switch_date": "2024-03-06",
        "old_valid_from": "2022-01-20",
        "old_valid_from_basis": "精確(Core Scientific 併殼上市完成日,沿用 v2 該行原值)",
        "approx": False,
        "basis": (
            "精確到日,而且事前可得:2024-03-06 公司發新聞稿公佈首份 AI/HPC 託管合約"
            "(向 CoreWeave 供應最多 16MW 資料中心機位)。同日 8-K(Item 7.01)把新聞稿列為附件,"
            "當日收市前全世界都看得到,不需要等年報。"
        ),
        "evidence": (
            "8-K 申報日 2024-03-06(accession 0001628280-24-009396,CIK 1839341,Item 7.01)"
            "原文:「On March 6, 2024, the Company issued a press release announcing an agreement "
            "to provide hosting services to CoreWeave.」"
            "所附新聞稿原文:「Core Scientific ... and CoreWeave, the leading specialized GPU cloud "
            "provider, today announced a multi-year contract for Core Scientific to supply up to "
            "16 MW of data center infrastructure to CoreWeave.」"
            "另有年報覆核:FY2023 10-K(0001628280-24-010682,申報日 2024-03-13)寫"
            "「On March 6, 2024, the Company announced a multi-year contract for Core Scientific to "
            "supply up to 16 MW of data center infrastructure to CoreWeave, Inc.」;"
            "邊界佐證:上一份 FY2022 10-K(0001628280-23-010454,申報日 2023-04-04)"
            "全文 CoreWeave 出現 0 次。"
        ),
    },
    "IREN": {
        "old_theme": "crypto_mining",
        "new_theme": "ai_hpc_hosting",
        "switch_date": "2024-02-08",
        "old_valid_from": "2022-01-01",
        "old_valid_from_basis": "近似(2022-01-01 前已上市且業務未變,沿用 v0 走廊起點)",
        "approx": False,
        "basis": (
            "精確到日,而且事前可得:2024-02-08 公司公佈與 AI 公司 poolside AI SAS 的 GPU 雲服務"
            "正式開始,是它第一份 AI 客戶合約。要留意:更早的 2023-08-29 只是宣佈買 248 顆 "
            "NVIDIA H100「target generative AI」,同一份新聞稿明文「Core business remains Bitcoin "
            "mining」,屬意向公告不是客戶合約,按本票判準不取。"
        ),
        "evidence": (
            "6-K 申報日 2024-02-08(accession 0001140361-24-006216,CIK 1878848)原文:"
            "「On February 8, 2024, Iris Energy Limited (the “Company”) released a press release "
            "announcing the commencement of GPU cloud service with leading AI company, Poolside AI SAS.」"
            "所附新聞稿:「Iris Energy has executed a cloud service agreement with poolside for 248 "
            "NVIDIA H100 GPUs.」"
            "年報覆核:FY2024 20-F(0001628280-24-038677,申報日 2024-08-28)寫"
            "「In August 2023 we announced the purchase of 248 NVIDIA H100 GPUs to target generative AI. "
            "In February 2024, we announced a three-month GPU cloud service agreement with Poolside SAS AI ...」;"
            "FY2025 10-K(0001878848-25-000063)另寫「AI Cloud Services, launched in 2024」。"
        ),
    },
    "WULF": {
        "old_theme": "crypto_mining",
        "new_theme": "ai_hpc_hosting",
        "switch_date": "2024-12-23",
        "old_valid_from": "2022-01-01",
        "old_valid_from_basis": "近似(2022-01-01 前已上市且業務未變,沿用 v0 走廊起點)",
        "approx": False,
        "basis": (
            "精確到日,而且事前可得:2024-12-23 公司 8-K 公佈與 Core42(G42 旗下)簽長期資料中心租約,"
            "在 Lake Mariner 交付逾 70MW 機位,是它第一份 AI/HPC 託管合約。"
            "更早的 2024 年 3 月只是撥出 2MW 做 GPU 試點——FY2023 10-K 自己寫"
            "「During the years ended December 31, 2023 and 2022, the Company only operated bitcoin "
            "mining facilities」,按本票判準不取。"
        ),
        "evidence": (
            "8-K 申報日 2024-12-23(accession 0000950142-24-002980,CIK 1083301,Item 8.01)原文:"
            "「TeraWulf ... entered into long-term data center lease agreements (the “Lease Agreements”) "
            "with Core42, a G42 company specializing in sovereign cloud, AI infrastructure, and digital "
            "services. Under the Lease Agreements, TeraWulf will deliver over 70 megawatts (“MW”) of "
            "turn-key data center infrastructure to host Core42’s deployment at the Lake Mariner facility.」"
            "年報覆核:FY2024 10-K(0001083301-25-000018,申報日 2025-03-03)寫"
            "「on December 23, 2024, when we entered into long-term data center lease agreements with "
            "Core42 Holding US LLC」;"
            "邊界佐證:FY2023 10-K(0001083301-24-000072,申報日 2024-03-20)明文"
            "「During the years ended December 31, 2023 and 2022, the Company only operated bitcoin "
            "mining facilities」,全文 Core42 出現 0 次。"
        ),
    },
    "CIFR": {
        "old_theme": "crypto_mining",
        "new_theme": "ai_hpc_hosting",
        "switch_date": "2025-09-25",
        "old_valid_from": "2022-01-01",
        "old_valid_from_basis": "近似(2022-01-01 前已上市且業務未變,沿用 v0 走廊起點)",
        "approx": False,
        "basis": (
            "精確到日,而且事前可得:2025-09-25 公司 8-K 公佈子公司 Cipher Barber Lake 與 Fluidstack "
            "簽十年期資料中心租約、由 Google 作後盾(租約簽署日 2025-09-24,公佈日 2025-09-25),"
            "是它第一份 AI/HPC 託管合約。"
            "四家之中它最遲:FY2024 10-K(2025-02-25 申報)講 HPC 講了 73 次,但全部是"
            "「potential HPC tenants」——有場地、無租客,按本票判準不算轉向。"
        ),
        "evidence": (
            "8-K 申報日 2025-09-25(accession 0000950103-25-012168,CIK 1819989,Item 1.01)原文:"
            "「... announced that its wholly owned indirect subsidiary Cipher Barber Lake LLC "
            "(“Cipher Barber Lake”) had entered into a Datacenter Lease (the “Fluidstack Lease”) with "
            "Fluidstack USA II Inc. ... Fluidstack’s obligations to pay rent under the Fluidstack Lease "
            "begin on the commencement date of the lease and will continue for a 10-year term.」"
            "同一份:「On September 24, 2025, Cipher Barber Lake entered into a Recognition Agreement ... "
            "among Cipher Barber Lake, Fluidstack and Google LLC ... pursuant to which Google has agreed "
            "to backstop ... certain obligations of Fluidstack under the Fluidstack Lease.」"
            "年報覆核:FY2025 10-K(0001819989-26-000009,申報日 2026-02-24)重述同一日期;"
            "邊界佐證:FY2024 10-K(0001819989-25-000005,申報日 2025-02-25)只寫"
            "「our increasing focus on diversification into constructing and operating data centers for "
            "HPC companies」與「potential HPC tenants」,未有任何 HPC 租客。"
        ),
    },
}

# 新鏈行的 note(換鏈之後)
NEW_NOTE = {
    "CORZ": "礦場轉 AI 託管的代表案例(v2.2:%s 起由 crypto_mining 轉入本鏈)",
    "IREN": "礦場加 AI 雲,同一條電力與幣價方程式(v2.2:%s 起由 crypto_mining 轉入本鏈)",
    "WULF": "核電供電礦場,同樣轉型 AI 託管(v2.2:%s 起由 crypto_mining 轉入本鏈)",
    "CIFR": "同上,並已簽 AI 資料中心租約(v2.2:%s 起由 crypto_mining 轉入本鏈)",
}

# 補回舊鏈(crypto_mining)那四行時要填的共同欄位,取自該鏈現有成員行
OLD_THEME = "crypto_mining"

# ---------------------------------------------------------------------------
# 二、HOOD 在 crypto_exchange 的入位日核實(結論:維持 2022-01-01,但兩格內容要改)
# ---------------------------------------------------------------------------

HOOD_VERIFY = {
    "valid_from": "2022-01-01",  # 不改
    "valid_from_basis": (
        "已核實(v2.2,KARST-169):走廊起點之前 HOOD 已在做加密交易並單獨披露該收入線,"
        "所以 2022-01-01 不是前視日期,是走廊起點本身。"
    ),
    "purity": (
        "同時是零售券商。加密交易收入由第一份年報(FY2021)起已單獨披露,"
        "但**從來不是交易收入的主體**:占總淨收入 2021 年 23%、2022 年 15%、2023 年 7%、"
        "2024 年 21%、2025 年 20%,而期權那一線同期是 38% / 36% / 27% / 26% / 25%,每一年都比加密大。"
        "所以它跟本鏈共同敘事的貼合度是四成上下、而且隨幣市週期上落,不是一條穩定的鏈位。"
    ),
    "purity_basis": (
        "更正 v2/v2.1 的原句「2024 年起加密交易佔交易收入主體,按規則 d 只入本鏈」——"
        "年報數字不支持:2024 年加密占總淨收入 21%,期權占 26%,期權仍然較大。"
    ),
    "evidence": (
        "HOOD 各年 10-K 的 transaction-based revenues 分項(占總淨收入百分比表,原文格式"
        "「Options 38% 36% 27% / Cryptocurrencies 23% 15% 7% / Equities 16% 9% 6%」):"
        "FY2021 10-K(accession 0001783879-22-000044,申報日 2022-02-24)給 2019/2020/2021;"
        "FY2023 10-K(0001783879-24-000054,申報日 2024-02-27)給 2021/2022/2023;"
        "FY2024 10-K(0001783879-25-000049,申報日 2025-02-18)給 2022/2023/2024,"
        "當中 2024 年 Cryptocurrencies 626(百萬美元)對 Options 760;"
        "FY2025 10-K(0001783879-26-000023,申報日 2026-02-18)給 2024/2025,"
        "Cryptocurrencies 901 對 Options 1,123。"
    ),
}

# ---------------------------------------------------------------------------
# 三、兩條鏈的逐鏈純度句(purity_note)連帶改動
# ---------------------------------------------------------------------------

PURITY_NOTE_FIX = {
    "crypto_mining": (
        "共同敘事=「幣價 × 算力份額 ÷ 電價」。"
        "v2 把已轉型 AI 託管的四家(CORZ / IREN / WULF / CIFR)整家拆去 ai_hpc_hosting;"
        "v2.2 改記換鏈日期——四家在各自轉向日之前仍屬本鏈,之後才轉入 ai_hpc_hosting。"
        "最邊緣是 HUT(2025 年分拆 ABTC 之後,股價一半跟自己的電力平台估值走)。"
    ),
    "ai_hpc_hosting": (
        "共同敘事=「把通電機位租給 AI 雲客戶」。這是 v2 由 crypto_mining 按規則 d 拆出來的。"
        "v2.2 把入位日由 2022 年初改為各自首份 AI/HPC 客戶合約的公佈日"
        "(CORZ 2024-03-06、IREN 2024-02-08、WULF 2024-12-23、CIFR 2025-09-25),"
        "轉向日之前它們仍在 crypto_mining。CRWV 自有 GPU、資本模式不同(規則 b),不收。"
        "**本鏈仍有一處同類前視問題未處理**:APLD 的 valid_from 仍是 2022-01-01,本票票面沒有涵蓋。"
    ),
    "crypto_exchange": (
        "共同敘事=「加密交易活躍度」。美股同位置只有兩家,結構性不足;"
        "CRCL(收入是儲備利息,由聯儲利率決定)與 GLXY(股價自 2025 年由 Helios 資料中心租約主導)"
        "按規則 b/d 不收。"
        "v2.2 核實 HOOD 的入位日:2022-01-01 維持(走廊起點之前它已在做加密交易),"
        "但更正一句錯的判詞——加密交易從來不是 HOOD 交易收入的主體,每一年都細過期權。"
    ),
}


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
    new_cols = list(cols) + NEW_COLS

    # 該鏈的共同欄位樣板(由現有成員行取)
    cm_tpl = [r for r in rows if r["theme"] == OLD_THEME][0]

    out = []
    changed = []          # (ticker, theme, 一句)
    touched_rows = set()  # 逐行對帳用:v2.1 的哪些行被改過
    for i, r in enumerate(rows):
        r = dict(r)
        for c in NEW_COLS:
            r[c] = ""
        tk, th = r["ticker"], r["theme"]

        if th in PURITY_NOTE_FIX:
            r["purity_note"] = PURITY_NOTE_FIX[th]

        if tk in SWITCH and th == SWITCH[tk]["new_theme"]:
            s = SWITCH[tk]
            old_vf = r["valid_from"]
            r["valid_from"] = s["switch_date"]
            r["valid_from_basis"] = "換鏈日(v2.2,KARST-169):首份 AI/HPC 客戶合約公佈日,精確到日、事前可得"
            r["note"] = NEW_NOTE[tk] % s["switch_date"]
            r["v22_change"] = "新鏈行:valid_from %s → %s" % (old_vf, s["switch_date"])
            r["v22_switch_basis"] = s["basis"]
            r["v22_switch_evidence"] = s["evidence"]
            changed.append((tk, th, r["v22_change"]))
            touched_rows.add(i)

        if tk == "HOOD" and th == "crypto_exchange":
            r["valid_from"] = HOOD_VERIFY["valid_from"]
            r["valid_from_basis"] = HOOD_VERIFY["valid_from_basis"]
            r["purity"] = HOOD_VERIFY["purity"]
            r["v22_change"] = "入位日核實:valid_from 2022-01-01 維持不變;purity 判詞更正"
            r["v22_switch_basis"] = HOOD_VERIFY["purity_basis"]
            r["v22_switch_evidence"] = HOOD_VERIFY["evidence"]
            changed.append((tk, th, r["v22_change"]))
            touched_rows.add(i)

        out.append(r)

    # 補回 crypto_mining 那四行
    for tk in ("CORZ", "IREN", "WULF", "CIFR"):
        s = SWITCH[tk]
        src = [r for r in out if r["ticker"] == tk and r["theme"] == s["new_theme"]][0]
        row = {c: "" for c in new_cols}
        row.update({
            "theme": OLD_THEME,
            "ticker": tk,
            "valid_from": s["old_valid_from"],
            "valid_to": s["switch_date"],
            "role": "core",
            "note": "v2.2 補回:v2 曾按規則 d 整家出隊,現改記為換鏈——本鏈成員至 %s 為止" % s["switch_date"],
            "story": cm_tpl["story"],
            "position": cm_tpl["position"],
            "purity": "轉向日之前:股價跟「幣價 × 算力份額 ÷ 電價」這條敘事走,%s 起轉入 ai_hpc_hosting" % s["switch_date"],
            "purity_note": PURITY_NOTE_FIX[OLD_THEME],
            "source_url": src["source_url"],
            "evidence_10k": src["evidence_10k"],
            "added_by": "v2.2",
            "valid_from_basis": s["old_valid_from_basis"],
            "filer_type": src["filer_type"],
            "src_theme_v1": src["src_theme_v1"],
            "v22_change": "舊鏈行:v2 已刪,v2.2 補回,valid_to=%s" % s["switch_date"],
            "v22_switch_basis": s["basis"],
            "v22_switch_evidence": s["evidence"],
        })
        idx = max(i for i, r in enumerate(out) if r["theme"] == OLD_THEME)
        out.insert(idx + 1, row)
        changed.append((tk, OLD_THEME, row["v22_change"]))

    write_csv_bom(OUT_MEMBERSHIP, new_cols, out)
    return rows, cols, out, new_cols, changed


def reconcile(src_rows, src_cols, out_rows):
    """逐行對帳:v2.1 每一行不是被原樣承接,就是在改動清單上;否則報錯。"""
    allowed_changed_cells = {
        # (ticker, theme) -> 准許改的欄位
        ("CORZ", "ai_hpc_hosting"): {"valid_from", "valid_from_basis", "note", "purity_note"},
        ("IREN", "ai_hpc_hosting"): {"valid_from", "valid_from_basis", "note", "purity_note"},
        ("WULF", "ai_hpc_hosting"): {"valid_from", "valid_from_basis", "note", "purity_note"},
        ("CIFR", "ai_hpc_hosting"): {"valid_from", "valid_from_basis", "note", "purity_note"},
        ("HOOD", "crypto_exchange"): {"valid_from_basis", "purity", "purity_note"},
    }
    # 承接行按原次序逐行對(v2.2 只插入新行,沒有重排),避免 (ticker, theme) 撞鍵——
    # v2.1 本身有一組重複鍵(WDC 在 memory 出現兩行,v2 之前已存在,本票不動)。
    carried = [r for r in out_rows if r.get("added_by") != "v2.2"]
    problems = []
    if len(carried) != len(src_rows):
        problems.append("承接行數 %d ≠ v2.1 行數 %d" % (len(carried), len(src_rows)))
        return {"same": 0, "purity_note_only": 0, "changed": 0,
                "added": len(out_rows) - len(carried), "problems": problems}

    n_same, n_note_only, n_changed = 0, 0, 0
    for r, o in zip(src_rows, carried):
        key = (r["ticker"], r["theme"])
        if (o["ticker"], o["theme"]) != key:
            problems.append("次序錯位:v2.1 %s 對上 v2.2 %s" % (str(key), str((o["ticker"], o["theme"]))))
            continue
        diff = {c for c in src_cols if (r.get(c) or "") != (o.get(c) or "")}
        if not diff:
            n_same += 1
            continue
        allowed = allowed_changed_cells.get(key, set())
        if diff <= {"purity_note"} and r["theme"] in PURITY_NOTE_FIX:
            n_note_only += 1
            continue
        if diff <= allowed:
            n_changed += 1
            continue
        problems.append("v2.1 行 %s 改了不准改的欄位:%s" % (str(key), sorted(diff - allowed)))

    added = [r for r in out_rows if r.get("added_by") == "v2.2"]
    return {"same": n_same, "purity_note_only": n_note_only, "changed": n_changed,
            "added": len(added), "problems": problems}


def build_removed():
    rows, cols = read_csv_bom(SRC_REMOVED)
    new_cols = list(cols) + ["v22_review"]
    out = []
    for r in rows:
        r = dict(r)
        if r["ticker"] == "HOOD":
            r["v22_review"] = (
                "v2.2 沒有改本行的出隊結論(HOOD 仍然不入 fintech)。"
                "本票另外核實了它在 crypto_exchange 的入位日:2022-01-01 維持,"
                "但更正了 v2 一句錯判詞——加密交易從來不是它交易收入的主體,每一年都細過期權。"
                "詳見 chain_membership_v2_2.csv 該行與 chain_stories_v2_2.md「v2.2 變更」一節。"
            )
        else:
            r["v22_review"] = "v2.2 未覆核本行;內容與 removed_v2_1.csv 逐格相同(本票只處理四家礦商與 HOOD 的入位日)。"
        out.append(r)
    write_csv_bom(OUT_REMOVED, new_cols, out)
    return rows, out


def build_stories(mem_rows, rec):
    with io.open(SRC_STORIES, "r", encoding="utf-8", newline="") as f:
        text = f.read()

    n_rows = len(mem_rows)
    n_themes = len(set(r["theme"] for r in mem_rows))
    n_cos = len(set(r["ticker"] for r in mem_rows))

    section = u"""## v2.2 變更(KARST-169,2026-09-03)

> **本文件 = `chain_stories_v2_1.md` 全文,只加了本節。** v0 / v1 / v2 / v2.1 的檔一字未改,仍在原處。
> 誠實聲明沿用下面那四項,**再加一項**:轉向日雖然全部取自公佈當日的申報,
> 但「哪一家要查轉向日」這個問題本身,是由今日回望才問得出來的,整張表仍然帶事後眼光。
> **凡本文件其餘部分與本節衝突,以本節與 `chain_membership_v2_2.csv` 為準。**

### 改了什麼、為什麼

v2.1 把 MSFT / ORCL 由「整家出隊」改記為換鏈日期之後,同一類前視問題還剩兩處沒有處理,
`chain_stories_v2_1.md` 自己列作未做事項:`ai_hpc_hosting` 那四家(CORZ / IREN / WULF / CIFR)
2024 年之後才轉去 AI 託管,`valid_from` 卻仍然是 2022 年初;HOOD 在 `crypto_exchange` 的
`valid_from` 同樣是 2022-01-01。本票把這兩處補上。

### 怎樣定轉向日(判準在查證之前寫死)

**取首次公開宣佈 AI/HPC 客戶合約的當日。** 兩個理由:

1. **事前可得。** 公佈當日 8-K / 6-K 連新聞稿一齊出,收市前全世界都看得到,不需要等年報。
   這一點與 v2.1 的 ORCL 那一格不同——ORCL 的日期是由後來的年報倒推的,本票四家全部不是。
2. **只宣佈買機、只宣佈策略,不算。** 分界線是「有沒有客戶合約」:
   IREN 2023-08-29 宣佈買 248 顆 H100「target generative AI」,同一份新聞稿寫住
   「Core business remains Bitcoin mining」;WULF 2024 年初撥 2MW 做 GPU 試點,
   FY2023 10-K 自己寫「During the years ended December 31, 2023 and 2022, the Company only
   operated bitcoin mining facilities」;CIFR 到 FY2024 10-K 講 HPC 講了 73 次,
   全部是「potential HPC tenants」,有場地無租客。這三處按本判準一律不取。

### 改記換鏈日期的:四家、八行

| 公司 | 舊鏈 `crypto_mining`(valid_to) | 新鏈 `ai_hpc_hosting`(valid_from) | 轉向日 | 準確度 | 佐證 |
|---|---|---|---|---|---|
| CORZ | 2022-01-20 → **2024-03-06** | **2024-03-06** → 現役 | 2024-03-06 | 精確到日、事前可得 | 8-K 2024-03-06(Item 7.01)連新聞稿:「a multi-year contract for Core Scientific to supply up to 16 MW of data center infrastructure to CoreWeave」;FY2022 10-K 全文 CoreWeave 0 次 |
| IREN | 2022-01-01 → **2024-02-08** | **2024-02-08** → 現役 | 2024-02-08 | 精確到日、事前可得 | 6-K 2024-02-08:「commencement of GPU cloud service with leading AI company, Poolside AI SAS」、「executed a cloud service agreement with poolside for 248 NVIDIA H100 GPUs」 |
| WULF | 2022-01-01 → **2024-12-23** | **2024-12-23** → 現役 | 2024-12-23 | 精確到日、事前可得 | 8-K 2024-12-23(Item 8.01):「entered into long-term data center lease agreements ... with Core42 ... deliver over 70 megawatts of turn-key data center infrastructure」;FY2023 10-K 明文當時只做挖礦 |
| CIFR | 2022-01-01 → **2025-09-25** | **2025-09-25** → 現役 | 2025-09-25 | 精確到日、事前可得 | 8-K 2025-09-25(Item 1.01):Cipher Barber Lake 與 Fluidstack 簽十年期 Datacenter Lease、Google 作後盾;FY2024 10-K 只有「potential HPC tenants」 |

四家全部**不是近似**,這是與 v2.1 那兩家最大的分別。

### HOOD 的入位日:核實過,日期不改,判詞要改

`crypto_exchange` 的 `valid_from` 維持 **2022-01-01**,理由:走廊起點之前 HOOD 已經在做加密交易,
而且由第一份年報(FY2021)起就把加密交易收入單獨列一行,所以這個日期不是前視,是走廊起點本身。

但核實過程查到 v2 寫錯了一句。v2 / v2.1 的 `purity` 欄寫住「2024 年起加密交易佔交易收入主體」,
**年報數字不支持**。加密交易收入占 HOOD 總淨收入的比例,逐年是:

| | 2021 | 2022 | 2023 | 2024 | 2025 |
|---|---:|---:|---:|---:|---:|
| 加密交易 | 23% | 15% | 7% | 21% | 20% |
| 期權 | 38% | 36% | 27% | 26% | 25% |
| 股票 | 16% | 9% | 6% | 6% | 7% |

**每一年期權都比加密大**,加密從來沒有做過主體;而且它由 2021 的 23% 跌到 2023 的 7%、
再升回 2024 的 21%,是隨幣市週期上落,不是一次轉向。那一句已改寫,原句與更正理由寫在
`v22_switch_basis` 欄。

這一格順帶答了一個更大的問題:**HOOD 本身是不是 `crypto_exchange` 這一層的乾淨成員,值得懷疑。**
本票按票面只核實日期、不動成員資格;不過 `crypto_exchange` 名冊只有兩家,本來已經在
「名冊不足五家」那 16 條鏈之內,量度上不入判準。

### 連帶改動:三條鏈的逐鏈純度句

`purity_note` 是逐鏈共用的一句,以下三條鏈的那一句在 v2.2 已不成立,所以改寫了。
這是本票唯一超出「四家 + HOOD」的改動,在此明列:

- `crypto_mining` —— 原句寫四家已被拆走,現在要寫成「轉向日之前仍屬本鏈」。
- `ai_hpc_hosting` —— 補上四個轉向日,並明寫 APLD 的同類問題**未處理**。
- `crypto_exchange` —— 補上 HOOD 入位日的核實結論。

### 逐行對帳結果

`build_v2_2.py` 對 `chain_membership_v2_1.csv` 的 {n_src} 行逐格核對,規則是:
每一行不是被原樣承接,就是在准許改動的清單上,否則報錯。

| | 行數 |
|---|---:|
| 逐格完全相同 | {same} |
| 只改了逐鏈共用的 `purity_note` | {note_only} |
| 在准許改動清單上(四家新鏈行 + HOOD 一行) | {changed} |
| v2.2 新增(補回 `crypto_mining` 四行) | {added} |
| **對帳報錯** | **{nprob}** |

### 數

| | v2.1 | v2.2 |
|---|---:|---:|
| 鏈數 | 65 | **{n_themes}** |
| 成員行數 | 349 | **{n_rows}** |
| 不重覆公司數 | 343 | **{n_cos}** |
| 本票新抓年報 | — | **10 份**(CORZ 3、WULF 3、CIFR 3、IREN 1;`fetchedBy: KARST-169`) |
| 本票新抓公告類申報(8-K / 6-K / 20-F,不入年報快取) | — | 14 份 |

`chain_membership_v2_2.csv` 比 v2.1 多三個欄:`v22_change`、`v22_switch_basis`、`v22_switch_evidence`;
沒有改動的行三欄留空。`removed_v2_2.csv` 多一個欄 `v22_review`,其餘 21 行與 v2.1 逐格相同。

### 本票沒有做的

1. **`ai_hpc_hosting` 的 APLD 仍是 2022-01-01。** 它同樣是由託管業務轉去 AI 的公司,
   同一類前視問題,但票面只點名四家,本票沒有動。要處理是另一張票。
2. `valid_from` 近似的整體比例沒有實質改善(本票精確化了四行,另外補回的四行沿用舊鏈原有的近似日)。
3. 純度判斷仍然全屬人手,**沒有任何統計量度背書**;本票是改表票,不出成績。
4. **HOOD 的成員資格未覆核**——只核實日期、更正判詞,沒有按四條出隊規則重判。

---

"""
    section = section.format(
        n_themes=n_themes, n_rows=n_rows, n_cos=n_cos,
        n_src=rec["n_src"], same=rec["same"], note_only=rec["purity_note_only"],
        changed=rec["changed"], added=rec["added"], nprob=len(rec["problems"]),
    )

    old_h1 = u"# 鏈層人手表 v2.1 —— 純度版 + 換鏈日期(KARST-168)"
    new_h1 = u"# 鏈層人手表 v2.2 —— 純度版 + 換鏈日期(KARST-169)"
    assert old_h1 in text
    text = text.replace(old_h1, new_h1, 1)

    anchor = u"## v2.1 變更(KARST-168,2026-09-03)"
    assert anchor in text
    text = text.replace(anchor, section.replace("\n", "\r\n") + anchor, 1)

    with io.open(OUT_STORIES, "w", encoding="utf-8", newline="") as f:
        f.write(text)


def main():
    src_rows, src_cols, out_rows, _cols, changed = build_membership()
    rec = reconcile(src_rows, src_cols, out_rows)
    rec["n_src"] = len(src_rows)
    build_removed()
    build_stories(out_rows, rec)

    print("membership v2.2: %d rows, %d themes, %d companies"
          % (len(out_rows), len(set(r["theme"] for r in out_rows)),
             len(set(r["ticker"] for r in out_rows))))
    print("對帳:相同 %d / 只改 purity_note %d / 准許改動 %d / 新增 %d / 報錯 %d"
          % (rec["same"], rec["purity_note_only"], rec["changed"], rec["added"], len(rec["problems"])))
    for p in rec["problems"]:
        print("  !!", p)
    for c in changed:
        print("  changed:", c)
    if rec["problems"]:
        raise SystemExit("對帳未過")


if __name__ == "__main__":
    main()
