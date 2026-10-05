"""Pull the arm groups and interventions of every trial in the two cohorts.

Produces ph3_arms.json - {nct: {armGroups: [...], interventions: [...]}}, the
input to the subject-drug logic in subjects.py.
"""

import sys

from ctgov import refuse_overwrite, studies
from repo_files import REGISTRY, write_json

F = (
    'protocolSection.identificationModule.nctId,'
    'protocolSection.armsInterventionsModule'
)


def extract(st):
    aim = st['protocolSection'].get('armsInterventionsModule', {})
    return {
        'armGroups': [
            {
                'label': g.get('label'),
                'type': g.get('type'),
                'interventionNames': g.get('interventionNames', []),
            }
            for g in aim.get('armGroups', [])
        ],
        'interventions': [
            {
                'name': i.get('name'),
                'type': i.get('type'),
                'armGroupLabels': i.get('armGroupLabels', []),
            }
            for i in aim.get('interventions', [])
        ],
    }


def main():
    refuse_overwrite(REGISTRY + 'ph3_arms.json')
    arms = {}
    for agg in ('phase:3,results:with', 'phase:3,status:ter+wit+sus'):
        print('pulling', agg, file=sys.stderr)
        for st in studies(agg, F):
            nct = st['protocolSection']['identificationModule']['nctId']
            arms[nct] = extract(st)
    write_json(arms, REGISTRY + 'ph3_arms.json')
    print('arms for', len(arms), 'NCTs')


if __name__ == '__main__':
    main()
