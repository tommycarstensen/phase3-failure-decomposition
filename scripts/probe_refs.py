"""Find linked publications for reasons still 'unclear' after the second pass.

Produces residual_refs.json - {nct: [registry reference records]}, the input
to fetch_pubmed.py and the third classification pass (PUB_TASK.md).
"""

import sys
from collections import Counter

from ctgov import refuse_overwrite, studies_by_id
from repo_files import LABELS, REGISTRY, read_json, write_json

F = (
    'protocolSection.identificationModule.nctId,'
    'protocolSection.referencesModule'
)


def main():
    refuse_overwrite(REGISTRY + 'residual_refs.json')
    reclass = read_json(LABELS + 'unclear_reclassified.json')
    resid = [n for n, label in reclass.items() if label == 'unclear']
    print('residual unknown NCTs:', len(resid), file=sys.stderr)

    refcount = Counter()
    has_result_pub = 0
    has_any_pub = 0
    pmids = 0
    out = {}
    for st in studies_by_id(resid, F):
        ps = st['protocolSection']
        nct = ps['identificationModule']['nctId']
        refs = ps.get('referencesModule', {}).get('references', [])
        out[nct] = refs
        types = [r.get('type') for r in refs]
        if refs:
            has_any_pub += 1
        if 'RESULT' in types or 'DERIVED' in types:
            has_result_pub += 1
        for r in refs:
            if r.get('pmid'):
                pmids += 1
        for t in types:
            refcount[t] += 1
    write_json(out, REGISTRY + 'residual_refs.json')

    print('probed:', len(out))
    print(
        '  with ANY linked reference:',
        has_any_pub,
        f'({100 * has_any_pub / len(out):.0f}%)',
    )
    print(
        '  with a RESULT/DERIVED publication:',
        has_result_pub,
        f'({100 * has_result_pub / len(out):.0f}%)',
    )
    print('  total PMIDs available:', pmids)
    print('  reference types:', dict(refcount))


if __name__ == '__main__':
    main()
