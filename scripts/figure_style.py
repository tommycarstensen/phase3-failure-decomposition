"""The size, the type and the file format the figures share.

Each figure is drawn at the width it is printed at, the text width of the
manuscript, so a font size here is the size on the page. The figures are
saved as vector PDF and draw recorded numbers only, so a figure script runs
after write_numbers.py.
"""

import matplotlib.pyplot as plt

from paper_numbers import read_numbers
from repo_files import PAPER, D

WIDTH = 6.5  # inches: the text width of the manuscript
BASE = 9  # points: axis and tick labels
SMALL = 8  # points: legends, value labels and notes; nothing is smaller


def start():
    """Set the type the figures share and return the recorded numbers."""
    plt.switch_backend('Agg')
    plt.rcParams.update(
        {
            'font.size': BASE,
            'font.family': 'DejaVu Sans',
            'axes.titlesize': BASE,
            'legend.fontsize': SMALL,
            # TrueType outlines, not Type 3 bitmaps-by-procedure
            'pdf.fonttype': 42,
        }
    )
    return read_numbers()


def save(fig, name):
    """Write paper/figures/<name>.pdf."""
    out = PAPER + f'figures/{name}.pdf'
    # without a creation date the same numbers give the same bytes
    fig.savefig(D + out, facecolor='white', metadata={'CreationDate': None})
    print('saved', out)
