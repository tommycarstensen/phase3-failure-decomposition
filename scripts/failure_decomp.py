"""Shared counting rules for the phase-3 failure decomposition.

Every analysis script imports its population, its win/miss verdict and its
failure buckets from here, so the rules exist once:

  1. The primary population is trials that enrolled at least one participant.
     A registration with status WITHDRAWN was stopped before enrolling anyone
     and is left out unless a script asks for it as a sensitivity analysis.
  2. A trial is counted once. A stopped trial that also posted a
     non-significant primary result is attributed to its termination reason,
     never additionally as a completed miss.
  3. `efficacy_positive` (stopped early for benefit) is a success and is
     excluded from the failure denominator.
  4. A p-value outside [0, 1] is a registry data-entry error and is treated as
     missing.
"""

import re
from collections import Counter

from repo_files import LABELS, REGISTRY, read_json, read_labels

# start-year windows (inclusive)
ERA = (2017, 2026)  # the Final Rule took effect on 18 January 2017
ERA_COMPLETE = (2017, 2022)  # starts old enough to have read out
ALL_YEARS = (1900, 2026)  # every registration with a recorded start year
TREND = (2005, 2021)  # start years with enough read-out trials for a rate

ALPHA = 0.05  # significance threshold of the primary-endpoint verdict

# when the registry was read, and when the labels were assigned
RETRIEVED_COHORT = '9 July 2026'  # ph3_results, ph3_stopped, ph3_meta...
RETRIEVED_ANALYSES = '20 August 2026'  # ph3_primary_analyses
CLASSIFIED = 'July 2026'

# Hwang et al. 2016 (JAMA Intern Med 176:1826): 640 novel therapeutics
# entered pivotal trials, 344 failed, with these reasons for failure.
HWANG = {
    'programs': 640,
    'failed': 344,
    'efficacy': 195,
    'safety': 59,
    'commercial': 74,
}

# category -> failure bucket
COMMERCIAL = [
    'business_strategic',
    'funding',
    'sponsor_undisclosed',
    'not_started',
]
OPERATIONAL = [
    'enrollment',
    'other_operational',
    'external_evidence',
    'regulatory',
    'covid',
    'supply_manufacturing',
]
EFFICACY = ['efficacy_futility']  # + completed misses (added in decompose)
SAFETY = ['safety']
UNKNOWN = ['unclear']
SUCCESS = ['efficacy_positive']  # excluded from failure denominator
# labels that say a trial stopped without stating why
NO_REASON = ['unclear', 'sponsor_undisclosed', 'not_started']
BUCKETS = {
    'eff': EFFICACY,
    'saf': SAFETY,
    'com': COMMERCIAL,
    'op': OPERATIONAL,
    'unk': UNKNOWN,
    'pos': SUCCESS,
}


def bucket_of(label):
    """The bucket a termination category is pooled into."""
    for bucket, labels in BUCKETS.items():
        if label in labels:
            return bucket
    raise ValueError(f'uncategorised stop reason: {label}')


_ALL = set(COMMERCIAL + OPERATIONAL + EFFICACY + SAFETY + UNKNOWN + SUCCESS)


def valid_p(p):
    """True for a number that can be a p-value."""
    return p is not None and 0 <= p <= 1


def record_sig(p_raw, p):
    """Operator-aware significance of ONE analysis record at alpha 0.05.

    Stripping the comparison operator and comparing the number with 0.05
    misreads the very common '<0.05' reporting style as non-significant.
    Returns True (guaranteed p < 0.05), False (guaranteed p >= 0.05), 'AMB'
    (operator leaves it undetermined: '>v' with v < 0.05, '<v' with v > 0.05),
    or None (no usable number)."""
    if not valid_p(p):
        return None
    s = str(p_raw).strip().lstrip('Pp').lstrip()
    if s.startswith('<='):
        return True if p < ALPHA else 'AMB'  # '<=v', v >= 0.05: undetermined
    if s.startswith('<'):
        return True if p <= ALPHA else 'AMB'  # p < v <= 0.05  =>  p < 0.05
    if s.startswith('>'):
        return 'AMB' if p < ALPHA else False  # '>v' with v >= 0.05: miss
    return p < ALPHA


def trial_verdict(analyses):
    """Trial-level verdict: True (win), False (miss), 'AMB' or None.

    A trial wins if any primary analysis is guaranteed significant."""
    saw = False
    amb = False
    for a in analyses:
        rs = record_sig(a.get('p_raw'), a.get('p'))
        if rs is None:
            continue
        saw = True
        if rs is True:
            return True
        if rs == 'AMB':
            amb = True
    if not saw:
        return None
    return 'AMB' if amb else False


def load(include_withdrawn=False):
    """Return (results, meta, stopcat).

    stopcat maps each stopped NCT to its final category (the reclassified
    label where one exists, else the first-pass whyStopped label). By default
    it holds terminated and suspended trials only; include_withdrawn=True adds
    the registrations withdrawn before enrollment.

    Each results record carries r['win']: True, False or None, the
    operator-aware primary-endpoint verdict from the raw p-value strings in
    ph3_primary_analyses.json. A verdict the operators leave undetermined, or
    a trial with no analysis record, falls back to the numeric minimum p from
    ph3_results.json. Test r['win'], not min_p, in downstream code."""
    results = read_json(REGISTRY + 'ph3_results.json')
    meta = read_json(REGISTRY + 'ph3_meta.json')
    pa = read_json(REGISTRY + 'ph3_primary_analyses.json')
    verdicts = {r['nct']: trial_verdict(r['analyses']) for r in pa}
    for r in results:
        v = verdicts.get(r['nct'])
        if v == 'AMB' or v is None:
            v = r['min_p'] < ALPHA if valid_p(r['min_p']) else None
        r['win'] = v
    reclass = read_json(LABELS + 'unclear_reclassified_v2.json')
    whyout = read_labels('why_out')
    stopcat = {
        s['nct']: (reclass.get(s['nct']) or whyout.get(s['nct']) or 'unclear')
        for s in read_json(REGISTRY + 'ph3_stopped.json')
        if include_withdrawn or s['status'] != 'WITHDRAWN'
    }
    unknown = set(stopcat.values()) - _ALL
    if unknown:  # fail loudly if a new label appears
        raise ValueError(f'uncategorised stop reasons: {sorted(unknown)}')
    return results, meta, stopcat


def year_of(meta, nct):
    m = re.match(r'(\d{4})', meta.get(nct, {}).get('start', '') or '')
    return int(m.group(1)) if m else None


def in_window(meta, nct, window):
    y = year_of(meta, nct)
    return y is not None and window[0] <= y <= window[1]


# ---- big-pharma sponsor classifier ----
# The big-pharma stratum is the LARGE companies: those that run a portfolio
# across therapeutic areas at roughly EUR 20bn or more of medicine sales. The
# other companies of BIGPHARMA are mid-size, with an established commercial
# business below that scale; they are added only in a sensitivity analysis
# (with_midsize=True), because where a list of mid-size companies should end
# is a matter of judgment. Each company has the name patterns under which it,
# its subsidiaries and the companies it acquired appear as lead sponsor. A
# pattern is matched at a word start in the lower-cased name; a trailing \b
# keeps 'roche' from matching Rochester and 'janssen' from matching Janssens.
# A subsidiary is counted with its present or last parent whatever the date of
# the trial. Organon, Alcon and Sandoz were divisions of Merck and Novartis
# when most of their registrations were made and are independent now. Two
# names are left as they are on purpose: 'Abbott' alone is counted with
# AbbVie, which took over Abbott's research-based medicines in 2013, although
# a few later registrations are of the business Abbott kept; and Biohaven is
# not counted with Pfizer, because the name is used both by the company
# Pfizer bought in 2022 and by the company spun out of it.
BIGPHARMA = {
    'Pfizer': ['pfizer', 'seagen', 'medivation', 'arena pharmaceuticals'],
    'Merck & Co.': [
        'merck sharp',
        'merck & co',
        r'msd\b',
        'schering-plough',
        r'organon\b',
    ],
    'Novartis': [
        'novartis',
        r'alcon\b',
        r'sandoz\b',
        'fougera',
        'the medicines company',
        'advanced accelerator applications',
        r'endocyte\b',
    ],
    'Roche': [
        r'roche\b',
        'genentech',
        'hoffmann',
        'intermune',
        'spark therapeutics',
    ],
    'Johnson & Johnson': [
        'johnson & johnson',
        r'janssen\b',
        'actelion',
        'centocor',
        'tibotec',
        'crucell',
        'ortho biotech',
        'aragon pharmaceuticals',
        'momenta pharmaceuticals',
        'cougar biotechnology',
        'intra-cellular therapies',
        r'scios\b',
        r'alza\b',
    ],
    'AstraZeneca': [
        'astrazeneca',
        'medimmune',
        'alexion',
        'pearl therapeutics',
        'ardea biosciences',
        'zs pharma',
        'acerta pharma',
        'portola pharmaceuticals',
    ],
    'GSK': ['glaxo', r'gsk\b', 'viiv', r'tesaro\b', 'human genome sciences'],
    'Sanofi': [
        'sanofi',
        'aventis',
        'bioverativ',
        'protein sciences',
        'provention bio',
        r'kadmon\b',
    ],
    # Abbott's pharmaceutical business became AbbVie in 2013
    'AbbVie': [
        'abbvie',
        'abbott',
        'allergan',
        'forest laboratories',
        'warner chilcott',
        'solvay pharmaceuticals',
        'pharmacyclics',
        'kythera',
        r'naurex\b',
        'durata therapeutics',
        'furiex',
        'tobira',
        r'immunogen\b',
        'facet biotech',
    ],
    'Bristol-Myers Squibb': [
        'bristol[- ]myers',
        'celgene',
        'mirati',
        'myokardia',
        'zymogenetics',
    ],
    'Eli Lilly': [
        r'lilly\b',
        'avid radiopharmaceuticals',
        'loxo oncology',
        'icos corporation',
        r'dermira\b',
    ],
    'Amgen': ['amgen', r'biovex\b', r'tularik\b'],
    'Gilead': ['gilead', 'pharmasset', 'triangle pharmaceuticals'],
    'Novo Nordisk': ['novo nordisk'],
    'Boehringer Ingelheim': ['boehringer'],
    'Bayer': [r'bayer\b'],
    'Takeda': [
        'takeda',
        r'shire\b',
        'baxalta',
        'millennium pharmaceuticals',
        'ariad pharmaceuticals',
        'tigenix',
        'new river pharmaceuticals',
    ],
    'Astellas': [
        'astellas',
        'ophthotech',
        'osi pharmaceuticals',
        r'iveric\b',
    ],
    'Daiichi Sankyo': ['daiichi', 'american regent'],
    'Otsuka': ['otsuka', 'astex pharmaceuticals', 'avanir', r'taiho\b'],
    # the generics business of Actavis and Watson went to Teva in 2016, and
    # the registrations under those names are generic-equivalence trials
    'Teva': [
        r'teva\b',
        'cephalon',
        'auspex',
        'nupathe',
        r'actavis\b',
        'watson pharmaceuticals',
    ],
    'Biogen': ['biogen'],
    'Regeneron': ['regeneron'],
    'Vertex': ['vertex'],
    'Moderna': ['moderna'],
    'Servier': ['servier', 'symphogen'],
    'UCB': [r'ucb\b', 'zogenix', 'ra pharmaceuticals'],
    'Merck KGaA': ['merck kgaa', 'emd serono'],
    'CSL': [r'csl\b', 'seqirus', 'vifor'],
    'Eisai': ['eisai', 'morphotek'],
    'Viatris': ['viatris', r'mylan\b', r'meda\b'],
    'Grifols': ['grifols', r'biotest\b'],
    'Ipsen': [r'ipsen\b', 'albireo', 'clementia pharmaceuticals'],
    'Chiesi': ['chiesi', 'amryt'],
    'Recordati': ['recordati'],
}
LARGE = frozenset(
    {
        'Pfizer',
        'Merck & Co.',
        'Novartis',
        'Roche',
        'Johnson & Johnson',
        'AstraZeneca',
        'GSK',
        'Sanofi',
        'AbbVie',
        'Bristol-Myers Squibb',
        'Eli Lilly',
        'Amgen',
        'Gilead',
        'Novo Nordisk',
        'Boehringer Ingelheim',
        'Bayer',
        'Takeda',
    }
)
_BIGPHARMA = re.compile(
    r'\b(?:' + '|'.join(p for ps in BIGPHARMA.values() for p in ps) + ')'
)
_LARGE = re.compile(
    r'\b(?:' + '|'.join(p for c in sorted(LARGE) for p in BIGPHARMA[c]) + ')'
)
# the registry's name for the Upjohn trials says Pfizer, Mylan and Viatris;
# they belong to Viatris, a mid-size company, not to the large one
_NOT_LARGE = re.compile(r'viatris')
# units of these companies that do not develop medicines
_NOT_PHARMA = re.compile(
    r'abbott (?:medical|diagnostics|nutrition)|'
    r'johnson & johnson (?:consumer|vision|medical|healthcare products)|'
    r'mcneil consumer|opella'
)


def is_bigpharma(name, with_midsize=False):
    """True for a lead-sponsor name of one of the LARGE companies, or of any
    BIGPHARMA company when the mid-size ones are wanted too."""
    name = (name or '').lower()
    if _NOT_PHARMA.search(name):
        return False
    if with_midsize:
        return bool(_BIGPHARMA.search(name))
    return bool(_LARGE.search(name)) and not _NOT_LARGE.search(name)


def sponsor_of(meta, nct):
    return meta.get(nct, {}).get('sponsor', '')


def decompose(results, meta, stopcat, window, subset=None):
    """Failure decomposition for trials starting in `window` (inclusive).

    `subset` is an optional predicate nct -> bool for stratification. Returns
    a dict with the failure denominator `den`, the completed-miss count `cm`,
    each bucket count, and `pos` (successes, reported but not in `den`)."""

    def keep(nct):
        if not in_window(meta, nct, window):
            return False
        return subset is None or subset(nct)

    # completed misses: operator-aware verdict False, status COMPLETED, not
    # stopped. The COMPLETED restriction keeps still-ongoing trials
    # (ACTIVE_NOT_RECRUITING etc.) out of the efficacy bucket: an interim
    # non-significant p is not a permanent miss.
    cm = sum(
        1
        for r in results
        if r['win'] is False
        and r['status'] == 'COMPLETED'
        and r['nct'] not in stopcat
        and keep(r['nct'])
    )
    b = Counter(c for n, c in stopcat.items() if keep(n))
    eff = cm + sum(b[k] for k in EFFICACY)
    saf = sum(b[k] for k in SAFETY)
    com = sum(b[k] for k in COMMERCIAL)
    op = sum(b[k] for k in OPERATIONAL)
    unk = sum(b[k] for k in UNKNOWN)
    den = eff + saf + com + op + unk  # efficacy_positive excluded
    return {
        'den': den,
        'cm': cm,
        'eff': eff,
        'op': op,
        'com': com,
        'saf': saf,
        'unk': unk,
        'pos': sum(b[k] for k in SUCCESS),
        'labels': b,
    }


def miss_rate(results, meta, window, subset=None, completed_only=False):
    """Primary-endpoint miss rate over trials with an operator-aware verdict.

    Returns (n, misses, rate in percent). completed_only=True restricts to
    overallStatus COMPLETED, excluding terminated trials whose early,
    underpowered results inflate the miss rate."""
    w = m = 0
    for r in results:
        if r['win'] is None:
            continue
        if completed_only and r['status'] != 'COMPLETED':
            continue
        if not in_window(meta, r['nct'], window):
            continue
        if subset is not None and not subset(r['nct']):
            continue
        if r['win']:
            w += 1
        else:
            m += 1
    n = w + m
    return n, m, (100 * m / n if n else 0.0)


def wilson(k, n, z=1.96):
    """Wilson 95% interval for k of n, as percentages."""
    if n == 0:
        return 0.0, 0.0
    p = k / n
    d = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / d
    half = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5) / d
    return 100 * max(0.0, centre - half), 100 * min(1.0, centre + half)
