"""Core pull #1: primary-endpoint significance and termination reasons.

Produces:
  ph3_results.json - [{nct, status, n_prim, min_p}] for phase-3 trials with
                     posted results
  ph3_stopped.json - [{nct, status, why}] for phase-3 terminated, withdrawn
                     or suspended trials
"""

import sys

from ctgov import is_phase3, pnum, refuse_overwrite, studies
from repo_files import REGISTRY, write_json

F1 = (
    'protocolSection.identificationModule.nctId,'
    'protocolSection.designModule.phases,'
    'protocolSection.statusModule.overallStatus,'
    'resultsSection.outcomeMeasuresModule.outcomeMeasures'
)
F2 = (
    'protocolSection.identificationModule.nctId,'
    'protocolSection.designModule.phases,'
    'protocolSection.statusModule.overallStatus,'
    'protocolSection.statusModule.whyStopped'
)


def result_record(st):
    """One results-posting study -> its primary-endpoint minimum p-value."""
    ps = st['protocolSection']
    oms = (
        st.get('resultsSection', {})
        .get('outcomeMeasuresModule', {})
        .get('outcomeMeasures', [])
    )
    prim = [o for o in oms if o.get('type') == 'PRIMARY']
    pvals = [
        pnum(a.get('pValue')) for o in prim for a in o.get('analyses', [])
    ]
    pvals = [v for v in pvals if v is not None]
    return {
        'nct': ps['identificationModule']['nctId'],
        'status': ps['statusModule']['overallStatus'],
        'n_prim': len(prim),
        'min_p': min(pvals) if pvals else None,
    }


def stopped_record(st):
    """One stopped study -> its status and free-text termination reason."""
    ps = st['protocolSection']
    return {
        'nct': ps['identificationModule']['nctId'],
        'status': ps['statusModule']['overallStatus'],
        'why': ps['statusModule'].get('whyStopped', ''),
    }


def main():
    refuse_overwrite(
        REGISTRY + 'ph3_results.json', REGISTRY + 'ph3_stopped.json'
    )

    print('pulling phase-3 WITH results...', file=sys.stderr)
    recs = [
        result_record(st)
        for st in studies('phase:3,results:with', F1)
        if is_phase3(st)
    ]
    write_json(recs, REGISTRY + 'ph3_results.json')
    print('ph3_results.json:', len(recs))

    print('pulling phase-3 terminated/withdrawn/suspended...', file=sys.stderr)
    srecs = [
        stopped_record(st)
        for st in studies('phase:3,status:ter+wit+sus', F2)
        if is_phase3(st)
    ]
    write_json(srecs, REGISTRY + 'ph3_stopped.json')
    print('ph3_stopped.json:', len(srecs))


if __name__ == '__main__':
    main()
