"""Core pull #3: the full primary-outcome statistical-analysis records.

These let the miss rate account for the reported comparison operator, effect
direction and non-inferiority design, which the direction-blind `min_p` of
pull #1 cannot.

For every phase-3 trial with posted results, each PRIMARY outcome's analysis
records are extracted with: paramType (mean difference / hazard ratio / ...),
paramValue, CI limits, nonInferiorityType, statistical method and p-value.

Produces:
  ph3_primary_analyses.json - [{nct, n_prim, analyses:[{oi, param_type,
       param_value, ci_lo, ci_hi, ci_pct, ni_type, ni_comment, method, p_raw,
       p}, ...]}, ...]

Downstream use (failure_decomp.py and endpoint_design.py, not this pull):
  - the operator-aware verdict, read from the raw p-value strings,
  - the miss rate with non-inferiority and equivalence designs excluded,
  - the count of wins whose significant analyses are all ratio parameters
    above 1 (the registry does not record which direction is benefit),
  - the stricter rules for combining primary outcomes.
"""

import sys

from ctgov import is_phase3, pnum, refuse_overwrite, studies
from repo_files import REGISTRY, write_json

F = (
    'protocolSection.identificationModule.nctId,'
    'protocolSection.designModule.phases,'
    'resultsSection.outcomeMeasuresModule.outcomeMeasures'
)


def fnum(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def extract(st):
    """One phase-3 study -> {nct, n_prim, analyses}."""
    ps = st['protocolSection']
    oms = (
        st.get('resultsSection', {})
        .get('outcomeMeasuresModule', {})
        .get('outcomeMeasures', [])
    )
    prim = [o for o in oms if o.get('type') == 'PRIMARY']
    analyses = []
    for oi, o in enumerate(prim):
        for a in o.get('analyses', []):
            analyses.append(
                {
                    'oi': oi,  # primary-outcome index (AND-rule grouping)
                    'param_type': a.get('paramType'),
                    'param_value': fnum(a.get('paramValue')),
                    'ci_lo': fnum(a.get('ciLowerLimit')),
                    'ci_hi': fnum(a.get('ciUpperLimit')),
                    'ci_pct': fnum(a.get('ciPctValue')),
                    'ni_type': a.get('nonInferiorityType'),
                    'ni_comment': a.get('nonInferiorityComment'),
                    'method': a.get('statisticalMethod'),
                    'p_raw': a.get('pValue'),
                    'p': pnum(a.get('pValue')),
                }
            )
    return {
        'nct': ps['identificationModule']['nctId'],
        'n_prim': len(prim),
        'analyses': analyses,
    }


def main():
    refuse_overwrite(REGISTRY + 'ph3_primary_analyses.json')
    print(
        'pulling phase-3 primary-outcome analysis records...', file=sys.stderr
    )
    recs = [
        extract(st)
        for st in studies('phase:3,results:with', F)
        if is_phase3(st)
    ]
    write_json(recs, REGISTRY + 'ph3_primary_analyses.json')
    print(
        'ph3_primary_analyses.json:',
        len(recs),
        'trials;',
        sum(len(r['analyses']) for r in recs),
        'primary analysis records',
    )


if __name__ == '__main__':
    main()
