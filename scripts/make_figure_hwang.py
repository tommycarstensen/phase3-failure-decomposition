"""The big-pharma efficacy share under each counting choice, against the
estimate of Hwang et al. 2016.

One row per choice: trials that enrolled (the primary analysis), the same in
the window that has read out, withdrawn registrations counted as failures,
the stratum widened by the mid-size companies, and, set apart below, trials
that enrolled with unreported misses imputed. An observed share carries its
program-clustered 95% interval. The imputed share has no such interval and
is drawn with the range from none to all of the unreported trials with a
comparator arm having missed. The label of Hwang et al. names their unit and
years, so that the figure cannot be read as a like-for-like benchmark, and
their line is dashed, so that it stays apart from the grid in greyscale. The
figure draws the recorded numbers (numbers/inference.json,
numbers/coverage.json and numbers/literature.json). Run after inference.py
and coverage.py.
"""

import math

import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator

from figure_palette import (
    BOUNDS,
    BOUNDS_EDGE,
    GRID,
    HWANG,
    INK,
    INK_SECONDARY,
    RAW,
    THIS_WORK,
    tint,
)
from figure_style import LINE_MAX, SMALL, WIDTH, save, start

numbers = start()


def value(name):
    return numbers[name]['value']


def text(name):
    return numbers[name]['txt']


first, last = value('era.first'), value('era.last')
complete = value('era.completeLast')
mid = value('bigpharma.mid')
# (row label, recorded name) of the observed shares, in the order of the
# text; every row starts in the main window unless its label says otherwise
OBSERVED = [
    ('Trials that enrolled\n(primary analysis)', 'hwang.enrolled'),
    (f'Trials that enrolled,\nstarts {first}–{complete}', 'hwang.complete'),
    ('Withdrawn registrations\ncounted as failures', 'hwang.registered'),
    (f'{mid} mid-size companies\nadded to the stratum', 'hwang.wide'),
]
IMPUTED = 'coverage.enrolled.big'
labels = [label for label, _ in OBSERVED]
labels.append('Unreported misses imputed\n(a range, not an interval)')
# the imputed row stands apart below the observed ones
rows = [len(OBSERVED) + 0.5 - i for i in range(len(OBSERVED))] + [0]

fig, ax = plt.subplots(figsize=(WIDTH, 3.4), facecolor='white')
across = ax.get_yaxis_transform()  # x in axes fractions, y in data units

# the estimate of Hwang et al. with its Wilson interval
ax.axvspan(
    value('hwang.eff.lo'), value('hwang.eff.hi'), color=tint(HWANG, 0.3), lw=0
)
ax.axvline(
    value('hwang.eff.pct'), color=HWANG, lw=LINE_MAX, linestyle=(0, (5, 2))
)
years = f'{text("lit.hwang.firstYear")}–{text("lit.hwang.lastYear")}'
ax.text(
    value('hwang.eff.pct'),
    1.02,
    f'Hwang et al. 2016, {text("hwang.eff.pct")}% '
    f'(Wilson 95% CI {text("hwang.eff.lo")} to {text("hwang.eff.hi")})\n'
    f'drug programs that entered pivotal trials in {years}',
    transform=ax.get_xaxis_transform(),
    ha='center',
    va='bottom',
    fontsize=SMALL,
    color=INK,
)
ax.text(
    1.02,
    rows[0] + 0.6,
    'Share (clustered 95% CI)',
    transform=across,
    ha='left',
    va='bottom',
    fontsize=SMALL,
    color=INK_SECONDARY,
)

edges = [value('hwang.eff.lo'), value('hwang.eff.hi')]
for row, (_, key) in zip(rows, OBSERVED):
    share = value(f'{key}.eff.pct')
    low, high = value(f'{key}.clustered.lo'), value(f'{key}.clustered.hi')
    edges += [low, high]
    ax.errorbar(
        share,
        row,
        xerr=[[share - low], [high - share]],
        fmt='o',
        markersize=7,
        markerfacecolor=RAW,
        markeredgecolor=INK,
        markeredgewidth=0.9,
        ecolor=INK,
        elinewidth=1,
        capsize=2.5,
        zorder=3,
    )
    ax.text(
        1.02,
        row,
        f'{text(f"{key}.eff.pct")}% ({text(f"{key}.clustered.lo")} to '
        f'{text(f"{key}.clustered.hi")})',
        transform=across,
        ha='left',
        va='center',
        fontsize=SMALL,
        color=INK,
    )

row = rows[-1]
none, every = value(f'{IMPUTED}.raw.eff'), value(f'{IMPUTED}.upper.eff')
edges += [none, every]
ax.barh(
    row,
    every - none,
    left=none,
    height=0.42,
    color=BOUNDS,
    edgecolor=BOUNDS_EDGE,
    linewidth=0.8,
    zorder=1,
)
ax.plot(
    value(f'{IMPUTED}.pooled.eff'),
    row,
    'o',
    markersize=7,
    color=THIS_WORK,
    markeredgecolor=INK,
    markeredgewidth=0.9,
    zorder=3,
)
ax.text(
    1.02,
    row,
    f'{text(f"{IMPUTED}.pooled.eff")}% (range {text(f"{IMPUTED}.raw.eff")} '
    f'to {text(f"{IMPUTED}.upper.eff")})',
    transform=across,
    ha='left',
    va='center',
    fontsize=SMALL,
    color=INK,
)

ax.set_yticks(rows)
ax.set_yticklabels(labels, fontsize=SMALL)
ax.get_yticklabels()[0].set_fontweight('bold')
ax.set_ylim(-0.6, rows[0] + 0.6)
# to the next multiple of five that leaves room beyond the outermost edge
ax.set_xlim(
    5 * math.floor((min(edges) - 2) / 5), 5 * math.ceil((max(edges) + 2) / 5)
)
ax.xaxis.set_major_locator(MultipleLocator(10))
ax.set_xlabel(
    'Efficacy share of failures, big-pharma stratum, '
    f'starts {first}–{last} unless stated (%)'
)
ax.spines[['top', 'right']].set_visible(False)
ax.grid(axis='x', color=GRID, lw=0.6, alpha=0.6)
ax.set_axisbelow(True)
fig.tight_layout(pad=0.6)
save(fig, 'ph3_bigpharma_vs_hwang')
