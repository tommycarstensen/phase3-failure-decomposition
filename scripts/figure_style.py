"""The size, the type and the file format the figures share.

Each figure is drawn at the width it is printed at, the text width of the
manuscript, so a font size here is the size on the page. The figures are
saved as vector PDF with embedded fonts and draw recorded numbers only, so a
figure script runs after write_numbers.py.

The type follows Elsevier's artwork instructions for the journal version:
Arial or Helvetica where the machine has them (DejaVu Sans otherwise), no
lettering below 8 points at this width (Elsevier asks for 7 at the printed
size, which holds down to a printed width of 140 mm), and no line heavier
than LINE_MAX points.
"""

import matplotlib.pyplot as plt

from paper_numbers import read_numbers
from repo_files import PAPER, D

WIDTH = 6.5  # inches: the text width of the manuscript
BASE = 9  # points: axis and tick labels
SMALL = 8  # points: legends, value labels and notes; nothing is smaller
LINE_MAX = 1.5  # points: Elsevier's heaviest line weight


def start():
    """Set the type the figures share and return the recorded numbers."""
    plt.switch_backend('Agg')
    plt.rcParams.update(
        {
            'font.size': BASE,
            'font.family': 'sans-serif',
            'font.sans-serif': ['Arial', 'Helvetica', 'DejaVu Sans'],
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
