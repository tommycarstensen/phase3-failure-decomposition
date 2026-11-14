"""The colours of the figures, one role each.

A colour means the same thing in every figure: mid gray is Hwang 2016, navy
is this work. The figures keep to these blues and grays, with no warm colour
(the author, 2026-11-14). The pairs that sit side by side were checked for
separation under simulated protanopia and deuteranopia as well as normal
colour vision, and the bar colours for separation in lightness, so that the
figures survive greyscale printing: the gray of Hwang 2016 lies between the
mid and the pale blue in lightness, where the ochre it replaced lay.
"""

HWANG = '#959595'  # Hwang 2016, the external comparison
THIS_WORK = '#1f3b73'  # this work: primary series, corrected values
THIS_WORK_REST = '#4c6da4'  # this work: sponsors other than big pharma
THIS_WORK_CONTEXT = '#c2d3ea'  # this work: the all-sponsors context series
RAW = '#b9c1ca'  # this work before the coverage correction
# the pale fill of what the two counting choices change: the range behind a
# corrected value, and the boxes of the two choices in the flow diagram
BOUNDS = '#dde6f2'
BOUNDS_EDGE = '#8fa6cc'  # the outline of that range, visible in greyscale


def tint(colour, share):
    """A palette colour mixed with white, `share` being how much of the
    colour is kept: the look of a transparent fill, but opaque, so that the
    grid stays behind it."""
    channels = bytes.fromhex(colour.lstrip('#'))
    mixed = (round(255 - share * (255 - c)) for c in channels)
    return '#' + ''.join(f'{c:02x}' for c in mixed)


INK = '#1a1a1a'  # bar edges, value labels
INK_SECONDARY = '#555555'  # annotations and reference lines
INK_MUTED = '#777777'  # footnotes
GRID = '#cccccc'
