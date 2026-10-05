"""Causes of phase-3 failure in Hwang et al. 2016 and in this work (big-pharma
stratum, other sponsors and all sponsors, trials that enrolled).

Each bar is a share of failures with its Wilson 95% interval. The figure
draws the recorded numbers (numbers/decomposition.json and
numbers/inference.json), so it cannot differ from the text. Run after
decomposition.py and inference.py.
"""

import matplotlib.pyplot as plt
import numpy as np
from matplotlib import patheffects
from matplotlib.patches import Patch

from figure_palette import (
    HWANG,
    INK,
    INK_SECONDARY,
    THIS_WORK,
    THIS_WORK_CONTEXT,
    THIS_WORK_REST,
)
from figure_style import SMALL, WIDTH, save, start

numbers = start()


def value(name):
    return numbers[name]['value']


def text(name):
    return numbers[name]['txt']


# the buckets in the order of the text
BUCKETS = [
    ('Efficacy', 'eff'),
    ('Operational', 'op'),
    ('Commercial', 'com'),
    ('Safety', 'saf'),
    ('Unknown', 'unk'),
]
# Hwang et al. report no operational category; their failures with none of
# the three stated reasons are drawn in the Unknown row.
HWANG_KEY = {'eff': 'eff', 'com': 'com', 'saf': 'saf', 'unk': 'other'}
SERIES = [
    ('hwang', 'Hwang et al. 2016', 'hwang.failed', 'programs', HWANG),
    ('big', 'This work, big pharma', None, 'trials', THIS_WORK),
    ('rest', 'This work, other sponsors', None, 'trials', THIS_WORK_REST),
    ('all', 'This work, all sponsors', None, 'trials', THIS_WORK_CONTEXT),
]


# a white edge keeps a whisker visible where it crosses a dark bar
HALO: list[patheffects.AbstractPathEffect] = [
    patheffects.withStroke(linewidth=2.2, foreground='white')
]


def share_name(stratum, bucket):
    """The recorded name of a share, or None where there is no such share."""
    if stratum != 'hwang':
        return f'decomp.enrolled.era.{stratum}.{bucket}'
    if bucket not in HWANG_KEY:
        return None
    return f'hwang.{HWANG_KEY[bucket]}'


fig, ax = plt.subplots(figsize=(WIDTH, 5.0), facecolor='white')
rows = np.arange(len(BUCKETS))[::-1]
height = 0.2
offsets = [((len(SERIES) - 1) / 2 - i) * height for i in range(len(SERIES))]
longest = 0.0
for row, (_, bucket) in zip(rows, BUCKETS):
    for (stratum, *_, colour), offset in zip(SERIES, offsets):
        name = share_name(stratum, bucket)
        if name is None:
            ax.text(
                0.7,
                row + offset,
                'no such category',
                va='center',
                ha='left',
                fontsize=SMALL,
                color=INK_SECONDARY,
            )
            continue
        share = value(name + '.pct')
        low, high = value(name + '.lo'), value(name + '.hi')
        longest = max(longest, high)
        ax.barh(
            row + offset,
            share,
            height,
            color=colour,
            edgecolor=INK,
            linewidth=0.6,
        )
        whisker = ax.errorbar(
            share,
            row + offset,
            xerr=[[share - low], [high - share]],
            fmt='none',
            ecolor=INK,
            elinewidth=0.8,
            capsize=1.6,
        )
        _, caps, stems = whisker.lines
        for line in (*caps, *stems):
            line.set_path_effects(HALO)
        ax.text(
            high + 0.8,
            row + offset,
            text(name + '.pct') + '%',
            va='center',
            ha='left',
            fontsize=SMALL,
            color=INK,
        )
ax.set_yticks(rows)
ax.set_yticklabels([name for name, _ in BUCKETS])
ax.set_xlabel('Share of failures (%), with its Wilson 95% interval')
ax.set_xlim(0, longest + 7)  # room for the label of the longest bar
ax.set_ylim(rows.min() - 0.62, rows.max() + 0.62)
ax.legend(
    handles=[
        Patch(
            fc=colour,
            ec=INK,
            lw=0.6,
            label=(
                f'{label}: '
                f'{text(n or f"decomp.enrolled.era.{stratum}.n")} '
                f'failed {unit}'
            ),
        )
        for stratum, label, n, unit, colour in SERIES
    ],
    loc='lower right',
    frameon=True,
)
ax.spines[['top', 'right']].set_visible(False)
fig.tight_layout(pad=0.6)
save(fig, 'ph3_failure_2016_vs_2026')
