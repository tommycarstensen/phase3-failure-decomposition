"""Where this repository's files live, and how the scripts read and write them.

Every path is resolved against the repository root, the directory above the
one holding this file, so a script gives the same result from any working
directory.
"""

import glob
import json
from pathlib import Path

D = str(Path(__file__).resolve().parent.parent) + '/'

# folders, relative to D
REGISTRY = 'data/registry/'  # the frozen ClinicalTrials.gov retrievals
PUBMED = 'data/pubmed/'  # linked PMIDs; the abstracts are not redistributed
LABELS = 'data/labels/'  # the labels of the three classification passes
VALIDATION = 'data/validation/'  # the adjudicated validation sample
PAPER = 'paper/'  # the manuscript, the supplement and what they read


def read_json(name):
    with open(D + name, encoding='utf-8') as fh:
        return json.load(fh)


def _for_writing(name):
    path = Path(D + name)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def write_json(obj, name, **kwargs):
    with open(_for_writing(name), 'w', encoding='utf-8') as fh:
        json.dump(obj, fh, **kwargs)


def read_lines(path):
    """The lines of a text file, newline included, as iterating it gives."""
    with open(path, encoding='utf-8') as fh:
        return fh.readlines()


def read_labels(folder):
    """NCT -> label from every batch_*.tsv in a label folder (last column)."""
    labels = {}
    for path in sorted(glob.glob(D + LABELS + folder + '/batch_*.tsv')):
        for line in read_lines(path):
            line = line.rstrip('\n')
            if not line.strip():
                continue
            p = line.split('\t')
            labels[p[0]] = p[-1].strip()
    return labels


def read_text(name):
    with open(D + name, encoding='utf-8') as fh:
        return fh.read()


def write_text(text, name):
    with open(_for_writing(name), 'w', encoding='utf-8') as fh:
        fh.write(text)
