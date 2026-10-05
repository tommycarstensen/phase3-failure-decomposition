"""Investigational-subject-drug identification, shared by dedup_arms.py and
novelty_flag.py so the heuristic lives in one place.

Each trial's *subject* is the experimental-arm drug that is rarest across the
results cohort (a backbone/comparator is common by construction; the novel
agent is rare). Backbones are drugs used as an active comparator in at least
BACKBONE_MIN_TRIALS trials and at least as often as they appear
experimentally."""

import re
from collections import Counter, defaultdict

BACKBONE_MIN_TRIALS = 8

# Normalised intervention names that are not an investigational drug. norm()
# has already removed the word 'placebo', so 'matching placebo' arrives here as
# 'matching'.
STOP = {
    'matching',
    'matched',
    'vehicle',
    'standard of care',
    'saline',
    'normal saline',
    'sham',
    'no intervention',
    'best supportive care',
    'standard therapy',
    'usual care',
    'control',
    'comparator',
    'active comparator',
    'active',
    'treatment',
    'experimental',
    'drug',
    'study drug',
}


def norm(name):
    n = (name or '').lower().strip()
    n = re.sub(r'\(.*?\)', '', n)
    n = re.sub(r'[\d.]+\s*(mg|mcg|ug|g|ml|iu|%|units?|mg/kg|mg/ml)\b', '', n)
    n = re.sub(
        r'\b(oral|iv|injection|tablet|capsule|solution|infusion|'
        r'subcutaneous|sc|film|coated|placebo)\b',
        '',
        n,
    )
    n = re.sub(r'[^a-z0-9+\- ]', '', n)
    n = re.sub(r'\s+', ' ', n).strip(' -+')
    return n


def is_drug(t):
    return t in ('DRUG', 'BIOLOGICAL')


def is_name(nd):
    """True for a normalised name that can identify a drug: not a stop word
    and not a one- or two-character fragment left by the normalisation."""
    return len(nd) >= 3 and nd not in STOP


def build(arms, results):
    """Return (subject_of, freq, backbone). subject_of(nct) -> the trial's
    rarest experimental drug (or None), defined for any nct present in `arms`.
    freq is the results-cohort frequency of each experimental drug (the rarity
    basis)."""
    role = defaultdict(Counter)
    for a in arms.values():
        lab2type = {g['label']: g.get('type') for g in a.get('armGroups', [])}
        for iv in a.get('interventions', []):
            if not is_drug(iv.get('type')):
                continue
            nd = norm(iv['name'])
            if not is_name(nd):
                continue
            types = {lab2type.get(lab) for lab in iv.get('armGroupLabels', [])}
            if 'EXPERIMENTAL' in types:
                role[nd]['exp'] += 1
            if 'ACTIVE_COMPARATOR' in types:
                role[nd]['cmp'] += 1
    backbone = {
        d
        for d, r in role.items()
        if r['cmp'] >= BACKBONE_MIN_TRIALS and r['cmp'] >= r['exp']
    }

    def exp_drugs(nct):
        a = arms.get(nct)
        if not a:
            return set()
        lab2type = {g['label']: g.get('type') for g in a.get('armGroups', [])}
        out = set()
        for iv in a.get('interventions', []):
            if not is_drug(iv.get('type')):
                continue
            nd = norm(iv['name'])
            if not is_name(nd) or nd in backbone:
                continue
            types = {lab2type.get(lab) for lab in iv.get('armGroupLabels', [])}
            if 'EXPERIMENTAL' in types:
                out.add(nd)
        return out

    freq = Counter()
    expsets = {}
    for r in results:
        ds = exp_drugs(r['nct'])
        expsets[r['nct']] = ds
        for d in ds:
            freq[d] += 1

    def subject_of(nct):
        ds = expsets.get(nct)
        if ds is None:
            ds = exp_drugs(nct)  # e.g. a terminated (non-results) trial
        if not ds:
            return None
        return min(ds, key=lambda d: (freq[d], d))

    return subject_of, freq, backbone
