"""Tests and intervals behind the manuscript's inferential statements.

1. Miss rate by start year: Cochran-Armitage trend, logistic slope with
   sponsor-clustered standard errors, and a test of homogeneity across years.
2. Sponsor-class contrast in the miss rate, plain and clustered by program.
3. The big-pharma efficacy share against Hwang et al.: a two-sample test that
   carries Hwang's sampling error, plain and with program-clustered standard
   errors, in three variants of the population.
4. Therapeutic-area heterogeneity in the miss rate.
5. Which completed trials report a usable primary p-value: a logistic model
   on sponsor class, start year, number of primary outcomes, single-arm design
   and therapeutic area.
"""

import math

import numpy as np
import statsmodels.api as sm
from scipy import stats

import subjects
from areas import area_of
from failure_decomp import (
    ALPHA,
    EFFICACY,
    ERA,
    ERA_COMPLETE,
    HWANG,
    SUCCESS,
    TREND,
    decompose,
    in_window,
    is_bigpharma,
    load,
    miss_rate,
    sponsor_of,
    valid_p,
    wilson,
    year_of,
)
from paper_numbers import Numbers, tex_escape, write_table
from repo_files import REGISTRY, read_json

results, meta, stopcat = load()
cond = read_json(REGISTRY + 'ph3_conditions.json')
arms = read_json(REGISTRY + 'ph3_arms.json')
subject_of, _, _ = subjects.build(arms, results)
nums = Numbers('inference')
binomial = sm.families.Binomial()
# exploratory split of the Infectious/Vaccine miss rate (supplement)
INFECTIOUS_SPLIT = 2020


def big(n):
    return is_bigpharma(sponsor_of(meta, n))


def big_wide(n):
    return is_bigpharma(sponsor_of(meta, n), with_midsize=True)


def cluster_of(nct):
    """The trial's subject drug, or the trial itself where none is known."""
    return subject_of(nct) or ('nct:' + nct)


def cochran_armitage(by_year):
    """(z, p) for a linear trend in the proportion; by_year maps a score to
    [non-events, events]."""
    scores = np.array(sorted(by_year), float)
    total = np.array([sum(by_year[y]) for y in sorted(by_year)])
    events = np.array([by_year[y][1] for y in sorted(by_year)])
    p_bar = events.sum() / total.sum()
    num = (scores * (events - total * p_bar)).sum()
    centred = scores - (total * scores).sum() / total.sum()
    den = math.sqrt(p_bar * (1 - p_bar) * (total * centred**2).sum())
    z = num / den
    return z, 2 * stats.norm.sf(abs(z))


# ---- 1. miss rate by start year ----
print(f'=== 1. miss rate by start year, {TREND[0]}-{TREND[1]} ===')
by_year, naive_by_year, rows = {}, {}, []
for r in results:
    if not in_window(meta, r['nct'], TREND):
        continue
    y = year_of(meta, r['nct'])
    if r['win'] is not None:
        miss = int(r['win'] is False)
        by_year.setdefault(y, [0, 0])[miss] += 1
        rows.append((y, miss, sponsor_of(meta, r['nct'])))
    if valid_p(r['min_p']):
        naive_by_year.setdefault(y, [0, 0])[int(r['min_p'] >= ALPHA)] += 1
years = sorted(by_year)
rates = {y: 100 * by_year[y][1] / sum(by_year[y]) for y in years}
z_ca, p_ca = cochran_armitage(by_year)
print(f'  Cochran-Armitage z = {z_ca:.2f}, p = {p_ca:.3f}')
yr = np.array([r[0] for r in rows], float)
mi = np.array([r[1] for r in rows], float)
sp = np.array([r[2] for r in rows])
fit = sm.GLM(mi, sm.add_constant(yr - yr.mean()), family=binomial).fit(
    cov_type='cluster', cov_kwds={'groups': sp}
)
slope, se = fit.params[1], fit.bse[1]
print(
    f'  logistic odds ratio per year {math.exp(slope):.3f} '
    f'[{math.exp(slope - 1.96 * se):.3f}, {math.exp(slope + 1.96 * se):.3f}], '
    f'p = {fit.pvalues[1]:.3f} (sponsor-clustered)'
)
chi2, p_het, dof, _ = stats.chi2_contingency(
    np.array([[by_year[y][1], by_year[y][0]] for y in years])
)
low = min(years, key=lambda y: rates[y])
high = max(years, key=lambda y: rates[y])
print(
    f'  homogeneity across years: chi2 = {chi2:.1f}, dof = {dof}, '
    f'p = {p_het:.3f}'
)
print(
    f'  yearly rate from {rates[low]:.1f}% ({low}) to {rates[high]:.1f}% '
    f'({high}); {rates[years[0]]:.1f}% in {years[0]}, '
    f'{rates[years[-1]]:.1f}% in {years[-1]}'
)
z_naive, p_naive = cochran_armitage(naive_by_year)
print(
    f'  naive rule (operator stripped): z = {z_naive:.2f}, p = {p_naive:.3f}'
)
nums.text('trend.firstYear', TREND[0])
nums.text('trend.lastYear', TREND[1])
nums.fixed('trend.ca.z', z_ca, 2)
nums.p('trend.ca.p', p_ca)
nums.fixed('trend.or', math.exp(slope), 2)
nums.fixed('trend.or.lo', math.exp(slope - 1.96 * se), 2)
nums.fixed('trend.or.hi', math.exp(slope + 1.96 * se), 2)
nums.p('trend.or.p', fit.pvalues[1])
nums.fixed('trend.het.chi2', chi2, 1)
nums.count('trend.het.dof', dof)
nums.p('trend.het.p', p_het)
nums.pct('trend.min.pct', rates[low])
nums.text('trend.min.year', low)
nums.pct('trend.max.pct', rates[high])
nums.text('trend.max.year', high)
nums.count('trend.overall.trials', len(mi))
nums.share('trend.overall', int(mi.sum()), len(mi))
nums.pct('trend.first.pct', rates[years[0]])
nums.pct('trend.last.pct', rates[years[-1]])
nums.fixed('trend.naive.z', z_naive, 2)
nums.p('trend.naive.p', p_naive)
# the yearly rates with their Wilson intervals, which the figure draws
for y in years:
    n_year = sum(by_year[y])
    lo, hi = wilson(by_year[y][1], n_year)
    nums.count(f'trend.year.{y}.trials', n_year)
    nums.share(f'trend.year.{y}.miss', by_year[y][1], n_year)
    nums.pct(f'trend.year.{y}.miss.lo', lo)
    nums.pct(f'trend.year.{y}.miss.hi', hi)
write_table(
    'yearly',
    [
        [
            y,
            f'{sum(by_year[y]):,}'.replace(',', '{,}'),
            by_year[y][1],
            f'{rates[y]:.1f}',
        ]
        for y in years
    ],
)

# ---- 2. sponsor-class contrast in the miss rate ----
print('\n=== 2. sponsor-class contrast in the miss rate, 2017-2026 ===')
nb, kb, rb = miss_rate(results, meta, ERA, subset=big)
ne, ke, re_ = miss_rate(results, meta, ERA, subset=lambda n: not big(n))
z, p = sm.stats.proportions_ztest([kb, ke], [nb, ne])
print(
    f'  big pharma {rb:.1f}% ({kb}/{nb}) vs all other sponsors {re_:.1f}% '
    f'({ke}/{ne}): z = {z:.1f}, p = {p:.1e}'
)
contrast = [
    (int(r['win'] is False), int(big(r['nct'])), cluster_of(r['nct']))
    for r in results
    if r['win'] is not None and in_window(meta, r['nct'], ERA)
]
fit = sm.GLM(
    np.array([c[0] for c in contrast], float),
    sm.add_constant(np.array([c[1] for c in contrast], float)),
    family=binomial,
).fit(
    cov_type='cluster', cov_kwds={'groups': np.array([c[2] for c in contrast])}
)
print(
    f'  odds ratio {math.exp(fit.params[1]):.2f}, program-clustered '
    f'p = {fit.pvalues[1]:.1e}'
)
nums.count('sponsor.big.trials', nb)
nums.share('sponsor.big.miss', kb, nb)
nums.count('sponsor.rest.trials', ne)
nums.share('sponsor.rest.miss', ke, ne)
nums.fixed('sponsor.z', z, 1)
nums.p('sponsor.p', p)
nums.fixed('sponsor.or', math.exp(fit.params[1]), 2)
nums.p('sponsor.or.p', fit.pvalues[1])

# ---- 3. big-pharma efficacy share against Hwang et al. ----
print('\n=== 3. big-pharma efficacy share against Hwang et al. ===')
h_k, h_n = HWANG['efficacy'], HWANG['failed']
h_p = h_k / h_n
h_lo, h_hi = wilson(h_k, h_n)
h_other = h_n - h_k - HWANG['safety'] - HWANG['commercial']
print(
    f'  Hwang: {h_k}/{h_n} = {100 * h_p:.1f}% [{h_lo:.1f}, {h_hi:.1f}]; '
    f'safety {HWANG["safety"]}, commercial {HWANG["commercial"]}, '
    f'no reason given {h_other}'
)
nums.count('hwang.programs', HWANG['programs'])
nums.count('hwang.failed', h_n)
for key, k in (
    ('eff', h_k),
    ('saf', HWANG['safety']),
    ('com', HWANG['commercial']),
    ('other', h_other),
):
    lo, hi = wilson(k, h_n)
    nums.share(f'hwang.{key}', k, h_n)
    nums.pct(f'hwang.{key}.lo', lo)
    nums.pct(f'hwang.{key}.hi', hi)
for skey, subset in (('all', None), ('big', big)):
    d = decompose(results, meta, stopcat, ERA, subset=subset)
    fold = (HWANG['safety'] / h_n) / (d['saf'] / d['den'])
    print(f'  safety share, {skey} sponsors: {fold:.1f} times below Hwang')
    nums.fixed(f'hwang.safetyFold.{skey}', fold, 0)


def against_hwang(key, label, window, include_withdrawn, big=big):
    _, _, stops = load(include_withdrawn=include_withdrawn)
    fails = [
        (1, cluster_of(r['nct']))
        for r in results
        if r['win'] is False
        and r['status'] == 'COMPLETED'
        and r['nct'] not in stops
        and in_window(meta, r['nct'], window)
        and big(r['nct'])
    ]
    fails += [
        (int(c in EFFICACY), cluster_of(n))
        for n, c in stops.items()
        if in_window(meta, n, window) and big(n) and c not in SUCCESS
    ]
    y = np.array([f[0] for f in fails], float)
    groups = np.array([f[1] for f in fails])
    k, n = int(y.sum()), len(y)
    share = k / n
    _, p = sm.stats.proportions_ztest([k, h_k], [n, h_n])
    fit = sm.GLM(y, np.ones((n, 1)), family=binomial).fit(
        cov_type='cluster', cov_kwds={'groups': groups}
    )
    b0, se0 = fit.params[0], fit.bse[0]

    def inv(t):
        return 1 / (1 + math.exp(-t))

    lo, hi = 100 * inv(b0 - 1.96 * se0), 100 * inv(b0 + 1.96 * se0)
    se_ours = se0 * share * (1 - share)  # delta method
    se_hwang = math.sqrt(h_p * (1 - h_p) / h_n)
    se_diff = math.sqrt(se_ours**2 + se_hwang**2)
    z_cl = (share - h_p) / se_diff
    p_cl = 2 * stats.norm.sf(abs(z_cl))
    d_lo = 100 * (share - h_p - 1.96 * se_diff)
    d_hi = 100 * (share - h_p + 1.96 * se_diff)
    print(
        f'  {label}: {k}/{n} = {100 * share:.1f}%, program-clustered CI '
        f'[{lo:.1f}, {hi:.1f}] ({len(set(groups))} programs); difference '
        f'{100 * (share - h_p):+.1f} points [{d_lo:+.1f}, {d_hi:+.1f}], '
        f'two-sample p = {p:.3f}, clustered p = {p_cl:.3f}'
    )
    nums.count(f'hwang.{key}.n', n)
    nums.share(f'hwang.{key}.eff', k, n)
    nums.count(f'hwang.{key}.clusters', len(set(groups)))
    nums.pct(f'hwang.{key}.clustered.lo', lo)
    nums.pct(f'hwang.{key}.clustered.hi', hi)
    nums.fixed(f'hwang.{key}.diff', abs(100 * (share - h_p)), 1)
    # this work minus Hwang et al., with the clustered standard error
    nums.fixed(f'hwang.{key}.diff.lo', d_lo, 1)
    nums.fixed(f'hwang.{key}.diff.hi', d_hi, 1)
    nums.p(f'hwang.{key}.p', p)
    nums.p(f'hwang.{key}.clustered.p', p_cl)


against_hwang('enrolled', 'enrolled, 2017-2026', ERA, False)
against_hwang('complete', 'enrolled, 2017-2022', ERA_COMPLETE, False)
against_hwang('registered', 'withdrawn counted, 2017-2026', ERA, True)
against_hwang('wide', 'with the mid-size companies', ERA, False, big=big_wide)

# ---- 4. therapeutic-area heterogeneity ----
print('\n=== 4. miss rate by therapeutic area, 2017-2026 ===')
AREAS_ORDER = [
    'Oncology',
    'Cardiometabolic',
    'Neuro/Psych',
    'Immunology/Inflammation',
    'Infectious/Vaccine',
    'Other/rare',
]
tab = {a: [0, 0] for a in AREAS_ORDER}  # area -> [win, miss]
infectious = {'before': [0, 0], 'from': [0, 0]}
for r in results:
    if r['win'] is None or not in_window(meta, r['nct'], ERA):
        continue
    a = area_of(cond, r['nct'])
    miss = int(r['win'] is False)
    if a in tab:
        tab[a][miss] += 1
    if a == 'Infectious/Vaccine':
        recent = in_window(meta, r['nct'], (INFECTIOUS_SPLIT, ERA[1]))
        era = 'from' if recent else 'before'
        infectious[era][miss] += 1
chi2, p, dof, _ = stats.chi2_contingency(
    np.array([[tab[a][1], tab[a][0]] for a in AREAS_ORDER])
)
for a in AREAS_ORDER:
    n = sum(tab[a])
    print(f'  {a:26s} miss {100 * tab[a][1] / n:4.1f}%  (n={n})')
    key = 'area.' + ''.join(c for c in a if c.isalpha())
    nums.count(key + '.trials', n)
    nums.share(key + '.miss', tab[a][1], n)
print(f'  heterogeneity chi2 = {chi2:.1f}, dof = {dof}, p = {p:.1e}')
nums.fixed('area.het.chi2', chi2, 1)
nums.count('area.het.dof', dof)
nums.p('area.het.p', p)
before, after = infectious['before'], infectious['from']
z, p = sm.stats.proportions_ztest(
    [before[1], after[1]], [sum(before), sum(after)]
)
print(
    f'  Infectious/Vaccine: starts before {INFECTIOUS_SPLIT} '
    f'{100 * before[1] / sum(before):.1f}% '
    f'(n={sum(before)}), from {INFECTIOUS_SPLIT} '
    f'{100 * after[1] / sum(after):.1f}% '
    f'(n={sum(after)}); z = {z:.1f}, p = {p:.3f}'
)
nums.text('area.infectious.split', INFECTIOUS_SPLIT)
nums.count('area.infectious.before.trials', sum(before))
nums.share('area.infectious.before.miss', before[1], sum(before))
nums.count('area.infectious.from.trials', sum(after))
nums.share('area.infectious.from.miss', after[1], sum(after))
nums.fixed('area.infectious.z', abs(z), 1)
nums.p('area.infectious.p', p)

# ---- 5. which completed trials report a usable primary p-value ----
print(
    '\n=== 5. reporting of a usable primary p-value, completed 2017-2026 ==='
)
rows = [
    (
        int(r['win'] is not None),
        int(big(r['nct'])),
        year_of(meta, r['nct']),
        r.get('n_prim') or 1,
        int(len((arms.get(r['nct']) or {}).get('armGroups', [])) == 1),
        area_of(cond, r['nct']),
        sponsor_of(meta, r['nct']),
    )
    for r in results
    if r['status'] == 'COMPLETED'
    and r['nct'] not in stopcat
    and in_window(meta, r['nct'], ERA)
]
reported = np.array([r[0] for r in rows], float)
year = np.array([r[2] for r in rows], float)
all_areas = sorted({r[5] for r in rows})
areas = all_areas[1:]  # the first is the reference category
nums.text('covmodel.reference', all_areas[0])
x = sm.add_constant(
    np.column_stack(
        [
            [r[1] for r in rows],
            year - year.mean(),
            np.log([r[3] for r in rows]),
            [r[4] for r in rows],
        ]
        + [[float(r[5] == a) for r in rows] for a in areas]
    )
)
fit = sm.GLM(reported, x, family=binomial).fit(
    cov_type='cluster', cov_kwds={'groups': np.array([r[6] for r in rows])}
)
names = ['const', 'bigPharma', 'year', 'logPrimaries', 'singleArm'] + [
    'area' + ''.join(c for c in a if c.isalpha()) for a in areas
]
labels = [
    'intercept',
    'big pharma',
    'start year (per year)',
    'number of primary outcomes (natural log)',
    'single-arm design',
] + [f'area: {a}' for a in areas]
print(f'  n = {len(rows)}; reporting {100 * reported.mean():.1f}%')
nums.count('covmodel.trials', len(rows))
table = []
for name, label, b, se, pv in zip(
    names, labels, fit.params, fit.bse, fit.pvalues
):
    if name == 'const':
        continue
    lo, hi = math.exp(b - 1.96 * se), math.exp(b + 1.96 * se)
    print(
        f'  {label:32s} OR {math.exp(b):5.2f} [{lo:.2f}, {hi:.2f}]  '
        f'p = {pv:.2g}'
    )
    nums.fixed(f'covmodel.{name}.or', math.exp(b), 2)
    nums.fixed(f'covmodel.{name}.lo', lo, 2)
    nums.fixed(f'covmodel.{name}.hi', hi, 2)
    nums.p(f'covmodel.{name}.p', pv)
    table.append(
        [
            tex_escape(label),
            f'{math.exp(b):.2f}',
            f'{lo:.2f} to {hi:.2f}',
            f'${nums.entries[f"covmodel.{name}.p"]["tex"]}$',
        ]
    )
write_table('covmodel', table)
nums.save()
