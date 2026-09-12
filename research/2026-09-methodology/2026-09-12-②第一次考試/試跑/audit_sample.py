# -*- coding: utf-8 -*-
"""KARST-228 抽樣:每張卡抽出「帶出處的判斷句」清單並以種子 20260913 抽 3 條。

定義(寫進核查檔):
- 判斷句單元 = 卡內【第一步】至【第八步】之間的非標題、非空行(一段一行的散文段落,或一條表格列)。
  第一/二/三/四/五/六/七/八步以外的段落(contamination_note、執行紀錄)不列入抽樣池。
- 「帶出處」= 該單元含至少一個引用標記:accession 編號(10 位-2 位-6 位 或 18 位連寫)、
  申報/文件類型字(10-K / 10-Q / 8-K / 20-F / 6-K / EX-99.1 / Exhibit 99.1 / peer10k)、
  包內欄位名(如 6_價格狀態、4_財務數列、g0_signal_q_yoy、improvement_type_機械、masking_check)、
  或「出處」二字。
- 編號 = 該卡內符合上述定義的單元,按檔案行號升序 1..N。
- 抽樣 = random.Random(20260913).sample(range(1,N+1), 3),若非 3 條則取全部。
"""
import io, os, random, re, json

BASE = r"C:/projects/Karst/research/2026-09-methodology/2026-09-12-②第一次考試"
PAO = os.path.join(BASE, r"試跑")
EVENTS = ["E001", "E009", "E017", "E025", "E033", "E041", "E049", "E057", "E065", "E073"]
SEED = 20260913
OUT = os.path.join(PAO, "_audit_sample.txt")

ACC18 = re.compile(r"\b\d{10}-?\d{2}-?\d{6}\b")
DOCO = re.compile(r"(10-K|10-Q|8-K|20-F|6-K|EX-99\.1|Exhibit 99\.1|peer10k|投資者簡報|電話會)", re.I)
FIELDO = re.compile(r"(6_價格狀態|4_財務數列|5_同業|7_共識|2_觸發資料|3_截止前文件|1_事件識別|masking_check|g0_signal_q_yoy|improvement_type|reaction_day|packets/|edgar_cache|Exhibit 99\.2|10-Q|10-K)")
MARK = re.compile(r"(出處|已核|推算|查不到)")

def units_of(path):
    txt = io.open(path, encoding="utf-8").read().split("\n")
    out = []
    inscope = False
    for i, ln in enumerate(txt, 1):
        s = ln.strip()
        if re.match(r"^#*\s*`?\s*contamination_note", s, re.I):
            inscope = False
            continue
        if s.startswith("#"):
            if re.match(r"^#+\s*【第[一二三四五六七八]步", s):
                inscope = True
            elif re.match(r"^#+\s*(執行紀錄|判不出的事|來源|附錄|口徑警告|取證包重大缺陷)", s):
                inscope = False
            continue
        if not inscope:
            continue
        if not s or set(s) <= set("-—| :"):
            continue
        if ACC18.search(s) or DOCO.search(s) or FIELDO.search(s):
            out.append((i, s))
    return out

lines = []
for arm in ("ds", "opus"):
    for e in EVENTS:
        hits = [f for f in os.listdir(os.path.join(PAO, arm)) if f.startswith("卡-" + e + "-")]
        p = os.path.join(PAO, arm, hits[0])
        us = units_of(p)
        n = len(us)
        rng = random.Random(SEED)
        idx = sorted(rng.sample(range(1, n + 1), min(3, n)))
        lines.append("=" * 78)
        lines.append("ARM=%s EVENT=%s FILE=%s  N=%d  SAMPLED=%s" % (arm, e, hits[0], n, idx))
        for k in idx:
            ln, s = us[k - 1]
            lines.append("  --- #%d (card line %d) ---" % (k, ln))
            lines.append("  " + s[:900])
        # 全池編號概覽(只列編號與行號,方便核對編號制)
        lines.append("  [pool] " + "; ".join("%d@L%d" % (j + 1, u[0]) for j, u in enumerate(us)))
io.open(OUT, "w", encoding="utf-8").write("\n".join(lines))
print("wrote", OUT)
