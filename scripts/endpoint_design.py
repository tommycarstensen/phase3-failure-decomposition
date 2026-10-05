"""How the miss rate depends on endpoint design and on the win rule.

Uses the full primary-analysis records (ph3_primary_analyses.json).

(A) Non-inferiority and equivalence designs, where a p-value against the null
    is not the success criterion: the miss rate with those trials excluded.
(B) Direction of effect among wins: how many wins have only ratio parameters
    above 1 among their significant analyses, and how many only hazard ratios
    above 1. The registry does not record which direction is benefit, so these
    are counts, not a bound on wins in the harmful direction.
(C) Rules for combining primary outcomes. The primary verdict is a win when
    any primary analysis is significant. Two stricter rules are reported:
    every primary outcome that has a usable p-value must be significant, and
    every primary outcome must be significant (an outcome with no usable
    p-value counts as not significant). The failure decomposition of the
    main window is repeated under each: a stricter rule turns wins of
    completed trials into misses, which are efficacy failures.
(D) Stability of the extracted values between the two retrievals. Both use
    the same parsing code, so this measures change in the registry, not the
    correctness of the parser.
"""

from collections import defaultdict

from failure_decomp import (
    ALL_YEARS,
    ALPHA,
    ERA,
    decompose,
    in_window,
    is_bigpharma,
    load,
    record_sig,
    sponsor_of,
    valid_p,
)
from paper_numbers import Numbers
from repo_files import REGISTRY, read_json

results, meta, stopcat = load()
pa = {r['nct']: r for r in read_json(REGISTRY + 'ph3_primary_analyses.json')}
nums = Numbers('endpoint_design')
WINDOWS = (('all', ALL_YEARS), ('era', ERA))

NI_TYPES = {
    'NON_INFERIORITY',
    'NON_INFERIORITY_OR_EQUIVALENCE',
    'EQUIVALENCE',
    'NON_INFERIORITY_OR_EQUIVALENCE_LEGACY',
}


def is_ni(nct):
    rec = pa.get(nct)
    return bool(rec) and bool(
        {a.get('ni_type') for a in rec['analyses']} & NI_TYPES
    )


print('=== (A) non-inferiority and equivalence designs excluded ===')
for wkey, window in WINDOWS:
    judged = [
        r
        for r in results
        if r['win'] is not None and in_window(meta, r['nct'], window)
    ]
    sup = [r for r in judged if not is_ni(r['nct'])]
    miss_sup = sum(r['win'] is False for r in sup)
    ni = len(judged) - len(sup)
    print(
        f'  {window[0]}-{window[1]}: {ni} of {len(judged)} trials '
        f'({100 * ni / len(judged):.1f}%) declare such a design; miss rate '
        f'without them {100 * miss_sup / len(sup):.1f}% (n={len(sup)})'
    )
    nums.share(f'ni.{wkey}', ni, len(judged))
    nums.count(f'ni.{wkey}.superiority.trials', len(sup))
    nums.share(f'ni.{wkey}.superiority.miss', miss_sup, len(sup))

print('\n=== (B) direction of effect among wins, 2017-2026 ===')
RATIO = (
    'HAZARD RATIO',
    'ODDS RATIO',
    'RISK RATIO',
    'RELATIVE RISK',
    'GMT RATIO',
)


def param_is(a, words):
    pt = (a.get('param_type') or '').upper().replace('_', ' ')
    return any(w in pt for w in words)


wins = ratio_only = hazard_only = 0
for r in results:
    if not r['win'] or not in_window(meta, r['nct'], ERA):
        continue
    wins += 1
    rec = pa.get(r['nct'])
    sig = [
        a
        for a in (rec['analyses'] if rec else [])
        if record_sig(a.get('p_raw'), a.get('p')) is True
    ]
    if not sig:
        continue
    above = [(a.get('param_value') or 0) > 1 for a in sig]
    if all(above) and all(param_is(a, RATIO) for a in sig):
        ratio_only += 1
    if all(above) and all(param_is(a, RATIO[:1]) for a in sig):
        hazard_only += 1
print(f'  wins: {wins}')
print(
    f'  every significant analysis a ratio parameter above 1: {ratio_only} '
    f'({100 * ratio_only / wins:.1f}%)'
)
print(
    f'  of those, every one a hazard ratio above 1: {hazard_only} '
    f'({100 * hazard_only / wins:.2f}%)'
)
nums.count('direction.wins', wins)
nums.share('direction.ratioOnly', ratio_only, wins)
nums.count('direction.hazardOnly.n', hazard_only)
nums.fixed('direction.hazardOnly.pct', 100 * hazard_only / wins, 1)

print('\n=== (C) rules for combining primary outcomes ===')
verdict = {'and': {}, 'strict': {}}  # rule -> nct -> win, any start year
for wkey, window in WINDOWS:
    n = miss_any = miss_and = miss_strict = incomplete = 0
    for r in results:
        rec = pa.get(r['nct'])
        if r['win'] is None or not rec:
            continue
        if not in_window(meta, r['nct'], window):
            continue
        per_outcome = defaultdict(list)
        for a in rec['analyses']:
            rs = record_sig(a.get('p_raw'), a.get('p'))
            if rs is None:
                continue
            if rs == 'AMB':  # numeric fallback, as in the verdict
                rs = a['p'] < ALPHA
            per_outcome[a['oi']].append(rs)
        if not per_outcome:
            continue
        n += 1
        hits = [any(v) for v in per_outcome.values()]
        lacking = rec['n_prim'] > len(per_outcome)
        incomplete += lacking
        miss_any += not any(hits)
        miss_and += not all(hits)
        miss_strict += lacking or not all(hits)
        verdict['and'][r['nct']] = all(hits)
        verdict['strict'][r['nct']] = all(hits) and not lacking
    print(
        f'  {window[0]}-{window[1]} (n={n}): any outcome '
        f'{100 * miss_any / n:.1f}%; every outcome that has a p-value '
        f'{100 * miss_and / n:.1f}%; every outcome '
        f'{100 * miss_strict / n:.1f}%; '
        f'{incomplete} trials have a primary outcome with no usable p-value'
    )
    nums.count(f'combine.{wkey}.trials', n)
    nums.share(f'combine.{wkey}.any', miss_any, n)
    nums.share(f'combine.{wkey}.and', miss_and, n)
    nums.share(f'combine.{wkey}.strict', miss_strict, n)
    nums.share(f'combine.{wkey}.incomplete', incomplete, n)


def big(nct):
    return is_bigpharma(sponsor_of(meta, nct))


print('  failure shares of the main window under each rule:')
for rule, wins in (('any', {}), *verdict.items()):
    judged = [{**r, 'win': wins.get(r['nct'], r['win'])} for r in results]
    for skey, subset in (('all', None), ('big', big)):
        d = decompose(judged, meta, stopcat, ERA, subset=subset)
        print(
            f'    {rule:6s} {skey}: {d["den"]} failures, efficacy '
            f'{100 * d["eff"] / d["den"]:.1f}%, operational '
            f'{100 * d["op"] / d["den"]:.1f}%'
        )
        nums.count(f'winrule.{rule}.{skey}.n', d['den'])
        nums.share(f'winrule.{rule}.{skey}.eff', d['eff'], d['den'])
        nums.share(f'winrule.{rule}.{skey}.op', d['op'], d['den'])

print('\n=== (D) stability between the two retrievals ===')
both = [r for r in results if r['nct'] in pa]
same_count = same_p = compared = 0
for r in both:
    rec = pa[r['nct']]
    same_count += r['n_prim'] == rec['n_prim']
    ps = [a['p'] for a in rec['analyses'] if a['p'] is not None]
    if r['min_p'] is not None and ps:
        compared += 1
        same_p += abs(r['min_p'] - min(ps)) < 1e-12
print(f'  trials in both retrievals: {len(both)} of {len(results)}')
print(
    f'  same number of primary outcomes: {same_count} '
    f'({100 * same_count / len(both):.2f}%)'
)
print(f'  same minimum p: {same_p} of {compared}')
nums.count('stability.both', len(both))
nums.count('stability.sameCount', same_count)
nums.fixed('stability.sameCount.pct', 100 * same_count / len(both), 2)
nums.count('stability.compared', compared)
nums.count('stability.sameP', same_p)
nums.count(
    'stability.invalidMinP',
    sum(
        1
        for r in results
        if r['min_p'] is not None and not valid_p(r['min_p'])
    ),
)
nums.save()
