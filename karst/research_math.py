"""Small, explicit valuation bridges. Inputs are analyst assumptions, not forecasts."""
import argparse
import hashlib
import json
import math
from pathlib import Path


def positive(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
        raise ValueError(name + ' must be finite and positive')
    return value


def calculate(spec):
    method, p = spec['method'], spec['inputs']
    if method == 'index_earnings':
        point = positive(p['index_reference'], 'index_reference')
        fund = positive(p['fund_reference'], 'fund_reference')
        outputs = []
        for scenario in p['scenarios']:
            eps = positive(scenario['eps'], 'eps')
            pe = positive(scenario['pe'], 'pe')
            target = eps * pe
            outputs.append({'name': scenario['name'], 'index_value': target,
                            'fund_equivalent': fund * target / point})
        outputs = {'scenarios': outputs, 'conversion': fund / point,
                   'note': 'Fixed-date price-ratio approximation; excludes distributions and tracking changes.'}
    elif method == 'multiple_growth':
        terminal = positive(p['terminal_pe'], 'terminal_pe')
        years = positive(p['years'], 'years')
        rate = positive(p['required_return'], 'required_return')
        outputs = {'implied_growth': [], 'supported_multiples': []}
        for multiple in p['entry_multiples']:
            positive(multiple, 'entry_multiple')
            outputs['implied_growth'].append({'multiple': multiple,
                'annual_eps_growth': (multiple / terminal)**(1 / years) * (1 + rate) - 1})
        for growth in p['growth_rates']:
            positive(1 + growth, '1+growth')
            outputs['supported_multiples'].append({'annual_eps_growth': growth,
                'multiple': terminal * ((1 + growth) / (1 + rate))**years})
        outputs['note'] = 'No dividends; assumes diluted EPS after reinvestment. Terminal PE and return are judgments.'
    else:
        raise ValueError('Unknown method')
    encoded = json.dumps(spec, sort_keys=True, allow_nan=False).encode()
    return {'method': method, 'inputs': p, 'inputs_sha256': hashlib.sha256(encoded).hexdigest(), 'outputs': outputs}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    result = calculate(json.loads(Path(args.input).read_text()))
    Path(args.output).write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + '\n')


if __name__ == '__main__':
    main()
