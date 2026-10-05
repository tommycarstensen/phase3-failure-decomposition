"""Program-level view: reduce the results cohort to distinct subject drugs.

Each trial's subject is its experimental-arm drug that is rarest across the
cohort (subjects.py). A program is the set of trials sharing a subject, and it
wins if any of its trials wins. The program-level rate is descriptive; the
subjects are used elsewhere as clusters for robust standard errors and for
the novel-versus-lifecycle flag.
"""

from collections import defaultdict

import subjects
from failure_decomp import load
from paper_numbers import Numbers, write_table
from repo_files import REGISTRY, read_json

arms = read_json(REGISTRY + 'ph3_arms.json')
results, _meta, _stopcat = load()
subject_of, freq, backbone = subjects.build(arms, results)
nums = Numbers('dedup_arms')


def arm_types(nct):
    return [g.get('type') for g in (arms.get(nct) or {}).get('armGroups', [])]


total = len(results)
with_arms = sum(1 for r in results if arm_types(r['nct']))
with_experimental = sum(
    1 for r in results if 'EXPERIMENTAL' in arm_types(r['nct'])
)
programs = defaultdict(set)
for r in results:
    drug = subject_of(r['nct'])
    if drug:
        programs[drug].add(r['nct'])
with_subject = sum(len(v) for v in programs.values())

print(f'results-posting trials: {total}')
print(
    f'  with arm groups recorded: {with_arms} ({100 * with_arms / total:.1f}%)'
)
print(
    f'  with an experimental arm: {with_experimental} '
    f'({100 * with_experimental / total:.1f}%)'
)
print(f'  with a subject drug: {with_subject}')
print(f'comparator or backbone drugs set aside: {len(backbone)}')
print(f'distinct subject drugs: {len(programs)}')
top = sorted(programs.items(), key=lambda x: (-len(x[1]), x[0]))[:10]
for drug, ncts in top:
    print(f'  {len(ncts):3d}  {drug}')

win_of = {r['nct']: r['win'] for r in results}
judged = [
    any(v)
    for v in (
        [win_of[n] for n in ncts if win_of[n] is not None]
        for ncts in programs.values()
    )
    if v
]
wins = sum(judged)
print(f'programs with at least one verdict: {len(judged)}')
print(
    f'  at least one win: {wins} ({100 * wins / len(judged):.0f}%); no win: '
    f'{len(judged) - wins} ({100 * (len(judged) - wins) / len(judged):.0f}%)'
)

nums.share('dedup.withArms', with_arms, total)
nums.share('dedup.withExperimental', with_experimental, total)
nums.count('dedup.withSubject', with_subject)
nums.count('dedup.backbones', len(backbone))
nums.count('dedup.backboneMinTrials', subjects.BACKBONE_MIN_TRIALS)
nums.count('dedup.subjects', len(programs))
nums.count('dedup.programs.judged', len(judged))
nums.share('dedup.programs.win', wins, len(judged))
nums.share('dedup.programs.noWin', len(judged) - wins, len(judged))
half = len(top) // 2
write_table(
    'subjects',
    [
        [len(a[1]), a[0], '', len(b[1]), b[0]]
        for a, b in zip(top[:half], top[half:])
    ],
)
nums.save()
