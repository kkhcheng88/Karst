import csv, json, os, sys

COLS = ["event_id","ticker","cik","signal_date","improvement_text","n_drivers","top_driver_type",
        "top_driver_share_lo","top_driver_share_hi","persistence_overall","p_continue",
        "pred_g2_point","pred_g2_lo","pred_g2_hi","pred_g4_point","pred_g4_lo","pred_g4_hi",
        "supply_catchup","supply_timing","tags","lifecycle_stage","stop_event_1_date",
        "stop_event_2_date","premise","falsify_1","biggest_unknown","unknowns_count","contamination_note"]

eid = sys.argv[1]
base = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'rows')
spec = json.load(open(os.path.join(base, eid + '.spec.json'), encoding='utf-8'))
row = [spec.get(c, '') for c in COLS]
with open(os.path.join(base, eid + '.csv'), 'w', newline='', encoding='utf-8') as f:
    w = csv.writer(f, quoting=csv.QUOTE_ALL)
    w.writerow(COLS)
    w.writerow(row)
os.remove(os.path.join(base, eid + '.spec.json'))
print('wrote', eid + '.csv', len(COLS), 'cols')
