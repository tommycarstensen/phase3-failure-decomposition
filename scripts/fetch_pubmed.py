"""Fetch the PubMed abstracts linked to the residual 'unclear' trials.

Reads residual_refs.json and produces:
  nct_pmids.json        - {nct: [[reference type, pmid], ...]}
  pubmed_abstracts.json - {pmid: abstract text}, not kept in the repository
                          (third-party text); this script re-fetches it by
                          PMID from the E-utilities.
"""

import re
import sys
import time
import urllib.parse

from ctgov import fetch
from repo_files import PUBMED, REGISTRY, read_json, write_json

EF = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi'
CH = 40


def read_text(response):
    return response.read().decode('utf-8', 'replace')


def efetch(ids):
    q = urllib.parse.urlencode(
        {
            'db': 'pubmed',
            'id': ','.join(ids),
            'rettype': 'abstract',
            'retmode': 'text',
        }
    )
    return fetch(EF + '?' + q, parse=read_text, timeout=90, pause=1.0)


def linked_pmids(refs):
    """PMIDs per NCT, and the set of all of them."""
    nct_pmids = {}
    allp = set()
    for nct, rs in refs.items():
        ps = []
        for r in rs:
            pm = r.get('pmid')
            if pm and r.get('type') in ('RESULT', 'DERIVED', 'BACKGROUND'):
                ps.append((r.get('type'), pm))
                allp.add(pm)
        if ps:
            nct_pmids[nct] = ps
    return nct_pmids, allp


def main():
    nct_pmids, allp = linked_pmids(read_json(REGISTRY + 'residual_refs.json'))
    print(
        'NCTs with pmids:',
        len(nct_pmids),
        ' unique pmids:',
        len(allp),
        file=sys.stderr,
    )

    pmids = sorted(allp)
    raw = {}
    for i in range(0, len(pmids), CH):
        end = i + CH
        txt = efetch(pmids[i:end])
        # efetch text mode separates records by blank lines and gives each a
        # 'PMID: NNN' line, so split on the gaps and key each block by PMID.
        for b in re.split(r'\n\n\n+', txt.strip()):
            m = re.search(r'PMID:\s*(\d+)', b)
            if m:
                raw[m.group(1)] = re.sub(r'\s+', ' ', b).strip()
        time.sleep(0.4)
    write_json(raw, PUBMED + 'pubmed_abstracts.json')
    write_json(nct_pmids, PUBMED + 'nct_pmids.json')
    print('fetched abstracts for', len(raw), 'pmids')


if __name__ == '__main__':
    main()
