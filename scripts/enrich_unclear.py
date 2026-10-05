"""Fetch extra registry context for termination reasons left 'unclear'.

For every stopped trial whose whyStopped string was labelled 'unclear', or
that has no whyStopped string at all, pull the detailed description,
enrollment and results flag. Produces unclear_enriched.json, the input to the
second classification pass (DETAIL_TASK.md) and to reclassify.py.
"""

import sys

from ctgov import refuse_overwrite, studies_by_id
from repo_files import REGISTRY, read_json, read_labels, write_json

F = (
    'protocolSection.identificationModule.nctId,'
    'protocolSection.statusModule.overallStatus,'
    'protocolSection.statusModule.whyStopped,'
    'protocolSection.descriptionModule.detailedDescription,'
    'protocolSection.designModule.enrollmentInfo,'
    'hasResults'
)


def unclear_ncts():
    stopped = {s['nct']: s for s in read_json(REGISTRY + 'ph3_stopped.json')}
    labels = read_labels('why_out')
    unclear = {n for n, label in labels.items() if label == 'unclear'}
    unclear |= {n for n, s in stopped.items() if not (s['why'] or '').strip()}
    return sorted(unclear)


def extract(st):
    ps = st['protocolSection']
    return {
        'status': ps['statusModule']['overallStatus'],
        'why': ps['statusModule'].get('whyStopped', ''),
        'detail': ps.get('descriptionModule', {}).get(
            'detailedDescription', ''
        ),
        'enroll': ps.get('designModule', {}).get('enrollmentInfo', {}),
        'hasResults': st.get('hasResults', False),
    }


def main():
    refuse_overwrite(REGISTRY + 'unclear_enriched.json')
    ncts = unclear_ncts()
    print('enriching', len(ncts), 'unclear NCTs', file=sys.stderr)
    out = {}
    for st in studies_by_id(ncts, F):
        nct = st['protocolSection']['identificationModule']['nctId']
        out[nct] = extract(st)
    write_json(out, REGISTRY + 'unclear_enriched.json')

    # quick diagnostics
    withdrawn0 = sum(
        1
        for v in out.values()
        if v['status'] == 'WITHDRAWN'
        and (v['enroll'].get('count') in (0, None))
    )
    low_enroll = sum(
        1
        for v in out.values()
        if isinstance(v['enroll'].get('count'), int)
        and 0 < v['enroll']['count'] < 15
    )
    has_detail = sum(
        1 for v in out.values() if len((v['detail'] or '').strip()) > 40
    )
    has_results = sum(1 for v in out.values() if v['hasResults'])
    print('fetched:', len(out))
    print('WITHDRAWN with 0/None enrolled (not started):', withdrawn0)
    print('actual enrollment 1-14 (likely enrollment fail):', low_enroll)
    print('has substantive detailedDescription (>40 chars):', has_detail)
    print('hasResults (efficacy classifiable):', has_results)


if __name__ == '__main__':
    main()
