"""ClinicalTrials.gov v2 API access shared by the pull scripts.

The API serves the current version of each record, so a pull returns the
registry as it is on the day it runs. The ph3_*.json, unclear_enriched.json and
residual_refs.json files in this repository are the frozen pulls the paper was
computed from, so the pull scripts refuse to replace them unless --overwrite
is given.
"""

import http.client
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

from repo_files import D

BASE = 'https://clinicaltrials.gov/api/v2/studies'
RETRYABLE = (OSError, http.client.HTTPException, ValueError)


def fetch(url, parse=json.load, timeout=120, pause=1.5):
    """GET a URL, retried three times on a transport or decode error."""
    for attempt in range(4):
        try:
            with urllib.request.urlopen(url, timeout=timeout) as r:
                return parse(r)
        except RETRYABLE:
            if attempt == 3:
                raise
            time.sleep(pause)
    raise AssertionError('unreachable: the last attempt returns or raises')


def studies(agg, fields, cap=400):
    """Yield every study matching an aggregate filter, 1,000 per page."""
    token = None
    total = None
    seen = 0
    for page in range(1, cap + 1):
        q = (
            f'format=json&pageSize=1000&aggFilters={agg}&fields={fields}'
            '&countTotal=true'
        )
        if token:
            q += '&pageToken=' + token
        d = fetch(BASE + '?' + q)
        if page == 1:
            total = d.get('totalCount')
        rows = d.get('studies', [])
        seen += len(rows)
        print(f'  page {page}: {seen}/{total} studies', file=sys.stderr)
        yield from rows
        token = d.get('nextPageToken')
        if not token:
            break
        time.sleep(0.2)


def studies_by_id(ncts, fields, chunk=40):
    """Yield the named studies, fetched `chunk` identifiers at a time."""
    for i in range(0, len(ncts), chunk):
        end = i + chunk
        q = urllib.parse.urlencode(
            {
                'filter.ids': ','.join(ncts[i:end]),
                'fields': fields,
                'pageSize': chunk,
                'format': 'json',
            }
        )
        yield from fetch(BASE + '?' + q, timeout=90).get('studies', [])
        time.sleep(0.2)


def is_phase3(study):
    design = study['protocolSection'].get('designModule', {})
    return 'PHASE3' in design.get('phases', [])


def pnum(pv):
    """The number inside a reported p-value string, operators stripped."""
    if pv is None:
        return None
    s = str(pv).replace('<', '').replace('>', '').replace('=', '').strip()
    m = re.search(r'[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?', s)
    if not m:
        return None
    return float(m.group())


def refuse_overwrite(*names):
    """Stop before a pull that would replace a frozen snapshot file."""
    if '--overwrite' in sys.argv[1:]:
        return
    present = [n for n in names if os.path.exists(D + n)]
    if present:
        sys.exit(
            f'{", ".join(present)}: already present. These are the frozen '
            'pulls the paper was computed from, and the registry cannot '
            'return that state again. Pass --overwrite to replace them with '
            'the registry as it is today.'
        )
