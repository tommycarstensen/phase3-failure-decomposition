"""How often a stopped trial's reason can be recovered from the registry.

For stopped trials that are failures (stopped-for-benefit excluded) the script
reports, after each classification pass, the share left without a reason. Two
definitions are given side by side:

  unclear    the label is 'unclear'
  no reason  the label is 'unclear', 'sponsor_undisclosed' or 'not_started':
             the last two say that a trial stopped, not why

The primary population is trials that enrolled; the same figures with
registrations withdrawn before enrollment are reported as a sensitivity.
"""

from failure_decomp import (
    ALL_YEARS,
    ERA,
    NO_REASON,
    SUCCESS,
    in_window,
    load,
)
from paper_numbers import Numbers
from repo_files import LABELS, REGISTRY, read_json, read_labels

results, meta, final = load(include_withdrawn=True)
first = read_labels('why_out')  # first pass: the whyStopped string
second = read_json(LABELS + 'unclear_reclassified.json')  # second pass
stopped = read_json(REGISTRY + 'ph3_stopped.json')
nums = Numbers('recoverability')


def shares(ncts, label_of):
    """(n, unclear, no reason) over the failures among ncts."""
    labels = [label_of(n) for n in ncts]
    labels = [lab for lab in labels if lab not in SUCCESS]
    n = len(labels)
    unclear = sum(lab == 'unclear' for lab in labels)
    none = sum(lab in NO_REASON for lab in labels)
    return n, unclear, none


STAGES = [
    ('first', 'whyStopped string only', lambda n: first.get(n, 'unclear')),
    (
        'second',
        '+ description, enrollment, status',
        lambda n: second.get(n) or first.get(n, 'unclear'),
    ),
    ('final', '+ linked publications', lambda n: final[n]),
]
POPULATIONS = [
    ('enrolled', 'trials that enrolled', lambda s: s['status'] != 'WITHDRAWN'),
    ('registered', 'all stopped registrations', lambda s: True),
]

for pkey, plabel, keep in POPULATIONS:
    for wkey, wlabel, window in [
        ('era', f'{ERA[0]}-{ERA[1]}', ERA),
        ('all', 'all years', ALL_YEARS),
    ]:
        ncts = [
            s['nct']
            for s in stopped
            if keep(s) and in_window(meta, s['nct'], window)
        ]
        print(f'=== {plabel}, {wlabel} ===')
        for skey, slabel, label_of in STAGES:
            n, unclear, none = shares(ncts, label_of)
            print(
                f'  {slabel:34s} n={n:5d}  unclear {unclear:4d} '
                f'({100 * unclear / n:4.1f}%)  no reason {none:4d} '
                f'({100 * none / n:4.1f}%)'
            )
            key = f'recover.{pkey}.{wkey}.{skey}'
            nums.count(key + '.n', n)
            nums.share(key + '.unclear', unclear, n)
            nums.share(key + '.noReason', none, n)
            nums.pct(key + '.reason.pct', 100 * (n - none) / n)
            nums.pct(key + '.notUnclear.pct', 100 * (n - unclear) / n)
        labels = [final[n] for n in ncts if final[n] not in SUCCESS]
        for lab in ('sponsor_undisclosed', 'not_started'):
            k = sum(x == lab for x in labels)
            print(f'    final label {lab}: {k}')
            nums.count(
                f'recover.{pkey}.{wkey}.final.{lab.replace("_", "")}', k
            )

blank = sum(1 for s in stopped if not (s['why'] or '').strip())
print(f'stopped registrations with a blank whyStopped: {blank}')
nums.count('recover.blankWhyStopped', blank)
nums.count('recover.firstPassLabels', len(first))
nums.save()
