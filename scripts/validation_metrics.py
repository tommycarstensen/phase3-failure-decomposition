"""Agreement between the first-pass labels and a blind adjudication.

The validation sample (gold_sample.tsv) holds the same number of first-pass
whyStopped labels for each category. A stronger model labelled the same
strings blind (gold_adjudicated.tsv); gold_truth.json holds the first-pass
labels.

The sample is stratified on the first-pass label, so agreement within a
stratum estimates P(adjudicator agrees | first-pass label). Weighting the
strata by how often each first-pass label occurs gives the agreement expected
over all first-pass labels. Two sets of weights are reported: all first-pass
labels, and those of trials that enrolled and started in the main window.

Labels assigned by the second and third passes and by the rules in
reclassify.py are not in the sample; the script counts how many final labels
that leaves unvalidated.
"""

import collections

import numpy as np

from failure_decomp import ERA, bucket_of, in_window, load, wilson
from paper_numbers import Numbers, write_table
from repo_files import (
    LABELS,
    VALIDATION,
    D,
    read_json,
    read_labels,
    read_lines,
)

SEED = 20260803
DRAWS = 10000
NAMES = {
    'enrollment': 'enrollment',
    'business_strategic': 'business or strategic',
    'efficacy_futility': 'efficacy or futility',
    'unclear': 'unclear',
    'other_operational': 'other operational',
    'funding': 'funding',
    'external_evidence': 'external evidence',
    'safety': 'safety',
    'regulatory': 'regulatory',
    'covid': 'COVID-19',
    'efficacy_positive': 'efficacy positive',
    'supply_manufacturing': 'supply or manufacturing',
}


def weighted(strata, prevalence, rng):
    """Agreement weighted by label prevalence, with a stratified bootstrap
    interval; all three as fractions."""
    cats = list(strata)
    total = sum(prevalence[c] for c in cats)
    w = np.array([prevalence[c] / total for c in cats])
    arrays = [np.array(strata[c], float) for c in cats]
    point = float((w * [a.mean() for a in arrays]).sum())
    boot = np.empty(DRAWS)
    for b in range(DRAWS):
        means = [a[rng.integers(0, len(a), len(a))].mean() for a in arrays]
        boot[b] = (w * means).sum()
    lo, hi = np.percentile(boot, [2.5, 97.5])
    return point, float(lo), float(hi)


def main():
    _, meta, final = load()
    first = read_labels('why_out')
    sample = read_json(VALIDATION + 'gold_truth.json')
    adjudicated = {
        line.split('\t')[0]: line.rstrip('\n').split('\t')[-1]
        for line in read_lines(D + VALIDATION + 'gold_adjudicated.tsv')
        if line.strip()
    }
    ncts = [n for n in sample if n in adjudicated]
    total = len(ncts)
    assert all(sample[n] == first[n] for n in ncts)  # first-pass labels
    nums = Numbers('validation_metrics')

    strata = collections.defaultdict(list)
    confusion = collections.defaultdict(collections.Counter)
    for n in ncts:
        strata[sample[n]].append(sample[n] == adjudicated[n])
        confusion[sample[n]][adjudicated[n]] += 1
    agree = sum(sum(v) for v in strata.values())
    lo, hi = wilson(agree, total)
    per_stratum = {len(v) for v in strata.values()}

    labels = sorted(strata)
    first_marginal = collections.Counter(sample[n] for n in ncts)
    adj_marginal = collections.Counter(adjudicated[n] for n in ncts)
    pe = sum(
        (first_marginal[c] / total) * (adj_marginal[c] / total) for c in labels
    )
    kappa = (agree / total - pe) / (1 - pe)

    # first-pass label prevalence: all labels, and enrolled trials 2017-2026
    prev_all = collections.Counter(first.values())
    prev_era = collections.Counter(
        first[n] for n in final if n in first and in_window(meta, n, ERA)
    )
    rng = np.random.default_rng(SEED)
    w_all = weighted(strata, prev_all, rng)
    w_era = weighted(strata, prev_era, rng)

    # the same at the level of the buckets the decomposition reports: a
    # disagreement between two categories of one bucket does not move a share
    in_bucket = collections.defaultdict(list)
    for n in ncts:
        in_bucket[sample[n]].append(
            bucket_of(sample[n]) == bucket_of(adjudicated[n])
        )
    b_agree = sum(sum(v) for v in in_bucket.values())
    b_lo, b_hi = wilson(b_agree, total)
    w_bucket = weighted(in_bucket, prev_all, rng)

    # kappa with the first-pass prevalence as the label marginal
    n_all = sum(prev_all.values())
    p_first = {c: prev_all[c] / n_all for c in labels}
    p_adj = {
        c: sum(p_first[s] * confusion[s][c] / len(strata[s]) for s in labels)
        for c in labels
    }
    pe_w = sum(p_first[c] * p_adj[c] for c in labels)
    kappa_w = (w_all[0] - pe_w) / (1 - pe_w)

    # final labels the sample does not cover (enrolled trials, 2017-2026)
    later = set(read_json(LABELS + 'unclear_reclassified_v2.json'))
    era = [n for n in final if in_window(meta, n, ERA)]
    era_later = [n for n in era if n in later]

    print(f'sample: {total} first-pass labels, {per_stratum} per category')
    print(
        f'agreement: {agree}/{total} = {100 * agree / total:.1f}% '
        f'[{lo:.1f}, {hi:.1f}]; kappa {kappa:.3f} (chance {pe:.3f})'
    )
    print(
        f'weighted to all first-pass labels (n={n_all}): '
        f'{100 * w_all[0]:.1f}% [{100 * w_all[1]:.1f}, {100 * w_all[2]:.1f}]; '
        f'kappa {kappa_w:.3f} (chance {pe_w:.3f})'
    )
    print(
        f'weighted to enrolled 2017-2026 first-pass labels '
        f'(n={sum(prev_era.values())}): {100 * w_era[0]:.1f}% '
        f'[{100 * w_era[1]:.1f}, {100 * w_era[2]:.1f}]'
    )
    print(
        f'enrolled 2017-2026 stopped trials: {len(era)}; label set by a later '
        f'pass or rule: {len(era_later)} '
        f'({100 * len(era_later) / len(era):.1f}%)'
    )

    print(
        f'same bucket: {b_agree}/{total} = {100 * b_agree / total:.1f}% '
        f'[{b_lo:.1f}, {b_hi:.1f}]; weighted {100 * w_bucket[0]:.1f}% '
        f'[{100 * w_bucket[1]:.1f}, {100 * w_bucket[2]:.1f}]'
    )
    nums.share('valid.bucket.agree', b_agree, total)
    nums.pct('valid.bucket.agree.lo', b_lo)
    nums.pct('valid.bucket.agree.hi', b_hi)
    nums.pct('valid.bucket.weighted.pct', 100 * w_bucket[0])
    nums.pct('valid.bucket.weighted.lo', 100 * w_bucket[1])
    nums.pct('valid.bucket.weighted.hi', 100 * w_bucket[2])
    nums.count('valid.sample', total)
    nums.count('valid.perCategory', per_stratum.pop())
    nums.count('valid.categories', len(labels))
    nums.share('valid.agree', agree, total)
    nums.pct('valid.agree.lo', lo)
    nums.pct('valid.agree.hi', hi)
    nums.fixed('valid.kappa', kappa, 2)
    nums.count('valid.firstPass.labels', n_all)
    nums.pct('valid.weighted.pct', 100 * w_all[0])
    nums.pct('valid.weighted.lo', 100 * w_all[1])
    nums.pct('valid.weighted.hi', 100 * w_all[2])
    nums.fixed('valid.weighted.kappa', kappa_w, 2)
    nums.pct('valid.weightedEra.pct', 100 * w_era[0])
    nums.pct('valid.weightedEra.lo', 100 * w_era[1])
    nums.pct('valid.weightedEra.hi', 100 * w_era[2])
    nums.count('valid.era.stopped', len(era))
    nums.share('valid.era.laterPass', len(era_later), len(era))

    print('\nper category, by first-pass prevalence:')
    table = []
    for c in sorted(labels, key=lambda c: -prev_all[c]):
        k, n = sum(strata[c]), len(strata[c])
        c_lo, c_hi = wilson(k, n)
        share = 100 * prev_all[c] / n_all
        others = {o: t for o, t in confusion[c].items() if o != c}
        times = max(others.values(), default=0)
        top = sorted(o for o, t in others.items() if t == times)
        if not times:
            instead = 'none'
        elif len(top) == 1:
            instead = f'{NAMES[top[0]]} ({times})'
        else:  # no single label leads
            instead = f'{len(top)} labels ({times} each)'
        print(
            f'  {c:22s} {k:2d}/{n}  [{c_lo:.0f}, {c_hi:.0f}]  prevalence '
            f'{share:4.1f}%  most often adjudicated instead: {instead}'
        )
        key = 'valid.cat.' + c.replace('_', '')
        nums.count(key + '.agree', k)
        nums.fixed(key + '.rate', k / n, 2)
        table.append(
            [
                NAMES[c],
                f'{k}/{n}',
                f'{c_lo:.0f} to {c_hi:.0f}',
                f'{share:.1f}',
                instead,
            ]
        )
    write_table('validation', table)
    nums.save()


if __name__ == '__main__':
    main()
