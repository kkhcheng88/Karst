import json, sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
eid = sys.argv[1]
base = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'A3', 'packets')
d = json.load(open(os.path.join(base, eid + '.json'), encoding='utf-8'))
q = d['4_財務數列']
print('KEYS', list(q.keys()))
print('g0', q.get('g0_signal_q_yoy'), 'prev', q.get('prev_q_yoy'), 'accel', q.get('accel_pp'))
for r in q['quarters']:
    ex = r.get('extra') or {}
    def g(k, ex=ex):
        v = ex.get(k)
        return v.get('value') if isinstance(v, dict) else v
    print(r['period_end'], 'rev', r.get('revenue'),
          '| inv', g('inventory'), 'ar', g('accounts_receivable'), 'rd', g('r_and_d'),
          'deferred', g('deferred_revenue'), 'backlog', g('backlog'), 'capex', g('capex'),
          'cash', g('cash_and_equivalents'), 'debt', g('total_debt'), 'ni', g('net_income'),
          'DA', g('depreciation_amortization'), 'afterT1', r.get('revenue_xbrl_first_filed_after_T1'))
