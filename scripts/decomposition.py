"""The failure decomposition and the primary-endpoint miss rate.

Reports the five failure buckets with Wilson intervals for all sponsors and
for the big-pharma stratum, in the Final-Rule era, in the readout-complete
window and over all years. The primary population is trials that enrolled;
the same decomposition with registrations withdrawn before enrollment counted
as failures is reported as a sensitivity. All counting rules are in
failure_decomp.py.
"""

from failure_decomp import (
    ALL_YEARS,
    COMMERCIAL,
    ERA,
    ERA_COMPLETE,
    NO_REASON,
    decompose,
    is_bigpharma,
    load,
    miss_rate,
    sponsor_of,
    wilson,
)
from paper_numbers import Numbers

BUCKETS = [
    ('eff', 'efficacy'),
    ('op', 'operational'),
    ('com', 'commercial'),
    ('saf', 'safety'),
    ('unk', 'unknown'),
]
WINDOWS = [
    ('era', f'{ERA[0]}-{ERA[1]}', ERA),
    ('complete', f'{ERA_COMPLETE[0]}-{ERA_COMPLETE[1]}', ERA_COMPLETE),
    ('all', 'all years', ALL_YEARS),
]
nums = Numbers('decomposition')


def report(key, label, results, meta, stopcat, window, subset):
    d = decompose(results, meta, stopcat, window, subset=subset)
    den = d['den']
    print(
        f'  {label}: failures {den} (completed misses {d["cm"]}; '
        f'stopped for benefit, excluded: {d["pos"]})'
    )
    nums.count(key + '.n', den)
    nums.count(key + '.completedMiss', d['cm'])
    nums.count(key + '.futility', d['labels']['efficacy_futility'])
    nums.pct(key + '.completedMissOfEff.pct', 100 * d['cm'] / d['eff'])
    nums.count(key + '.benefit', d['pos'])
    for b, name in BUCKETS:
        lo, hi = wilson(d[b], den)
        print(
            f'    {name:12s} {d[b]:5d}  {100 * d[b] / den:5.1f}%  '
            f'[{lo:.1f}, {hi:.1f}]'
        )
        nums.share(f'{key}.{b}', d[b], den)
        nums.pct(f'{key}.{b}.lo', lo)
        nums.pct(f'{key}.{b}.hi', hi)


def run(pkey, plabel, include_withdrawn):
    results, meta, stopcat = load(include_withdrawn=include_withdrawn)

    def big(n):
        return is_bigpharma(sponsor_of(meta, n))

    def rest(n):
        return not big(n)

    for wkey, wlabel, window in WINDOWS:
        print(f'=== {plabel}, {wlabel} ===')
        for skey, slabel, subset in [
            ('all', 'all sponsors', None),
            ('big', 'big pharma', big),
            ('rest', 'all other sponsors', rest),
        ]:
            key = f'decomp.{pkey}.{wkey}.{skey}'
            report(key, slabel, results, meta, stopcat, window, subset)
    return results, meta


results, meta = run('enrolled', 'trials that enrolled', False)
run('registered', 'withdrawn registrations counted', True)

print(f'=== registrations withdrawn before enrollment, {ERA[0]}-{ERA[1]} ===')
enrolled = load()[2]
registered = load(include_withdrawn=True)[2]
withdrawn = set(registered) - set(enrolled)
d = decompose(results, meta, registered, ERA, subset=withdrawn.__contains__)
print(f'  not stopped for benefit: {d["den"]}')
nums.count('withdrawn.era.n', d['den'])
nums.count(
    'withdrawn.era.notStated.n',
    sum(d['labels'][k] for k in NO_REASON if k in COMMERCIAL),
)
for b, name in BUCKETS:
    print(f'    {name:12s} {d[b]:5d}  {100 * d[b] / d["den"]:5.1f}%')
    nums.share(f'withdrawn.era.{b}', d[b], d['den'])

print('=== primary-endpoint miss rate (trials with a verdict) ===')
for wkey, wlabel, window in WINDOWS:
    n, m, rate = miss_rate(results, meta, window)
    nc, mc, ratec = miss_rate(results, meta, window, completed_only=True)
    lo, hi = wilson(m, n)
    print(
        f'  {wlabel}: {rate:.1f}% ({m}/{n}) [{lo:.1f}, {hi:.1f}]; '
        f'completed trials only {ratec:.1f}% ({mc}/{nc})'
    )
    nums.count(f'miss.{wkey}.trials', n)
    nums.share(f'miss.{wkey}', m, n)
    nums.pct(f'miss.{wkey}.lo', lo)
    nums.pct(f'miss.{wkey}.hi', hi)
    nums.count(f'miss.{wkey}.completed.trials', nc)
    nums.share(f'miss.{wkey}.completed', mc, nc)
nums.save()
