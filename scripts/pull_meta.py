"""Core pull #2: lightweight metadata joined onto the two cohorts.

Produces ph3_meta.json - {nct: {status, why, start, drugs[], sponsor}} for
every phase-3 trial in either cohort. Used for the start year and the sponsor
class.
"""

import sys

from ctgov import refuse_overwrite, studies
from repo_files import REGISTRY, write_json

F = (
    'protocolSection.identificationModule.nctId,'
    'protocolSection.statusModule.overallStatus,'
    'protocolSection.statusModule.whyStopped,'
    'protocolSection.statusModule.startDateStruct,'
    'protocolSection.armsInterventionsModule.interventions,'
    'protocolSection.sponsorCollaboratorsModule.leadSponsor'
)


def extract(st):
    ps = st['protocolSection']
    sm = ps['statusModule']
    drugs = [
        iv.get('name', '')
        for iv in ps.get('armsInterventionsModule', {}).get(
            'interventions', []
        )
        if iv.get('type') in ('DRUG', 'BIOLOGICAL')
    ]
    return {
        'nct': ps['identificationModule']['nctId'],
        'status': sm['overallStatus'],
        'why': sm.get('whyStopped', ''),
        'start': sm.get('startDateStruct', {}).get('date', ''),
        'drugs': drugs,
        'sponsor': ps.get('sponsorCollaboratorsModule', {})
        .get('leadSponsor', {})
        .get('name', ''),
    }


def main():
    refuse_overwrite(REGISTRY + 'ph3_meta.json')
    meta = {}
    for agg in ('phase:3,results:with', 'phase:3,status:ter+wit+sus'):
        print('pulling', agg, file=sys.stderr)
        for st in studies(agg, F):
            m = extract(st)
            meta[m['nct']] = m
    write_json(meta, REGISTRY + 'ph3_meta.json')
    print('ph3_meta.json:', len(meta), 'unique NCTs')


if __name__ == '__main__':
    main()
