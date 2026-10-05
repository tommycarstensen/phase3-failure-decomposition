"""The efficacy and operational shares under the two counting choices.

One panel for each population: trials that enrolled, and the same with
registrations withdrawn before enrollment counted as failures. In each panel
a row shows the share as observed, the share after imputing misses for
unreported completed trials with a comparator arm (at the pooled miss rate,
with the covariate-adjusted imputation as a tick), and the range up to the
bound in which every such trial missed. The figure draws the recorded
numbers (numbers/coverage.json). Run after coverage.py.
"""

import math

import matplotlib.pyplot as plt

from figure_palette import (
    BOUNDS,
    GRID,
    INK,
    INK_SECONDARY,
    RAW,
    THIS_WORK,
)
from figure_style import BASE, SMALL, WIDTH, save, start

numbers = start()


def value(name):
    return numbers[name]['value']


def text(name):
    return numbers[name]['txt']


PANELS = [
    ('A', 'Trials that enrolled (primary analysis)', 'coverage.enrolled.all'),
    (
        'B',
        'Registrations withdrawn before enrollment counted as failures',
        'coverage.registered.all',
    ),
]
ROWS = [('Efficacy', 'eff', 1.0), ('Operational', 'op', 0.0)]
# (recorded state, what it is, colour of its label); the first row of the
# first panel names the states, every row gives their values
STATES = [
    ('raw', 'as observed', INK),
    ('pooled', 'misses imputed', INK),
    ('upper', 'if all had missed', INK_SECONDARY),
]

fig, axes = plt.subplots(
    2,
    1,
    figsize=(WIDTH, 4.1),
    sharex=True,
    height_ratios=[1.17, 1],
    facecolor='white',
)
edges = []
for ax, (letter, title, key) in zip(axes, PANELS):
    for _, bucket, y in ROWS:
        observed = value(f'{key}.raw.{bucket}')
        pooled = value(f'{key}.pooled.{bucket}')
        adjusted = value(f'{key}.adjusted.{bucket}')
        bound = value(f'{key}.upper.{bucket}')
        edges += [observed, bound]
        ax.barh(
            y,
            abs(bound - observed),
            left=min(bound, observed),
            height=0.36,
            color=BOUNDS,
            edgecolor=GRID,
            linewidth=0.6,
            zorder=1,
        )
        ax.plot([observed, pooled], [y, y], color=INK, lw=1, zorder=2)
        ax.plot(
            [adjusted, adjusted],
            [y - 0.21, y + 0.21],
            color=THIS_WORK,
            lw=1.4,
            zorder=2,
        )
        for x, colour in ((observed, RAW), (pooled, THIS_WORK)):
            ax.plot(
                x,
                y,
                'o',
                markersize=7,
                color=colour,
                markeredgecolor=INK,
                markeredgewidth=0.9,
                zorder=4,
            )
        named = ax is axes[0] and bucket == ROWS[0][1]
        if named:
            ax.text(
                adjusted + 0.8,
                y,
                'covariate-adjusted',
                ha='left',
                va='center',
                fontsize=SMALL,
                color=THIS_WORK,
            )
        for state, what, colour in STATES:
            label = text(f'{key}.{state}.{bucket}') + '%'
            ax.text(
                value(f'{key}.{state}.{bucket}'),
                y + 0.27,
                f'{what}\n{label}' if named else label,
                ha='center',
                va='bottom',
                fontsize=SMALL,
                color=colour,
            )
    ax.set_yticks([y for _, _, y in ROWS])
    ax.set_yticklabels([label for label, _, _ in ROWS])
    ax.set_ylim(-0.5, 1.95 if ax is axes[0] else 1.7)
    ax.set_title(
        f'{letter}   {title}', fontweight='bold', loc='left', fontsize=BASE
    )
    ax.spines[['top', 'right']].set_visible(False)
    ax.grid(axis='x', color=GRID, lw=0.6, alpha=0.6)

era = f'{value("era.first")}–{value("era.last")}'
axes[-1].set_xlabel(f'Share of failures, all sponsors, starts {era} (%)')
# to the next multiple of five that leaves room for the outermost labels
axes[-1].set_xlim(
    5 * math.floor((min(edges) - 6) / 5), 5 * math.ceil((max(edges) + 6) / 5)
)
fig.tight_layout(pad=0.6, h_pad=1.2)
save(fig, 'ph3_coverage_correction')
