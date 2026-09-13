import csv, io, sys

h = ['event_id','ticker','cik','signal_date','improvement_text','n_drivers','top_driver_type',
     'top_driver_share_lo','top_driver_share_hi','persistence_overall','p_continue',
     'pred_g2_point','pred_g2_lo','pred_g2_hi','pred_g4_point','pred_g4_lo','pred_g4_hi',
     'supply_catchup','supply_timing','tags','lifecycle_stage','stop_event_1_date','stop_event_2_date',
     'premise','falsify_1','biggest_unknown','unknowns_count','contamination_note']

r = ['E024','CPRI','0001530721','2017-11-06',
     '總收入 1146.6 百萬美元按年 +5.37% 由上一季 -3.59% 轉升;同店可比銷售 -1.8%;增長主要來自 56 間淨新店與歐亞電商;毛利率 60.2% 對 59.2%;其後兩季總收入增速按指引主要來自 Jimmy Choo 收購增量',
     '5','數量',0.45,0.65,'中',0.45,
     0.033,0.000,0.080,0.050,0.010,0.110,
     '不適用','—','','飽和','2018-02-13','2018-05-30',
     'Jimmy Choo 自 2017-11-01 起按期併表且無重大一次性整合成本;MK 品牌可比銷售跌幅不擴大到高雙位數;匯率不逆轉',
     '其後兩季平均按年總收入增速 < 0% 即論點失效(門檻 4.29%)',
     '2018 財年 Q4 的收入(公司只給 Q3 與全年;以殘差推算約 11.2 億美元)',
     7,
     '知道該公司其後改名並再做大型收購及一次合併被監管否決(屬 T1 後)已隔離;偏淡的總判無法完全排除受此記憶影響;共識一律查不到']

assert len(h) == 28, len(h)
assert len(r) == 28, len(r)
for v in r:
    s = str(v)
    assert '\n' not in s and ',' not in s and '"' not in s, repr(s)

with open(r'C:/projects/Karst/research/2026-09-methodology/2026-09-12-②第一次考試/B/ds/rows/E024.csv',
          'w', encoding='utf-8', newline='') as f:
    w = csv.writer(f, quoting=csv.QUOTE_ALL)
    w.writerow(h)
    w.writerow(r)

with open(r'C:/projects/Karst/research/2026-09-methodology/2026-09-12-②第一次考試/B/ds/rows/E024.csv',
          'r', encoding='utf-8', newline='') as f:
    rows = list(csv.reader(f))
print('rows=', len(rows), 'cols=', [len(x) for x in rows])
print('header_ok=', rows[0] == h)
print('persistence=', rows[1][9], 'p=', rows[1][10], 'g2=', rows[1][11], rows[1][12], rows[1][13])
