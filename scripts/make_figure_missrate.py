"""The primary-endpoint miss rate by start year.

For each start year of the trend window the figure shows the share of trials
with a verdict that missed their primary endpoint, its Wilson 95% interval
and, under the year, the number of trials with a verdict. It draws the
recorded numbers (numbers/inference.json). Run after inference.py.
"""

import math

import matplotlib.pyplot as plt

from figure_palette import GRID, INK_SECONDARY, THIS_WORK
from figure_style import SMALL, WIDTH, save, start

numbers = start()


def value(name):
    return numbers[name]['value']


def text(name):
    return numbers[name]['txt']


first, last = value('trend.firstYear'), value('trend.lastYear')
years = list(range(first, last + 1))
rate = [value(f'trend.year.{y}.miss.pct') for y in years]
low = [value(f'trend.year.{y}.miss.lo') for y in years]
high = [value(f'trend.year.{y}.miss.hi') for y in years]
top = 10 * math.ceil((max(high) + 2) / 10)
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
ax.axhline(
    value('trend.overall.pct'),
    color=INK_SECONDARY,
    ls='--',
    lw=1,
    zorder=2,
    label=f'all starts {first}–{last}: {text("trend.overall.pct")}%',
)
ax.plot(
    years,
    rate,
    '-o',
    color=THIS_WORK,
    lw=1.6,
    markersize=4.5,
    markeredgecolor='white',
    markeredgewidth=0.8,
    zorder=3,
    label='yearly rate',
)
# where the main window of the decomposition begins: a date, not an effect
ax.axvline(window - 0.5, color=INK_SECONDARY, ls=':', lw=1, zorder=2)
ax.text(
    window - 0.4,
    top - 1,
    f'main window:\nstarts from {window}',
    ha='left',
    va='top',
    fontsize=SMALL,
    color=INK_SECONDARY,
)
ax.set_xticks(years)
ax.set_xticklabels(
    [f'{y}\n{text(f"trend.year.{y}.trials")}' for y in years], fontsize=SMALL
)
ax.set_xlabel('Trial start year, and the number of trials with a verdict')
ax.set_ylabel('Missed the primary endpoint\n(% of trials with a verdict)')
ax.set_xlim(first - 0.6, last + 0.6)
ax.set_ylim(0, top)
handles, labels = ax.get_legend_handles_labels()
order = [2, 0, 1]  # the rate, its interval, then the reference line
ax.legend(
    [handles[i] for i in order],
    [labels[i] for i in order],
    loc='lower left',
    frameon=False,
)
ax.spines[['top', 'right']].set_visible(False)
ax.grid(axis='y', color=GRID, lw=0.6, alpha=0.6)
fig.tight_layout(pad=0.6)
save(fig, 'ph3_miss_rate_by_year')
