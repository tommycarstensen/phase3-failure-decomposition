"""Novel-versus-lifecycle check on the big-pharma stratum.

Hwang et al. studied novel therapeutics. A big-pharma trial may instead test
a drug that already has a phase-3 win (a label expansion or a new
formulation). Each trial's subject drug is flagged:

  lifecycle  the drug has a phase-3 win in the corpus with a start year
             strictly before this trial's
  novel      it has none

The flag can only see wins inside the corpus, so a drug validated before the
registry's results era, or in trials without a usable p-value, is called
novel. The novel group is therefore contaminated with lifecycle trials, which
works against finding a difference between the groups.
"""

import subjects
from failure_decomp import (
    ERA,
    decompose,
    is_bigpharma,
    load,
    miss_rate,
    sponsor_of,
    wilson,
    year_of,
)
from paper_numbers import Numbers, write_table
from repo_files import REGISTRY, read_json

results, meta, stopcat = load()
arms = read_json(REGISTRY + 'ph3_arms.json')
subject_of, _, _ = subjects.build(arms, results)
nums = Numbers('novelty_flag')

is_lifecycle = subjects.lifecycle_flag(
    results, subject_of, lambda nct: year_of(meta, nct)
)


def big(n):
    return is_bigpharma(sponsor_of(meta, n))


CUTS = [
    ('all', 'big pharma, all', big),
    (
        'novel',
        'big pharma, novel',
        lambda n: big(n) and is_lifecycle(n) is False,
    ),
    (
        'lifecycle',
        'big pharma, lifecycle',
        lambda n: big(n) and is_lifecycle(n) is True,
    ),
    (
        'unflagged',
        'big pharma, no subject drug',
        lambda n: big(n) and is_lifecycle(n) is None,
    ),
]
print('=== big-pharma failures 2017-2026: novel and lifecycle subjects ===')
table = []
for key, label, cut in CUTS:
    d = decompose(results, meta, stopcat, ERA, subset=cut)
    n, m, rate = miss_rate(results, meta, ERA, subset=cut)
    den = d['den']
    pct = {b: 100 * d[b] / den for b in ('eff', 'op', 'com', 'saf', 'unk')}
    print(
        f'  {label:28s} failures {den:4d}  miss {rate:4.1f}% (n={n})  '
        + '  '.join(f'{b} {v:4.1f}' for b, v in pct.items())
    )
    nums.count(f'novelty.{key}.n', den)
    nums.count(f'novelty.{key}.miss.trials', n)
    nums.share(f'novelty.{key}.miss', m, n)
    for b in pct:
        nums.share(f'novelty.{key}.{b}', d[b], den)
    table.append(
        [label, den, f'{rate:.1f}']
        + [f'{pct[b]:.1f}' for b in ('eff', 'op', 'com', 'saf', 'unk')]
    )
write_table('novelty', table[:3])

# The Wilson interval of the novel subset's efficacy share. Its comparison
# with Hwang et al., who studied novel therapeutics, is in inference.py with
# the other comparisons, so that it is clustered by program in the same way.
cuts = {key: cut for key, _, cut in CUTS}
novel = decompose(results, meta, stopcat, ERA, subset=cuts['novel'])
lo, hi = wilson(novel['eff'], novel['den'])
print(
    f"  novel: {novel['eff']}/{novel['den']} = "
    f"{100 * novel['eff'] / novel['den']:.1f}% [{lo:.1f}, {hi:.1f}]"
)
nums.pct('novelty.novel.eff.lo', lo)
nums.pct('novelty.novel.eff.hi', hi)
nums.save()
