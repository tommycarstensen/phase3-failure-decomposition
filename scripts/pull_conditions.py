"""Pull the registered conditions of every trial in the two cohorts.

Produces ph3_conditions.json - {nct: [condition, ...]}, the input to the
therapeutic-area assignment in areas.py.
"""

import sys

from ctgov import refuse_overwrite, studies
from repo_files import REGISTRY, write_json

F = (
    'protocolSection.identificationModule.nctId,'
    'protocolSection.conditionsModule.conditions'
)


def main():
    refuse_overwrite(REGISTRY + 'ph3_conditions.json')
    cond = {}
    for agg in ('phase:3,results:with', 'phase:3,status:ter+wit+sus'):
        print('pulling', agg, file=sys.stderr)
        for st in studies(agg, F):
            ps = st['protocolSection']
            cond[ps['identificationModule']['nctId']] = ps.get(
                'conditionsModule', {}
            ).get('conditions', [])
    write_json(cond, REGISTRY + 'ph3_conditions.json')
    print('conditions for', len(cond), 'NCTs')


if __name__ == '__main__':
    main()
