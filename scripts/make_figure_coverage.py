"""The efficacy and operational shares under the two counting choices.

One panel for each population: trials that enrolled, and the same with
registrations withdrawn before enrollment counted as failures. In each panel
a row shows the share as observed, the share after imputing misses for
unreported completed trials with a comparator arm (at the pooled miss rate,
with the covariate-adjusted imputation as a tick), and the range up to the
bound in which every such trial missed. Above each panel stands the
difference between the two shares as observed, with its program-clustered
95% interval, and a key under the panels says that the band is the range of
an assumption, not a confidence interval. The figure draws the recorded
numbers (numbers/coverage.json and numbers/inference.json). Run after
coverage.py and inference.py.
"""

import math

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

from figure_palette import (
    BOUNDS,
    BOUNDS_EDGE,
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


def signed(name):
    """A recorded number as text, with a typographic minus sign."""
    return text(name).replace('-', '−')


def difference(first, second, key):
    """The difference of the two shares as observed, with its interval."""
    return (
        f'As observed, {first} minus {second} is {signed(key)} points '
        f'(clustered 95% CI {signed(key + ".lo")} to {signed(key + ".hi")})'
    )


PANELS = [
    (
        'A',
        'Trials that enrolled (primary analysis)',
        'coverage.enrolled.all',
        difference('efficacy', 'operational', 'order.enrolled.diff'),
    ),
    (
        'B',
        'Withdrawn registrations counted as failures',
        'coverage.registered.all',
        difference('operational', 'efficacy', 'order.registered.diff'),
    ),
]
ROWS = [('Efficacy', 'eff', 1.0), ('Operational', 'op', 0.0)]
# (recorded state, what it is, colour of its label); the first row of each
# panel names the states, every row gives their values
STATES = [
    ('raw', 'as observed', INK),
    ('pooled', 'misses imputed', INK),
    ('upper', 'if all had missed', INK_SECONDARY),
]
MARKER = {'markersize': 7, 'markeredgecolor': INK, 'markeredgewidth': 0.9}

fig, axes = plt.subplots(
    2, 1, figsize=(WIDTH, 4.8), sharex=True, facecolor='white'
)
edges = []
for ax, (letter, title, key, lead) in zip(axes, PANELS):
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
            edgecolor=BOUNDS_EDGE,
            linewidth=0.8,
            zorder=1,
        )
        ax.plot([observed, pooled], [y, y], color=INK, lw=1, zorder=2)
        ax.plot(
            [adjusted, adjusted],
            [y - 0.24, y + 0.24],
            color=THIS_WORK,
            lw=1.4,
            zorder=2,
        )
        for x, colour in ((observed, RAW), (pooled, THIS_WORK)):
            ax.plot(x, y, 'o', color=colour, zorder=4, **MARKER)
        named = bucket == ROWS[0][1]
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
    ax.set_ylim(-0.5, 1.95)
    ax.set_title(
        f'{letter}   {title}',
        fontweight='bold',
        loc='left',
        fontsize=BASE,
        pad=15,
    )
    ax.text(
        0,
        1.03,
        lead,
        transform=ax.transAxes,
        ha='left',
        va='bottom',
        fontsize=SMALL,
        color=INK,
    )
    ax.spines[['top', 'right']].set_visible(False)
    ax.grid(axis='x', color=GRID, lw=0.6, alpha=0.6)
    ax.set_axisbelow(True)

era = f'{value("era.first")}–{value("era.last")}'
axes[-1].set_xlabel(f'Share of failures, all sponsors, starts {era} (%)')
# to the next multiple of five that leaves room for the outermost labels
axes[-1].set_xlim(
    5 * math.floor((min(edges) - 6) / 5), 5 * math.ceil((max(edges) + 6) / 5)
)
key = [
    Line2D([], [], ls='', marker='o', color=RAW, **MARKER),
    Line2D([], [], ls='', marker='o', color=THIS_WORK, **MARKER),
    Line2D([], [], ls='', marker='|', color=THIS_WORK, markersize=10, mew=1.4),
    Patch(facecolor=BOUNDS, edgecolor=BOUNDS_EDGE, linewidth=0.8),
]
fig.legend(
    key,
    [
        'as observed',
        'misses imputed',
        'covariate-adjusted imputation',
        'range to all such trials missed, an assumption, not a CI',
    ],
    loc='lower center',
    ncol=2,
    fontsize=SMALL,
    frameon=False,
    handlelength=1.6,
    columnspacing=2.0,
)
fig.tight_layout(pad=0.6, h_pad=1.2, rect=(0, 0.1, 1, 1))
save(fig, 'ph3_coverage_correction')
