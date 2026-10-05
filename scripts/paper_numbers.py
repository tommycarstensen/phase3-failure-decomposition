"""Named numbers for the manuscript, the supplement and the README.

Every number the documents quote is recorded here by the script that computes
it. Each script saves its numbers to numbers/<script>.json; write_numbers.py
merges those files into paper/numbers.tex, which the LaTeX sources read with
\\num{name}. No result number is typed into a document by hand, so the text
cannot drift from the analysis.
"""

import glob
import math
import os
import re

from repo_files import PAPER, D, read_json, write_json, write_text

_NAME = re.compile(r'[a-z][A-Za-z0-9]*(\.[A-Za-z0-9]+)*$')


def _p_value(p):
    """A p-value as (TeX, plain text): two significant digits down to 0.001,
    one significant digit times a power of ten below that."""
    if p >= 0.00095:
        decimals = max(2, 1 - math.floor(math.log10(p)))
        s = f'{p:.{decimals}f}'
        return s, s
    exponent = math.floor(math.log10(p))
    mantissa = p / 10**exponent
    if round(mantissa) == 10:
        mantissa, exponent = 1, exponent + 1
    return (
        f'{mantissa:.0f}\\times10^{{{exponent}}}',
        f'{mantissa:.0f}e{exponent}',
    )


class Numbers:
    """The numbers one script contributes, keyed by a dotted name."""

    def __init__(self, section):
        self.section = section
        self.entries = {}

    def _put(self, name, value, tex, txt):
        if not _NAME.match(name):
            raise ValueError(f'bad number name: {name}')
        if name in self.entries:
            raise ValueError(f'number recorded twice: {name}')
        self.entries[name] = {'value': value, 'tex': tex, 'txt': txt}

    def count(self, name, value):
        """An integer, printed with a thousands separator."""
        txt = f'{int(value):,}'
        self._put(name, int(value), txt.replace(',', '{,}'), txt)

    def pct(self, name, value):
        """A percentage: name has one decimal, name.int is rounded."""
        self._put(name, round(value, 4), f'{value:.1f}', f'{value:.1f}')
        whole = f'{value:.0f}'
        self._put(name + '.int', round(value, 4), whole, whole)

    def share(self, name, k, n):
        """A count k of n, with its percentage: name.n, name.pct."""
        self.count(name + '.n', k)
        self.pct(name + '.pct', 100 * k / n)

    def fixed(self, name, value, digits=2):
        """A number with a fixed count of decimals."""
        s = f'{value:.{digits}f}'
        self._put(name, round(value, 6), s, s)

    def p(self, name, value):
        tex, txt = _p_value(value)
        self._put(name, value, tex, txt)

    def text(self, name, value):
        self._put(name, value, str(value), str(value))

    def save(self):
        write_json(self.entries, f'numbers/{self.section}.json', indent=1)


def tex_escape(s):
    for a, b in (('&', r'\&'), ('%', r'\%'), ('_', r'\_'), ('#', r'\#')):
        s = s.replace(a, b)
    return s


def write_table(name, rows):
    """Save LaTeX table rows (lists of cells) to paper/tables/<name>.tex."""
    lines = [' & '.join(str(c) for c in row) + r' \\' for row in rows]
    write_text('\n'.join(lines) + '\n', PAPER + f'tables/{name}.tex')


def read_numbers():
    """Every recorded number, name -> entry. A name may be recorded once."""
    merged = {}
    for path in sorted(glob.glob(D + 'numbers/*.json')):
        section = os.path.basename(path)
        for name, entry in read_json('numbers/' + section).items():
            if name in merged:
                raise ValueError(f'{name} is recorded by two scripts')
            merged[name] = entry
    return merged
