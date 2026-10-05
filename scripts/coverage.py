"""Endpoint-reporting coverage and what it does to the efficacy share.

A completed trial enters the efficacy bucket only if its posted results carry
a primary analysis with a usable p-value. Stopped trials enter the
decomposition whether or not they report one, so the efficacy bucket is
under-filled relative to the others.

The script measures that coverage among completed, non-stopped trials of the
Final-Rule era and imputes the missing misses three ways:

  pooled     every unreported trial with a comparator arm missed at the rate
             observed among reporting trials with a comparator arm
  adjusted   the same, with the miss probability predicted from sponsor
             class, start year, number of primary outcomes and therapeutic
             area (a logistic model fitted to the reporting trials)
  bounds     none of them missed (the observed share) or all of them missed

Single-arm studies have no between-group test to miss and receive no imputed
miss; imputing for them as well is reported for comparison. The bounds are
conditional on the cohort: a completed trial that never posted results is not
in it.
"""

import numpy as np
import statsmodels.api as sm

from areas import area_of
from failure_decomp import (
    ERA,
    decompose,
    in_window,
    is_bigpharma,
    load,
    sponsor_of,
    year_of,
)
from paper_numbers import Numbers
from repo_files import REGISTRY, read_json

SEED = 20260803
DRAWS = 10000
BUCKETS = ('eff', 'op', 'com', 'saf', 'unk')

arms = read_json(REGISTRY + 'ph3_arms.json')
cond = read_json(REGISTRY + 'ph3_conditions.json')
nums = Numbers('coverage')


def arm_groups(nct):
    return len((arms.get(nct) or {}).get('armGroups', []))


def single_arm(nct):
    return arm_groups(nct) == 1


def shares(d, extra):
    """Bucket shares in percent after adding `extra` efficacy misses."""
    den = d['den'] + extra
    out = {b: 100 * d[b] / den for b in BUCKETS}
    out['eff'] = 100 * (d['eff'] + extra) / den
    return out


def design_matrix(trials, meta, areas):
    year = np.array([year_of(meta, r['nct']) for r in trials], float)
    cols = [
        np.ones(len(trials)),
        [float(is_bigpharma(sponsor_of(meta, r['nct']))) for r in trials],
        year - 2020,
        np.log([r.get('n_prim') or 1 for r in trials]),
    ]
    for a in areas:
        cols.append([float(area_of(cond, r['nct']) == a) for r in trials])
    return np.column_stack(cols)


def analyse(pkey, plabel, include_withdrawn, subset_key, subset_label, big):
    results, meta, stopcat = load(include_withdrawn=include_withdrawn)

    def keep(n):
        if not in_window(meta, n, ERA):
            return False
        if big is None:
            return True
        return is_bigpharma(sponsor_of(meta, n)) == big

    d = decompose(results, meta, stopcat, ERA, subset=keep)
    completed = [
        r
        for r in results
        if r['status'] == 'COMPLETED'
        and r['nct'] not in stopcat
        and keep(r['nct'])
    ]
    reported = [r for r in completed if r['win'] is not None]
    unreported = [r for r in completed if r['win'] is None]
    rep_c = [r for r in reported if not single_arm(r['nct'])]
    unrep_c = [r for r in unreported if not single_arm(r['nct'])]
    misses = sum(r['win'] is False for r in reported)
    misses_c = sum(r['win'] is False for r in rep_c)
    assert misses == d['cm'], (misses, d['cm'])
    rate = misses / len(reported)
    rate_c = misses_c / len(rep_c)

    key = f'coverage.{pkey}.{subset_key}'
    print(f'=== {plabel}, {subset_label}, {ERA[0]}-{ERA[1]} ===')
    print(
        f'  completed, not stopped: {len(completed)}; with a verdict '
        f'{len(reported)} ({100 * len(reported) / len(completed):.1f}%)'
    )
    n_single_rep = len(reported) - len(rep_c)
    n_single_unrep = len(unreported) - len(unrep_c)
    print(
        f'  single-arm: {n_single_rep} of those with a verdict '
        f'({100 * n_single_rep / len(reported):.1f}%), {n_single_unrep} of '
        f'those without ({100 * n_single_unrep / len(unreported):.1f}%)'
    )
    print(
        f'  with a comparator arm: {len(rep_c)} reported, {len(unrep_c)} '
        f'unreported; miss rate among reported {100 * rate_c:.1f}% '
        f'({misses_c}/{len(rep_c)})'
    )
    nums.count(key + '.completed', len(completed))
    nums.share(key + '.reported', len(reported), len(completed))
    nums.share(key + '.unreported', len(unreported), len(completed))
    nums.share(key + '.singleArm.reported', n_single_rep, len(reported))
    nums.share(key + '.singleArm.unreported', n_single_unrep, len(unreported))
    nums.count(key + '.comparator.reported', len(rep_c))
    nums.count(key + '.comparator.unreported', len(unrep_c))
    # not single-arm, but with no arm group recorded at all
    nums.count(
        key + '.comparator.noArmGroups',
        sum(arm_groups(r['nct']) == 0 for r in rep_c + unrep_c),
    )
    nums.pct(
        key + '.comparator.coverage.pct',
        100 * len(rep_c) / (len(rep_c) + len(unrep_c)),
    )
    nums.share(key + '.comparator.miss', misses_c, len(rep_c))
    nums.share(key + '.all.miss', misses, len(reported))

    def show(name, label, extra, lo=None, hi=None):
        s = shares(d, extra)
        ci = ''
        if lo is not None and hi is not None:
            a, b = shares(d, lo), shares(d, hi)
            ci = (
                f'  efficacy 95% CI [{a["eff"]:.1f}, {b["eff"]:.1f}], '
                f'operational [{b["op"]:.1f}, {a["op"]:.1f}]'
            )
            nums.pct(f'{key}.{name}.eff.lo', a['eff'])
            nums.pct(f'{key}.{name}.eff.hi', b['eff'])
            nums.pct(f'{key}.{name}.op.lo', b['op'])
            nums.pct(f'{key}.{name}.op.hi', a['op'])
        print(
            f'  {label:34s} efficacy {s["eff"]:5.1f}  operational '
            f'{s["op"]:5.1f}  commercial {s["com"]:5.1f}  safety '
            f'{s["saf"]:4.1f}  unknown {s["unk"]:4.1f}{ci}'
        )
        nums.count(f'{key}.{name}.extra', round(extra))
        for b in BUCKETS:
            nums.pct(f'{key}.{name}.{b}', s[b])

    show('raw', 'as observed', 0)
    # bootstrap the miss rate among reporting comparator trials
    rng = np.random.default_rng(SEED)
    win = np.array([r['win'] is False for r in rep_c], float)
    draws = rng.choice(win, size=(DRAWS, len(win)), replace=True).mean(axis=1)
    lo, hi = np.percentile(draws, [2.5, 97.5]) * len(unrep_c)
    show(
        'pooled',
        'pooled miss rate, comparator arms',
        rate_c * len(unrep_c),
        lo,
        hi,
    )

    # covariate-adjusted: logistic miss model on the reporting trials
    areas = sorted({area_of(cond, r['nct']) for r in rep_c})[1:]
    x_rep = design_matrix(rep_c, meta, areas)
    variable = x_rep.std(axis=0) > 0
    variable[0] = True  # the intercept
    model = sm.GLM(win, x_rep[:, variable], family=sm.families.Binomial())
    fit = model.fit()
    x_unrep = design_matrix(unrep_c, meta, areas)[:, variable]
    show('adjusted', 'covariate-adjusted', float(fit.predict(x_unrep).sum()))

    show('upper', 'bound: every one missed', len(unrep_c))
    show(
        'withSingleArm', 'pooled, single-arm included', rate * len(unreported)
    )
    needed = d['op'] - d['eff']
    if needed > 0:
        print(
            f'  extra misses for efficacy to pass operational: {needed} '
            f'({100 * needed / len(unrep_c):.1f}% of the unreported with a '
            'comparator arm)'
        )
        nums.share(key + '.needed', needed, len(unrep_c))


analyse('enrolled', 'trials that enrolled', False, 'all', 'all sponsors', None)
analyse('enrolled', 'trials that enrolled', False, 'big', 'big pharma', True)
analyse(
    'enrolled',
    'trials that enrolled',
    False,
    'rest',
    'all other sponsors',
    False,
)
analyse('registered', 'withdrawn counted', True, 'all', 'all sponsors', None)
nums.save()
