"""The share of completed trials with a usable primary p-value, by start
year.

For each start year from the first of the trend window to the last with
enough completed trials, the figure shows the share of completed,
non-stopped trials with posted results that carry a verdict, its Wilson 95%
interval and, under the year, the number of such trials. This is the size of
the second counting choice year by year. It draws the recorded numbers
(numbers/inference.json and numbers/coverage.json) in the style of
make_figure_missrate.py. Run after inference.py and coverage.py.
"""

import math

import matplotlib.pyplot as plt

from figure_palette import GRID, INK_SECONDARY, THIS_WORK
from figure_style import LINE_MAX, SMALL, WIDTH, save, start

numbers = start()


def value(name):
    return numbers[name]['value']


def text(name):
    return numbers[name]['txt']


first, last = value('reporting.firstYear'), value('reporting.lastYear')
years = list(range(first, last + 1))
share = [value(f'reporting.year.{y}.verdict.pct') for y in years]
low = [value(f'reporting.year.{y}.verdict.lo') for y in years]
high = [value(f'reporting.year.{y}.verdict.hi') for y in years]
top = 10 * math.ceil((max(high) + 6) / 10)
window = value('era.first')

fig, ax = plt.subplots(figsize=(WIDTH, 3.3), facecolor='white')
ax.fill_between(
    years,
    low,
    high,
    color=THIS_WORK,
    alpha=0.16,
    lw=0,
    zorder=1,
    label='Wilson 95% interval',
)
# the share of the main window as a whole, drawn over the main window only
ax.hlines(
    value('coverage.enrolled.all.reported.pct'),
    window - 0.5,
    last + 0.6,
    color=INK_SECONDARY,
    ls='--',
    lw=1,
    zorder=2,
    label=(
        f'main window, {text("coverage.enrolled.all.reported.pct")}% overall'
    ),
)
ax.plot(
    years,
    share,
    '-o',
    color=THIS_WORK,
    lw=LINE_MAX,
    markersize=4.5,
    markeredgecolor='white',
    markeredgewidth=0.8,
    zorder=3,
    label='yearly share',
)
# where the main window of the decomposition begins: a date, not an effect
ax.axvline(window - 0.5, color=INK_SECONDARY, ls=':', lw=1, zorder=2)
ax.text(
    window - 0.4,
    top - 1,
    f'main window,\nstarts from {window}',
    ha='left',
    va='top',
    fontsize=SMALL,
    color=INK_SECONDARY,
)
ax.set_xticks(years)
ax.set_xticklabels(
    [f'{y}\n{text(f"reporting.year.{y}.trials")}' for y in years],
    fontsize=SMALL,
)
ax.set_xlabel(
    'Trial start year, and the number of completed trials with posted results'
)
ax.set_ylabel('With a usable primary p-value\n(% of completed trials)')
ax.set_xlim(first - 0.6, last + 0.6)
ax.set_ylim(0, top)
handles, labels = ax.get_legend_handles_labels()
order = [2, 0, 1]  # the share, its interval, then the reference line
ax.legend(
    [handles[i] for i in order],
    [labels[i] for i in order],
    loc='lower left',
    frameon=False,
)
ax.spines[['top', 'right']].set_visible(False)
ax.grid(axis='y', color=GRID, lw=0.6, alpha=0.6)
ax.set_axisbelow(True)
fig.tight_layout(pad=0.6)
save(fig, 'ph3_reporting_by_year')
