"""Failure decomposition and miss rate by therapeutic area, main window.

Areas come from the keyword mapper in areas.py. The miss rate is over trials
with a verdict and has its own denominator, which is not the failure count.
"""

from areas import area_of
from failure_decomp import ERA, decompose, load, miss_rate
from paper_numbers import Numbers, write_table
from repo_files import REGISTRY, read_json

AREAS = [
    'Oncology',
    'Cardiometabolic',
    'Neuro/Psych',
    'Immunology/Inflammation',
    'Infectious/Vaccine',
    'Other/rare',
]
results, meta, stopcat = load()
cond = read_json(REGISTRY + 'ph3_conditions.json')
nums = Numbers('stratify')

print('=== therapeutic area, 2017-2026 ===')
table, rates = [], {}
for area in AREAS:

    def in_area(n, area=area):
        return area_of(cond, n) == area

    d = decompose(results, meta, stopcat, ERA, subset=in_area)
    n, m, rate = miss_rate(results, meta, ERA, subset=in_area)
    den = d['den']
    pct = {b: 100 * d[b] / den for b in ('eff', 'op', 'com', 'saf', 'unk')}
    rates[area] = rate
    print(
        f'  {area:26s} failures {den:4d}  miss {rate:4.1f}% (n={n})  '
        + '  '.join(f'{b} {v:4.1f}' for b, v in pct.items())
    )
    key = 'strat.' + ''.join(c for c in area if c.isalpha())
    nums.count(key + '.n', den)
    nums.count(key + '.miss.trials', n)
    nums.share(key + '.miss', m, n)
    for b, value in pct.items():
        nums.pct(f'{key}.{b}', value)
    table.append(
        [area, den, n, f'{rate:.1f}']
        + [f'{pct[b]:.1f}' for b in ('eff', 'op', 'com', 'saf', 'unk')]
    )
write_table('areas', table)
low = min(AREAS, key=lambda a: rates[a])
high = max(AREAS, key=lambda a: rates[a])
nums.pct('strat.miss.min', rates[low])
nums.text('strat.miss.min.area', low)
nums.pct('strat.miss.max', rates[high])
nums.text('strat.miss.max.area', high)
nums.save()
