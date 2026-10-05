"""The cohort and the p-value strings behind the primary-endpoint verdict.

Counts the registrations retrieved under each filter, the population analysed,
and what the registry's primary-analysis records contain: how many carry a
p-value string, how many trials get a verdict, and how many verdicts the
operator-aware reading changes relative to stripping the operator and
comparing the number with 0.05.
"""

from collections import Counter

from failure_decomp import (
    ALL_YEARS,
    ALPHA,
    BIGPHARMA,
    CLASSIFIED,
    ERA,
    ERA_COMPLETE,
    LARGE,
    RETRIEVED_ANALYSES,
    RETRIEVED_COHORT,
    in_window,
    is_bigpharma,
    load,
    sponsor_of,
    trial_verdict,
    valid_p,
    year_of,
)
from paper_numbers import Numbers
from repo_files import REGISTRY, read_json

# the intervention types that pull_meta.py keeps as a trial's drugs
DRUG_TYPES = {'DRUG', 'BIOLOGICAL'}
results, meta, stopcat = load(include_withdrawn=True)
stopped = read_json(REGISTRY + 'ph3_stopped.json')
pa = read_json(REGISTRY + 'ph3_primary_analyses.json')
nums = Numbers('cohort')
nums.text('era.first', ERA[0])
nums.text('era.last', ERA[1])
nums.text('era.completeLast', ERA_COMPLETE[1])
nums.text('allYears.last', ALL_YEARS[1])
nums.text('alpha', ALPHA)
nums.text('retrieval.cohort', RETRIEVED_COHORT)
nums.text('retrieval.analyses', RETRIEVED_ANALYSES)
nums.text('classification.month', CLASSIFIED)

in_results = {r['nct'] for r in results}
in_stopped = {s['nct'] for s in stopped}
status = Counter(s['status'] for s in stopped)
unique = len(in_results | in_stopped)
print('=== cohort ===')
print(f'  with posted results: {len(results)}')
print(f'  terminated, withdrawn or suspended: {len(stopped)}  {dict(status)}')
print(f'  in both: {len(in_results & in_stopped)}; unique: {unique}')
print(f'  analysed (withdrawn excluded): {unique - status["WITHDRAWN"]}')
nums.count('cohort.results', len(results))
nums.count('cohort.stopped', len(stopped))
nums.count('cohort.both', len(in_results & in_stopped))
nums.count('cohort.unique', unique)
nums.count('cohort.terminated', status['TERMINATED'])
nums.count('cohort.withdrawn', status['WITHDRAWN'])
nums.count('cohort.suspended', status['SUSPENDED'])
nums.count('cohort.analysed', unique - status['WITHDRAWN'])
nums.count('cohort.stoppedEnrolled', len(stopped) - status['WITHDRAWN'])

# the phase filter is the only filter on what a registration tests
arms = read_json(REGISTRY + 'ph3_arms.json')
no_drug = sum(
    1
    for n in in_results | in_stopped
    if not {i['type'] for i in arms[n]['interventions']} & DRUG_TYPES
)
print(
    f'  no drug or biological intervention: {no_drug} '
    f'({100 * no_drug / unique:.1f}%)'
)
nums.share('cohort.noDrug', no_drug, unique)

era_stopped = [s for s in stopped if in_window(meta, s['nct'], ERA)]
era_withdrawn = sum(s['status'] == 'WITHDRAWN' for s in era_stopped)
print(
    f'  stopped registrations starting {ERA[0]}-{ERA[1]}: {len(era_stopped)}, '
    f'of which withdrawn before enrollment {era_withdrawn} '
    f'({100 * era_withdrawn / len(era_stopped):.1f}%)'
)
nums.count('cohort.era.stopped', len(era_stopped))
nums.share('cohort.era.withdrawn', era_withdrawn, len(era_stopped))

rstatus = Counter(r['status'] for r in results)
print(f'  results cohort by status: {dict(rstatus)}')
nums.count('cohort.results.completed', rstatus['COMPLETED'])
nums.count('cohort.results.terminated', rstatus['TERMINATED'])
nums.count(
    'cohort.results.other',
    len(results) - rstatus['COMPLETED'] - rstatus['TERMINATED'],
)

no_year = sum(1 for n in meta if year_of(meta, n) is None)
late = sum(1 for n in meta if (year_of(meta, n) or 0) > ALL_YEARS[1])
print(f'  no start year: {no_year}; start after {ALL_YEARS[1]}: {late}')
nums.count('cohort.noStartYear', no_year)
nums.count('cohort.startAfterWindow', late)

sponsors = {sponsor_of(meta, n) for n in meta}
big = {s for s in sponsors if is_bigpharma(s)}
wide = {s for s in sponsors if is_bigpharma(s, with_midsize=True)}
patterns = sum(len(BIGPHARMA[c]) for c in LARGE)
print(
    f'  big-pharma companies: {len(LARGE)}, patterns: {patterns}; '
    f'lead-sponsor names matched: {len(big)} of {len(sponsors)}; with the '
    f'{len(BIGPHARMA) - len(LARGE)} mid-size companies: {len(wide)} names'
)
nums.count('bigpharma.companies', len(LARGE))
nums.count('bigpharma.mid', len(BIGPHARMA) - len(LARGE))
nums.count('bigpharma.patterns', patterns)
nums.count('bigpharma.sponsorNames', len(big))
nums.count('bigpharma.wide.sponsorNames', len(wide))
nums.count('cohort.sponsorNames', len(sponsors))

print('\n=== primary-analysis records (results cohort) ===')
records = [a for r in pa if r['nct'] in in_results for a in r['analyses']]
strings = [a['p_raw'] for a in records if a['p_raw'] is not None]
invalid = [a for a in records if a['p'] is not None and not valid_p(a['p'])]
invalid_trials = {
    r['nct']
    for r in pa
    if r['nct'] in in_results
    and any(a['p'] is not None and not valid_p(a['p']) for a in r['analyses'])
}
print(f'  analysis records: {len(records)}')
print(
    f'  with a p-value string: {len(strings)} '
    f'({len(set(strings))} distinct strings)'
)
print(
    f'  p outside [0, 1]: {len(invalid)} records in {len(invalid_trials)} '
    f'trials  {[a["p_raw"] for a in invalid]}'
)
# the second retrieval against the results cohort of the first
in_analyses = {r['nct'] for r in pa}
absent = [r for r in results if r['nct'] not in in_analyses]
absent_verdict = sum(r['win'] is not None for r in absent)
not_in_cohort = len(in_analyses - in_results)
print(
    f'  cohort trials absent from this retrieval: {len(absent)} '
    f'({absent_verdict} with a verdict); retrieved but not in the cohort: '
    f'{not_in_cohort}'
)
nums.count('analyses.absent', len(absent))
nums.count('analyses.absent.withVerdict', absent_verdict)
nums.count('analyses.notInCohort', not_in_cohort)
nums.count('pvalue.records', len(records))
nums.count('pvalue.strings', len(strings))
nums.count('pvalue.distinct', len(set(strings)))
nums.count('pvalue.invalid.records', len(invalid))
nums.count('pvalue.invalid.trials', len(invalid_trials))

by_nct = {r['nct']: r for r in pa}
flips = reverse = ambiguous = naive_n = 0
for r in results:
    rec = by_nct.get(r['nct'])
    verdict = trial_verdict(rec['analyses']) if rec else None
    naive = r['min_p'] < ALPHA if valid_p(r['min_p']) else None
    naive_n += naive is not None
    ambiguous += verdict == 'AMB'
    flips += verdict is True and naive is False
    reverse += verdict is False and naive is True
with_verdict = sum(1 for r in results if r['win'] is not None)
with_year = sum(
    1
    for r in results
    if r['win'] is not None and in_window(meta, r['nct'], ALL_YEARS)
)
print(
    f'  trials with a verdict: {with_verdict} ({with_year} with a start year)'
)
print(f'  trials with a numeric minimum p (naive rule): {naive_n}')
print(
    f'  naive miss read as a win once the operator is honoured: {flips} '
    f'({100 * flips / with_verdict:.1f}% of trials with a verdict)'
)
print(f'  operator leaves the verdict undetermined: {ambiguous}')
nums.count('verdict.trials', with_verdict)
nums.count('verdict.noStartYear', with_verdict - with_year)
nums.share('verdict.flips', flips, with_verdict)
nums.count('verdict.flips.reverse', reverse)
nums.count('verdict.ambiguous', ambiguous)
nums.pct('verdict.coverage.pct', 100 * with_verdict / len(results))

# what the flow diagram shows and no other script records: the trials that
# enrolled and started in the main window, by how they ended
enrolled_stops = {s['nct'] for s in stopped if s['status'] != 'WITHDRAWN'}
analysed = (in_results | in_stopped) - (in_stopped - enrolled_stops)
window = {n for n in analysed if in_window(meta, n, ERA)}
window_stopped = window & enrolled_stops
completed = [
    r
    for r in results
    if r['status'] == 'COMPLETED'
    and r['nct'] in window
    and r['nct'] not in enrolled_stops
]
wins = sum(r['win'] is True for r in completed)
active = len(window) - len(window_stopped) - len(completed)
print(f'\n=== trials that enrolled, starting {ERA[0]}-{ERA[1]} ===')
print(
    f'  {len(window)} of {len(analysed)}: stopped {len(window_stopped)}, '
    f'completed and not stopped {len(completed)} ({wins} won), '
    f'neither {active}'
)
nums.count('flow.outsideWindow', len(analysed) - len(window))
nums.count('flow.era.enrolled', len(window))
nums.count('flow.era.stopped', len(window_stopped))
nums.count('flow.era.completed.win', wins)
nums.count('flow.era.other', active)
nums.save()
