"""Second-pass labels for the termination reasons the first pass left without
a reason: the whyStopped string was blank, or the model labelled it 'unclear'.

A bare sponsor decision (BARE: the string says that the sponsor, the company
or its management decided, and gives no business reason) becomes
'sponsor_undisclosed'. That rule comes first and also overrides a second-pass
model label of 'business_strategic': the taxonomy calls a bare sponsor
decision a string that states no reason, and the model, told to avoid
'unclear', answered 'business_strategic' to such strings whose detailed
description says nothing about the stop. Any other second-pass model label
(detail_out/, read from the detailed description) is used where it names a
reason. Where the model names none, the wider SPONSOR pattern, which also
takes a bare 'business decision' or a discontinued program, gives
'sponsor_undisclosed' too. For what is left, a registration withdrawn with no
participants becomes 'not_started' and an actual enrollment above zero and
below LOW_ENROLLMENT becomes 'enrollment'. Whatever remains stays 'unclear'.
Produces unclear_reclassified.json.
"""

import re
from collections import Counter

from paper_numbers import Numbers
from repo_files import LABELS, REGISTRY, read_json, read_labels, write_json

# an actual enrollment below this reads as a failure to enrol
LOW_ENROLLMENT = 15
enr = read_json(REGISTRY + 'unclear_enriched.json')
dlab = read_labels('detail_out')  # second-pass model labels

SPONSOR = re.compile(
    r'sponsor decision|company decision|business decision|business reason|'
    r'terminated by (the )?sponsor|withdrawn by (the )?sponsor|'
    r'sponsor.*discontinu|'
    r'discontinu.*(development|program)|study terminated by sponsor|'
    r'sponsor has no',
    re.IGNORECASE,
)
# the sponsor, the company or its management decided, in the spellings found
BARE = re.compile(
    r"sponsor'?s?\s+(internal\s+)?decision|"
    r'decision\s+(of|by)\s+(the\s+)?(sponsor|company)|'
    r'(decided|stopped|terminated|halted|cancell?ed|withdrawn)\s+by\s+'
    r'(the\s+)?(previous\s+)?(study\s+)?sponsor|'
    r'(sponsor|company)\s+(has\s+)?(currently\s+)?'
    r'(decided|elected|terminated|halted|cancell?ed|withdr[ae]w)|'
    r'sponsor\s+made\s+the\s+decision|'
    r"sponsor'?s\s+(discretion|convenience)|discretion\s+of\s+the\s+sponsor|"
    r'(company|corporate|corporation|management|internal)\s+'
    r'(company\s+)?decision|'
    r'sponsor\s+has\s+no|^\W*(per\s+)?sponsor\W*$',
    re.IGNORECASE,
)
# a business reason is a reason: such a string is not a bare decision
BUSINESS = re.compile(
    r'business|commercial|strateg|portfolio|priorit|financ|fund|market',
    re.IGNORECASE,
)


def bare_decision(why):
    return bool(BARE.search(why)) and not BUSINESS.search(why)


def final_label(nct):
    """Return (label, how it was assigned)."""
    v = enr[nct]
    why = v.get('why') or ''
    ec = v.get('enroll', {}).get('count')
    actual = v.get('enroll', {}).get('type') == 'ACTUAL'
    d = dlab.get(nct)
    if bare_decision(why) and d in (None, 'unclear', 'business_strategic'):
        return 'sponsor_undisclosed', 'rule'
    if d and d != 'unclear':
        return d, 'model'
    if SPONSOR.search(why) or BARE.search(why):
        return 'sponsor_undisclosed', 'wider'
    if v['status'] == 'WITHDRAWN' and ec in (0, None):
        return 'not_started', 'rule'
    if actual and isinstance(ec, int) and 0 < ec < LOW_ENROLLMENT:
        return 'enrollment', 'rule'
    return 'unclear', 'none'


labelled = {n: final_label(n) for n in enr}
final = {n: lab for n, (lab, _) in labelled.items()}
write_json(final, LABELS + 'unclear_reclassified.json')

tot = len(final)
c = Counter(final.values())
how = Counter(h for _, h in labelled.values())
# 'wider' is the sponsor rule's wider pattern, where the model named no reason
by_rule = Counter(
    lab for lab, h in labelled.values() if h in ('rule', 'wider')
)
rules = how['rule'] + how['wider']
blank = sum(1 for v in enr.values() if not (v.get('why') or '').strip())
print(f'=== second pass over {tot} trials without a first-pass reason ===')
print(f'  blank whyStopped: {blank}; first-pass "unclear": {tot - blank}')
print(f'  second-pass model labels available: {len(dlab)}')
for k, n in c.most_common():
    print(f'  {k:22s} {n:4d}  ({100 * n / tot:4.1f}%)')
print(f'  assigned by the model: {how["model"]}')
print(f'  assigned by rule: {rules}  {dict(by_rule)}')
print(f'  of the sponsor rule, by the wider pattern: {how["wider"]}')
print(f'  still unclear: {how["none"]}')

nums = Numbers('reclassify')
nums.count('pass2.input', tot)
nums.count('pass2.blank', blank)
nums.count('pass2.modelRead', len(dlab))
nums.count('pass2.byModel', how['model'])
nums.count('pass2.byRule', rules)
nums.count('pass2.rule.sponsor', by_rule['sponsor_undisclosed'])
nums.count('pass2.rule.sponsor.wide', how['wider'])
nums.count(
    'pass2.rule.sponsor.overModel',
    sum(
        1
        for n, (lab, _) in labelled.items()
        if lab == 'sponsor_undisclosed' and dlab.get(n) == 'business_strategic'
    ),
)
nums.count('pass2.rule.notStarted', by_rule['not_started'])
nums.count('pass2.rule.enrollment', by_rule['enrollment'])
nums.count('pass2.rule.enrollmentMax', LOW_ENROLLMENT - 1)
nums.count(
    'pass2.model.notStarted',
    sum(
        1
        for lab, h in labelled.values()
        if lab == 'not_started' and h == 'model'
    ),
)
nums.count('pass2.unclear', how['none'])
nums.save()
