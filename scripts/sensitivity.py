"""Sensitivity of the miss rate and of the decomposition to analysis choices.

(A) Numeric diagnostics for the miss rate. The primary verdict scores a win
    when any primary analysis is significant, which is lenient under
    multiplicity. Three stricter numeric readings of the minimum p are
    reported: the naive threshold (operator stripped), trials with a single
    primary outcome, and a Sidak per-trial threshold on the number of primary
    outcomes.

(B) Taxonomy. Five assignments are contestable. Each is varied in turn: half
    of regulatory stops to safety; the adjudicated share of external-evidence
    stops to efficacy; the adjudicated share of business or strategic stops
    to unknown; every bare sponsor decision to unknown; and the second-pass
    model labels of efficacy or futility, which the registry text does not
    support, to unknown. The adjudicated shares come from the validation
    sample. Two scenarios then ask how large the safety share could be if
    sponsor decisions, or sponsor and business decisions, concealed safety
    stops.
"""

import re

from failure_decomp import (
    ALL_YEARS,
    ALPHA,
    ERA,
    decompose,
    in_window,
    is_bigpharma,
    load,
    sponsor_of,
    valid_p,
)
from paper_numbers import Numbers, write_table
from repo_files import (
    REGISTRY,
    VALIDATION,
    D,
    read_json,
    read_labels,
    read_lines,
)

results, meta, stopcat = load()
nums = Numbers('sensitivity')

print(
    '=== (A) numeric miss-rate diagnostics (minimum p, operator stripped) ==='
)
for wkey, window in (('all', ALL_YEARS), ('era', ERA)):
    naive, single, sidak = [], [], []
    for r in results:
        if not valid_p(r['min_p']) or not in_window(meta, r['nct'], window):
            continue
        k = r.get('n_prim') or 1
        naive.append(r['min_p'] >= ALPHA)
        if k == 1:
            single.append(r['min_p'] >= ALPHA)
        # Sidak per-trial alpha; exactly ALPHA at k == 1
        threshold = ALPHA if k == 1 else 1 - (1 - ALPHA) ** (1 / k)
        sidak.append(r['min_p'] >= threshold)
    for key, label, rows in [
        ('naive', 'naive threshold', naive),
        ('single', 'single primary outcome', single),
        ('sidak', 'Sidak on primary outcomes', sidak),
    ]:
        print(
            f'  {window[0]}-{window[1]} {label:26s}: miss '
            f'{100 * sum(rows) / len(rows):.1f}% (n={len(rows)})'
        )
        nums.count(f'diag.{wkey}.{key}.trials', len(rows))
        nums.share(f'diag.{wkey}.{key}', sum(rows), len(rows))

print('\n=== (B) taxonomy reassignments, failure shares 2017-2026 ===')
gold = read_json(VALIDATION + 'gold_truth.json')
adjudicated = {
    line.split('\t')[0]: line.rstrip('\n').split('\t')[-1]
    for line in read_lines(D + VALIDATION + 'gold_adjudicated.tsv')
    if line.strip()
}


def adjudicated_as(label, other):
    """(k, n): sampled items labelled `label` that the adjudicator called
    `other`."""
    items = [n for n, lab in gold.items() if lab == label]
    return sum(adjudicated[n] == other for n in items), len(items)


ext_k, ext_n = adjudicated_as('external_evidence', 'efficacy_futility')
bus_k, bus_n = adjudicated_as('business_strategic', 'unclear')
print(
    f'  adjudicated: external evidence as efficacy/futility {ext_k}/{ext_n}; '
    f'business/strategic as unclear {bus_k}/{bus_n}'
)
nums.count('tax.external.k', ext_k)
nums.count('tax.external.n', ext_n)
nums.count('tax.business.k', bus_k)
nums.count('tax.business.n', bus_n)

BUCKETS = ('eff', 'op', 'com', 'saf', 'unk')

# The second-pass model labels of efficacy or futility among the stops of the
# main window. A reading of them found that neither the whyStopped string nor
# the detailed description states such a reason; the strings are classed here
# by what they name.
enriched = read_json(REGISTRY + 'unclear_enriched.json')
second_pass = read_labels('detail_out')
MONITORING = re.compile(r'dsmb|dmc|idmc|monitoring', re.IGNORECASE)
INTERIM = re.compile(r'interim', re.IGNORECASE)
model_labels = {
    n: lab
    for n, lab in stopcat.items()
    if in_window(meta, n, ERA)
    and second_pass.get(n) == lab
    and lab != 'unclear'
}
model_efficacy = sorted(
    n for n, lab in model_labels.items() if lab == 'efficacy_futility'
)
named = {'monitoring': 0, 'interim': 0, 'other': 0}
for n in model_efficacy:
    why = enriched[n].get('why') or ''
    if MONITORING.search(why):
        named['monitoring'] += 1
    elif INTERIM.search(why):
        named['interim'] += 1
    else:
        named['other'] += 1
print(
    f'  second-pass model labels standing in 2017-2026: {len(model_labels)}; '
    f'efficacy or futility: {len(model_efficacy)} {named}'
)
nums.count('audit.model.n', len(model_labels))
nums.count('audit.eff.n', len(model_efficacy))
for key, k in named.items():
    nums.count(f'audit.eff.{key}', k)
nums.text('audit.eff.ncts', ', '.join(model_efficacy))


def of_label(*labels, fraction=1.0):
    """The expected number of failures moved: a fraction of the stops that
    carry one of the labels, not a whole number of trials."""
    return lambda d, subset: fraction * sum(d['labels'][x] for x in labels)


def audited(d, subset):
    return sum(1 for n in model_efficacy if subset is None or subset(n))


# (key, row label, source bucket, target bucket, how many failures move)
VARIANTS = [
    ('asAnalysed', 'as analyzed', None, None, None),
    (
        'regToSafety',
        'half of regulatory stops to safety',
        'op',
        'saf',
        of_label('regulatory', fraction=0.5),
    ),
    (
        'extToEfficacy',
        f'{ext_k}/{ext_n} of external evidence to efficacy',
        'op',
        'eff',
        of_label('external_evidence', fraction=ext_k / ext_n),
    ),
    (
        'busToUnknown',
        f'{bus_k}/{bus_n} of business or strategic to unknown',
        'com',
        'unk',
        of_label('business_strategic', fraction=bus_k / bus_n),
    ),
    (
        'sponsorToUnknown',
        'bare sponsor decisions to unknown',
        'com',
        'unk',
        of_label('sponsor_undisclosed'),
    ),
    (
        'modelEfficacyToUnknown',
        'second-pass efficacy labels to unknown',
        'eff',
        'unk',
        audited,
    ),
    (
        'sponsorToSafety',
        'bare sponsor decisions to safety',
        'com',
        'saf',
        of_label('sponsor_undisclosed'),
    ),
    (
        'decisionsToSafety',
        'sponsor and business decisions to safety',
        'com',
        'saf',
        of_label('sponsor_undisclosed', 'business_strategic'),
    ),
]
# the first rows vary an assignment; the last two are scenarios for safety
nums.count('tax.assignments', 5)
nums.count('tax.scenarios', 2)
assert len(VARIANTS) == 1 + 5 + 2


def big(n):
    return is_bigpharma(sponsor_of(meta, n))


table = []
for skey, slabel, subset in (
    ('all', 'all sponsors', None),
    ('big', 'big pharma', big),
):
    d = decompose(results, meta, stopcat, ERA, subset=subset)
    print(f'  {slabel} (n={d["den"]}):')
    for vkey, vlabel, source, target, amount in VARIANTS:
        counts = {b: d[b] for b in BUCKETS}
        if amount:
            moved = amount(d, subset)
            counts[source] -= moved
            counts[target] += moved
        pct = {b: 100 * counts[b] / d['den'] for b in BUCKETS}
        print(
            f'    {vlabel:42s} '
            + '  '.join(f'{b} {pct[b]:4.1f}' for b in BUCKETS)
        )
        for b in BUCKETS:
            nums.pct(f'tax.{skey}.{vkey}.{b}', pct[b])
        table.append([vlabel, slabel] + [f'{pct[b]:.1f}' for b in BUCKETS])
write_table('taxonomy', table)
nums.save()
