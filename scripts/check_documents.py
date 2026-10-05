"""Check that the manuscript and the supplement say what the numbers say.

Four checks. reproduce.sh stops if any of them fails.

  1. No result is typed by hand. Outside the reference list, every digit in
     the title and body of manuscript.tex and supplement.tex, and in
     readme_findings.md, must come from a recorded number (\\num{name} or
     {{name}}). The exceptions are in ALLOWED: names and conventions, not
     results.
  2. References. Every \\cite has a \\bibitem, every \\bibitem is cited, and
     the reference list is in the order of first citation.
  3. Cross-references. Every \\ref points at a label that exists, every table
     and figure is referred to, every \\num names a recorded number, every
     generated table is used and every figure file exists.
  4. Claims. The sentences that state an order, a size or the outcome of a
     test are restated in claims() as conditions on the recorded numbers, so
     a change in the data that makes a sentence false fails the check.

Run after write_numbers.py.
"""

import glob
import os
import re
import sys
from pathlib import Path

from paper_numbers import read_numbers
from repo_files import PAPER, D, read_text

MANUSCRIPT, SUPPLEMENT = PAPER + 'manuscript.tex', PAPER + 'supplement.tex'
README_TEMPLATE = PAPER + 'readme_findings.md'
# the supplement sees the manuscript's labels under this prefix
MAIN_PREFIX = 'main-'
BUCKETS = ('eff', 'op', 'com', 'saf', 'unk')

# Digits that are names or conventions, not results.
ALLOWED = [
    r'[Pp]hase[- ~]\d',  # phase-3, Phase 2/Phase~3
    r'COVID-19',
    r'\b95\\% (?:CI|intervals?)\b',  # the level of every interval
    r'\$\[0, 1\]\$',  # the range of a p-value
    r'above 1\b',  # the null value of a ratio
    r'\\chi\^2',
    r'\bv2 API',  # the registry's API version
    r'^\d+\. ',  # a list marker in the README
    # the author's ORCID on the title page and in the Declarations
    r'(?:href\{https://orcid\.org/)?0000-0002-3672-9931\}?',
]
# Commands whose arguments are names or layout, removed before the scan.
NOT_TEXT = [
    r'\\(?:num|ref|label|cite|tablebody|url|vspace|bibitem)\{[^}]*\}',
    r'\{\{[A-Za-z0-9.]+\}\}',
    r'\\includegraphics(?:\[[^\]]*\])?\{[^}]*\}',
    r'\\setlength\{[^}]*\}\{[^}]*\}',
    r'\\multicolumn\{\d+\}\{[^}]*\}',
    r'\\cmidrule(?:\([^)]*\))?\{[^}]*\}',
    # a tabular's column specification, braces nested up to three deep
    r'\\begin\{tabular\}\{(?:[^{}]|\{(?:[^{}]|\{[^{}]*\})*\})*\}',
    r'\\begin\{[a-z]+\}\[[^\]]*\]',
]


def uncommented(name):
    """The lines of a LaTeX file with their comments removed."""
    return [re.sub(r'(?<!\\)%.*', '', x) for x in read_text(name).split('\n')]


def reader_lines(name):
    """(line number, text) for what a reader sees: the title and everything
    from the start of the document to the reference list."""
    inside = False
    for number, line in enumerate(uncommented(name), 1):
        if line.startswith('\\begin{thebibliography}'):
            return
        inside = inside or line.startswith('\\begin{document}')
        if inside or line.startswith('\\title{'):
            yield number, line


def typed_numbers(name, lines):
    problems = []
    for number, line in lines:
        for pattern in NOT_TEXT:
            line = re.sub(pattern, '', line)
        allowed = [
            m.span() for pattern in ALLOWED for m in re.finditer(pattern, line)
        ]
        for m in re.finditer(r'\d+(?:[.,]\d+)*', line):
            if any(a <= m.start() < b for a, b in allowed):
                continue
            start, end = max(0, m.start() - 30), m.end() + 20
            problems.append(
                f'{name}:{number}: {m.group()} is typed by hand: '
                f'...{line[start:end].strip()}...'
            )
    return problems


def p_values_outside_math(name, lines):
    """A p-value is recorded in scientific notation once it is small, which
    only math mode can print: every \\num of a p-value must be inside $...$,
    whatever its value is today."""
    problems = []
    for number, line in lines:
        text = re.sub(r'\$[^$]*\$', '', line)
        for key in re.findall(r'\\num\{([^}]*)\}', text):
            if re.search(r'(?:^|\.)p$', key):
                problems.append(
                    f'{name}:{number}: the p-value {key} is outside math mode'
                )
    return problems


def references(text):
    cited = []
    for group in re.findall(r'\\cite\{([^}]*)\}', text):
        cited += [
            k.strip() for k in group.split(',') if k.strip() not in cited
        ]
    listed = re.findall(r'\\bibitem\{([^}]*)\}', text)
    problems = [
        f'cited but not in the reference list: {k}'
        for k in cited
        if k not in listed
    ]
    problems += [
        f'in the reference list but never cited: {k}'
        for k in listed
        if k not in cited
    ]
    if not problems and cited != listed:
        problems.append(
            'the reference list is not in the order of first citation: '
            f'{", ".join(cited)}'
        )
    return problems, len(listed)


def cross_references(main, supp, numbers):
    def found(command, text):
        return re.findall(
            r'\\' + command + r'(?:\[[^\]]*\])?\{([^}]*)\}', text
        )

    main_labels, supp_labels = found('label', main), found('label', supp)
    problems = [
        f'label defined twice: {k}'
        for k in sorted(set(main_labels + supp_labels))
        if (main_labels + supp_labels).count(k) > 1
    ]
    targets = {
        MANUSCRIPT: set(main_labels + supp_labels),
        SUPPLEMENT: set(supp_labels) | {MAIN_PREFIX + k for k in main_labels},
    }
    used = set()
    for name, text in ((MANUSCRIPT, main), (SUPPLEMENT, supp)):
        for ref in found('ref', text):
            used.add(ref.removeprefix(MAIN_PREFIX))
            if ref not in targets[name]:
                problems.append(f'{name}: \\ref to a missing label: {ref}')
        for number in found('num', text):
            if number not in numbers:
                problems.append(f'{name}: \\num of a missing number: {number}')
        for path in found('includegraphics', text):
            if not os.path.exists(D + PAPER + path):
                problems.append(f'{name}: missing figure file: {path}')
    problems += [
        f'{k} is a table or figure that the text never refers to'
        for k in main_labels + supp_labels
        if k.startswith(('tab:', 'fig:')) and k not in used
    ]
    tables = {Path(p).stem for p in glob.glob(D + PAPER + 'tables/*.tex')}
    bodies = set(found('tablebody', main + supp))
    problems += [
        f'{PAPER}tables/{k}.tex is missing' for k in sorted(bodies - tables)
    ]
    problems += [
        f'{PAPER}tables/{k}.tex is not used' for k in sorted(tables - bodies)
    ]
    return problems, len(used)


def claims(numbers):
    """(sentence, whether the recorded numbers bear it out)."""

    def v(name):
        return numbers[name]['value']

    def shares(key, suffix='.pct'):
        return {b: v(f'{key}.{b}{suffix}') for b in BUCKETS}

    def close(a, b):
        return abs(a - b) < 0.01

    def ranked(s):
        return sorted(s, key=lambda b: -s[b])

    def named(pattern):
        return {
            k: e['value'] for k, e in numbers.items() if re.match(pattern, k)
        }

    windows = ('era', 'complete', 'all')
    enrolled = {w: shares(f'decomp.enrolled.{w}.all') for w in windows}
    registered = shares('decomp.registered.era.all')
    big = shares('decomp.enrolled.era.big')
    rest = shares('decomp.enrolled.era.rest')
    cov = 'coverage.enrolled.all'
    raw, pooled, adjusted = (
        shares(f'{cov}.{k}', '') for k in ('raw', 'pooled', 'adjusted')
    )
    tie = shares('coverage.registered.all.pooled', '')
    correction = pooled['eff'] - raw['eff']
    population = raw['eff'] - registered['eff']
    hw, saf = v('hwang.eff.pct'), v('hwang.saf.pct')
    variants = (
        'asAnalysed',
        'regToSafety',
        'extToEfficacy',
        'busToUnknown',
        'sponsorToUnknown',
        'modelEfficacyToUnknown',
        'sponsorToSafety',
        'decisionsToSafety',
    )
    tax = {
        (s, t): shares(f'tax.{s}.{t}', '')
        for s in ('all', 'big')
        for t in variants
    }
    base = tax['all', 'asAnalysed']
    rules = [
        v(f'{k}.pct')
        for k in (
            'combine.all.and',
            'diag.all.naive',
            'diag.all.sidak',
            'diag.all.single',
        )
    ]
    agree = named(r'valid\.cat\.[a-z0-9]+\.agree$')
    lowest = sorted(agree, key=lambda k: agree[k])[:2]
    areas = named(r'area\.[A-Z][A-Za-z]*\.miss\.pct$')
    era = 'recover.enrolled.era'
    decomps = named(r'(decomp\.[a-z]+\.[a-z]+\.[a-z]+|withdrawn\.era)\.n$')

    return [
        # the cohort and the verdict
        (
            'one cohort trial is absent from the second retrieval, no verdict',
            v('analyses.absent') == 1
            and v('analyses.absent.withVerdict') == 0,
        ),
        (
            'every changed verdict goes from miss to win',
            v('verdict.flips.reverse') == 0 < v('verdict.flips.n'),
        ),
        (
            'the two counts of trials with a verdict differ by the undated',
            v('verdict.trials')
            == v('miss.all.trials') + v('verdict.noStartYear'),
        ),
        # the decomposition and the population
        (
            'efficacy is ahead of operational causes in every window',
            all(s['eff'] > s['op'] for s in enrolled.values()),
        ),
        (
            'efficacy and operational causes are close in every window',
            all(abs(s['eff'] - s['op']) < 5 for s in enrolled.values()),
        ),
        (
            'their intervals overlap in the main window ("level")',
            v('decomp.enrolled.era.all.eff.lo')
            < v('decomp.enrolled.era.all.op.hi'),
        ),
        (
            'they are the two largest causes among trials that enrolled',
            ranked(enrolled['era'])[:2] == ['eff', 'op'],
        ),
        (
            'withdrawn registrations rarely stop for efficacy',
            v('withdrawn.era.eff.pct') < 2,
        ),
        (
            'they stop for business reasons, funding or logistics',
            v('withdrawn.era.op.pct') + v('withdrawn.era.com.pct') > 90,
        ),
        (
            'with withdrawn registrations counted, operational comes first',
            ranked(registered)[0] == 'op',
        ),
        (
            'and outrank efficacy by a wide margin',
            registered['op'] - registered['eff'] > 10,
        ),
        ('counting them lowers the efficacy share markedly', population > 5),
        (
            'the efficacy share is higher in the window that has read out',
            enrolled['complete']['eff'] > enrolled['era']['eff'],
        ),
        # endpoint-reporting coverage
        (
            'trials without a verdict are far more often single-arm',
            v(f'{cov}.singleArm.unreported.pct')
            > 5 * v(f'{cov}.singleArm.reported.pct'),
        ),
        (
            'almost every comparator trial has two or more arm groups',
            100 * v(f'{cov}.comparator.noArmGroups')
            < v(f'{cov}.comparator.reported')
            + v(f'{cov}.comparator.unreported'),
        ),
        (
            'the shares with and without a verdict add up',
            abs(v(f'{cov}.reported.pct') + v(f'{cov}.unreported.pct') - 100)
            < 0.01,
        ),
        (
            'Dechartres et al. found a similar share with a posted p-value',
            abs(v('lit.dechartres.reported.pct') - v(f'{cov}.reported.pct'))
            < 5,
        ),
        (
            'posted tests are significant more often than unposted ones',
            v('lit.dechartres.reported.significant.pct')
            > v('lit.dechartres.calculated.significant.pct'),
        ),
        (
            'a verdict is more likely for big pharma',
            v('covmodel.bigPharma.lo') > 1,
        ),
        ('less likely with each later start year', v('covmodel.year.hi') < 1),
        (
            'less likely with more primary outcomes',
            v('covmodel.logPrimaries.hi') < 1,
        ),
        (
            'much less likely for single-arm studies',
            v('covmodel.singleArm.hi') < 0.5,
        ),
        (
            'imputation raises the efficacy share and lowers operational',
            pooled['eff'] > raw['eff'] and pooled['op'] < raw['op'],
        ),
        (
            'so does the adjusted imputation',
            adjusted['eff'] > raw['eff'] and adjusted['op'] < raw['op'],
        ),
        (
            'after imputation efficacy leads, clear of operational causes',
            ranked(pooled)[0] == 'eff' and pooled['eff'] - pooled['op'] > 5,
        ),
        (
            'the bound is above the pooled imputation',
            v(f'{cov}.upper.eff') > pooled['eff'],
        ),
        (
            'the sampling interval contains the pooled share',
            v(f'{cov}.pooled.eff.lo')
            < pooled['eff']
            < v(f'{cov}.pooled.eff.hi'),
        ),
        (
            'and is narrower than the correction itself',
            v(f'{cov}.pooled.eff.hi') - v(f'{cov}.pooled.eff.lo') < correction,
        ),
        (
            'over all years more stops lack a reason and unknown is larger',
            v('decomp.enrolled.all.all.unk.pct')
            > v('decomp.enrolled.era.all.unk.pct')
            and v('recover.enrolled.all.final.reason.pct')
            < v('recover.enrolled.era.final.reason.pct'),
        ),
        (
            'big-pharma failures equal all completed misses by coincidence',
            v('hwang.enrolled.n') == v('decomp.enrolled.era.all.completedMiss')
            and v('decomp.enrolled.era.big.completedMiss')
            < v('hwang.enrolled.n'),
        ),
        (
            'the clustered interval is wider than the Wilson interval',
            v('hwang.enrolled.clustered.hi') - v('hwang.enrolled.clustered.lo')
            > v('decomp.enrolled.era.big.eff.hi')
            - v('decomp.enrolled.era.big.eff.lo'),
        ),
        (
            'the two choices move the efficacy share by a similar amount',
            0.5 < correction / population < 2,
        ),
        (
            'with withdrawn registrations counted, imputation gives a tie',
            abs(tie['eff'] - tie['op']) < 1,
        ),
        # the comparison with Hwang et al.
        (
            'efficacy is the leading cause in the big-pharma stratum',
            ranked(big)[0] == 'eff',
        ),
        (
            'the big-pharma share is not distinguishable from Hwang et al.',
            min(
                v('hwang.enrolled.p'),
                v('hwang.enrolled.clustered.p'),
                v('hwang.complete.p'),
                v('hwang.complete.clustered.p'),
            )
            > v('alpha'),
        ),
        (
            'its clustered interval overlaps the interval of their estimate',
            v('hwang.enrolled.clustered.hi') > v('hwang.eff.lo')
            and v('hwang.enrolled.clustered.lo') < v('hwang.eff.hi'),
        ),
        (
            'agreement by bucket is higher than agreement by category',
            v('valid.bucket.agree.pct') > v('valid.agree.pct')
            and v('valid.bucket.weighted.pct') > v('valid.weighted.pct'),
        ),
        (
            'with mid-size companies: lower, from no difference to well below',
            v('hwang.wide.eff.pct') < v('hwang.enrolled.eff.pct') < hw
            and v('hwang.wide.clustered.p') > v('alpha')
            and v('hwang.wide.diff.lo') < -10
            and v('hwang.wide.diff.hi') > 0,
        ),
        (
            'the novel subset is lower, not significantly; lifecycle higher',
            v('novelty.novel.eff.pct') < v('hwang.enrolled.eff.pct') < hw
            and v('novelty.novel.hwang.p') > v('alpha')
            and v('novelty.novel.hwang.diff.lo')
            < 0
            < v('novelty.novel.hwang.diff.hi')
            and v('novelty.lifecycle.eff.pct') > v('novelty.novel.eff.pct'),
        ),
        (
            'novel and lifecycle miss equally often; novel has more business',
            abs(v('novelty.novel.miss.pct') - v('novelty.lifecycle.miss.pct'))
            < 1
            and v('novelty.novel.com.pct') > v('novelty.lifecycle.com.pct'),
        ),
        (
            'the interval of the difference spans several points each way',
            v('hwang.enrolled.diff.lo') <= -3
            and v('hwang.enrolled.diff.hi') >= 3,
        ),
        (
            'with withdrawn registrations counted it falls below theirs',
            max(v('hwang.registered.p'), v('hwang.registered.clustered.p'))
            < v('alpha')
            and v('hwang.registered.diff.hi') < 0
            and v('hwang.registered.eff.pct') < big['eff'],
        ),
        (
            'a stricter win rule puts efficacy ahead and raises its share',
            v('winrule.any.all.eff.pct') == raw['eff']
            and v('winrule.any.big.eff.pct') == big['eff']
            and all(
                v(f'winrule.{rule}.all.eff.pct')
                > v(f'winrule.{rule}.all.op.pct')
                for rule in ('and', 'strict')
            )
            and raw['eff']
            < v('winrule.and.all.eff.pct')
            < v('winrule.strict.all.eff.pct')
            and big['eff']
            < v('winrule.and.big.eff.pct')
            < v('winrule.strict.big.eff.pct'),
        ),
        (
            'fewer big-pharma failures are operational',
            big['op'] < v('decomp.enrolled.era.rest.op.pct'),
        ),
        (
            'the imputed share raises the big-pharma figure above theirs',
            v('coverage.enrolled.big.pooled.eff') > hw,
        ),
        (
            'the two scripts agree on the big-pharma stratum',
            v('hwang.enrolled.n')
            == v('decomp.enrolled.era.big.n')
            == v('novelty.all.n')
            and v('hwang.enrolled.eff.pct') == big['eff'],
        ),
        (
            "Hwang's three reasons leave a remainder that is not negative",
            v('hwang.other.n') >= 0
            and v('hwang.eff.n') + v('hwang.saf.n') + v('hwang.com.n')
            <= v('hwang.failed'),
        ),
        (
            'novel, lifecycle and unflagged failures add up',
            v('novelty.novel.n')
            + v('novelty.lifecycle.n')
            + v('novelty.unflagged.n')
            == v('novelty.all.n'),
        ),
        # safety and the taxonomy
        (
            'the safety share is far below that of Hwang et al.',
            max(enrolled['era']['saf'], big['saf']) < saf / 4,
        ),
        (
            'the fold differences are the ratios of the shares',
            close(v('hwang.safetyFold.all'), saf / enrolled['era']['saf'])
            and close(v('hwang.safetyFold.big'), saf / big['saf']),
        ),
        (
            'and are quoted from the smaller to the larger',
            v('hwang.safetyFold.big') < v('hwang.safetyFold.all'),
        ),
        (
            'Razuvayevskaya et al. found a similarly small safety share',
            v('lit.razuv.safety.pct') < 5,
        ),
        (
            'five assignments are varied and two scenarios shown',
            v('tax.assignments') == 5
            and v('tax.scenarios') == 2
            and len(variants) == 1 + 5 + 2,
        ),
        (
            'second-pass efficacy labels: none big pharma; as unknown, level',
            v('audit.eff.monitoring')
            + v('audit.eff.interim')
            + v('audit.eff.other')
            == v('audit.eff.n')
            <= v('audit.model.n')
            and tax['big', 'modelEfficacyToUnknown']['eff']
            == tax['big', 'asAnalysed']['eff']
            and 0
            < tax['all', 'modelEfficacyToUnknown']['eff']
            - tax['all', 'modelEfficacyToUnknown']['op']
            < 0.5,
        ),
        (
            'sponsor decisions as safety: below theirs; with business, above',
            all(
                tax[s, 'sponsorToSafety']['saf']
                < saf
                < tax[s, 'decisionsToSafety']['saf']
                for s in ('all', 'big')
            ),
        ),
        (
            'the wider pattern is a small part of the sponsor rule',
            0 < v('pass2.rule.sponsor.wide') < v('pass2.rule.sponsor') / 4,
        ),
        (
            'moving regulatory holds raises the safety share',
            all(
                tax[s, 'regToSafety']['saf'] > tax[s, 'asAnalysed']['saf']
                for s in ('all', 'big')
            ),
        ),
        (
            'moving external evidence raises the efficacy share',
            tax['all', 'extToEfficacy']['eff'] > base['eff'],
        ),
        (
            'moving business or strategic lowers commercial, raises unknown',
            tax['all', 'busToUnknown']['com'] < base['com']
            and tax['all', 'busToUnknown']['unk'] > base['unk'],
        ),
        (
            'sponsor decisions as unknown lower commercial, raise unknown',
            tax['all', 'sponsorToUnknown']['com'] < base['com']
            and tax['all', 'sponsorToUnknown']['unk'] > base['unk'],
        ),
        (
            'none of the five changes the order of efficacy and operational',
            all(s['eff'] > s['op'] for s in tax.values()),
        ),
        (
            'commercial and unknown move by several points, safety by less',
            min(
                base['com'] - tax['all', 'busToUnknown']['com'],
                tax['all', 'busToUnknown']['unk'] - base['unk'],
            )
            > 3
            > tax['all', 'regToSafety']['saf'] - base['saf'],
        ),
        (
            'the sampled categories have the sample size per category',
            v('tax.external.n')
            == v('tax.business.n')
            == v('valid.perCategory'),
        ),
        # miss rate
        (
            'the verdict is the most lenient rule, every-outcome strictest',
            v('miss.all.pct') <= min(rules)
            and v('combine.all.strict.pct') >= max(rules),
        ),
        (
            'the any-outcome rule is the verdict',
            all(
                v(f'combine.{w}.any.n') == v(f'miss.{w}.n')
                and v(f'combine.{w}.trials') == v(f'miss.{w}.trials')
                for w in ('all', 'era')
            ),
        ),
        (
            'excluding non-inferiority designs changes the rate little',
            abs(v('ni.all.superiority.miss.pct') - v('miss.all.pct')) < 1,
        ),
        (
            'there is no linear trend',
            v('trend.ca.p') > v('alpha')
            and v('trend.or.lo') < 1 < v('trend.or.hi'),
        ),
        (
            'homogeneity across years is not rejected',
            v('trend.het.p') > v('alpha'),
        ),
        (
            'with the operator stripped the trend test shows a decline',
            v('trend.naive.p') < v('alpha') and v('trend.naive.z') < 0,
        ),
        # sponsor class and area
        (
            'big-pharma trials miss less often',
            v('sponsor.big.miss.pct') < v('sponsor.rest.miss.pct')
            and max(v('sponsor.p'), v('sponsor.or.p')) < v('alpha')
            and v('sponsor.or') < 1,
        ),
        (
            'operational is the largest bucket for other sponsors',
            ranked(rest)[0] == 'op',
        ),
        ('miss rates differ between areas', v('area.het.p') < v('alpha')),
        ('there are six areas', len(areas) == 6),
        (
            'the quoted range is the range over the areas',
            close(min(areas.values()), v('strat.miss.min'))
            and close(max(areas.values()), v('strat.miss.max')),
        ),
        # validation and recoverability
        (
            'agreement is complete for funding and COVID-19',
            v('valid.cat.funding.agree')
            == v('valid.cat.covid.agree')
            == v('valid.perCategory'),
        ),
        (
            'and lowest for external evidence and business or strategic',
            lowest
            == [
                'valid.cat.externalevidence.agree',
                'valid.cat.businessstrategic.agree',
            ],
        ),
        (
            'there is one sample per category',
            len(agree) == v('valid.categories')
            and v('valid.sample') == len(agree) * v('valid.perCategory'),
        ),
        (
            'the two retrievals return the same minimum p',
            v('stability.sameP') == v('stability.compared'),
        ),
        (
            'and nearly always the same number of primary outcomes',
            v('stability.sameCount.pct') > 99,
        ),
        (
            'each pass leaves fewer trials without a reason',
            v(f'{era}.first.noReason.pct')
            > v(f'{era}.second.unclear.pct')
            >= v(f'{era}.final.unclear.pct'),
        ),
        (
            'sponsor-undisclosed adds to the trials with a reason',
            v(f'{era}.final.reason.pct') < v(f'{era}.final.notUnclear.pct'),
        ),
        # counts that must add up
        (
            'the two filters overlap as stated',
            v('cohort.results') + v('cohort.stopped') - v('cohort.both')
            == v('cohort.unique'),
        ),
        (
            'the statuses add up to the stopped registrations',
            v('cohort.terminated')
            + v('cohort.withdrawn')
            + v('cohort.suspended')
            == v('cohort.stopped'),
        ),
        (
            'the analysed population is the cohort less the withdrawn',
            v('cohort.unique') - v('cohort.withdrawn') == v('cohort.analysed'),
        ),
        (
            'the second pass accounts for every registration it read',
            v('pass2.byModel') + v('pass2.byRule') + v('pass2.unclear')
            == v('pass2.input'),
        ),
        (
            'the three rules add up',
            v('pass2.rule.sponsor')
            + v('pass2.rule.notStarted')
            + v('pass2.rule.enrollment')
            == v('pass2.byRule'),
        ),
        (
            'every decomposition adds up to its failures',
            all(
                sum(v(f'{k[:-2]}.{b}.n') for b in BUCKETS) == n
                for k, n in decomps.items()
            ),
        ),
        # the flow diagram
        (
            'the trials that enrolled are in the main window or outside it',
            v('flow.era.enrolled') + v('flow.outsideWindow')
            == v('cohort.analysed'),
        ),
        (
            'those of the main window stopped, completed or did neither',
            v('flow.era.stopped') + v(f'{cov}.completed') + v('flow.era.other')
            == v('flow.era.enrolled'),
        ),
        (
            'its stopped trials are the stopped registrations that enrolled',
            v('flow.era.stopped')
            == v('cohort.era.stopped') - v('cohort.era.withdrawn.n')
            == v(f'{era}.final.n') + v('decomp.enrolled.era.all.benefit'),
        ),
        (
            'its completed trials won, missed or have no verdict',
            v('flow.era.completed.win')
            + v('decomp.enrolled.era.all.completedMiss')
            == v(f'{cov}.reported.n')
            and v(f'{cov}.reported.n') + v(f'{cov}.unreported.n')
            == v(f'{cov}.completed'),
        ),
        (
            'those without a verdict are single-arm or have a comparator arm',
            v(f'{cov}.singleArm.unreported.n')
            + v(f'{cov}.comparator.unreported')
            == v(f'{cov}.unreported.n'),
        ),
        (
            'the failures are the early stops and the completed misses',
            v(f'{era}.final.n') + v('decomp.enrolled.era.all.completedMiss')
            == v('decomp.enrolled.era.all.n'),
        ),
    ]


def main():
    numbers = read_numbers()
    main_text = '\n'.join(uncommented(MANUSCRIPT))
    supp_text = '\n'.join(uncommented(SUPPLEMENT))
    typed = typed_numbers(MANUSCRIPT, reader_lines(MANUSCRIPT))
    typed += typed_numbers(SUPPLEMENT, reader_lines(SUPPLEMENT))
    typed += typed_numbers(
        README_TEMPLATE,
        enumerate(read_text(README_TEMPLATE).split('\n'), 1),
    )
    typed += p_values_outside_math(MANUSCRIPT, reader_lines(MANUSCRIPT))
    typed += p_values_outside_math(SUPPLEMENT, reader_lines(SUPPLEMENT))
    cited, n_references = references(main_text)
    if re.search(r'\\cite\{', supp_text):
        cited.append(f'{SUPPLEMENT} cites, but has no reference list')
    crossed, n_labels = cross_references(main_text, supp_text, numbers)
    stated = claims(numbers)
    false = [
        f'not borne out: {sentence}' for sentence, holds in stated if not holds
    ]

    problems = typed + cited + crossed + false
    for problem in problems:
        print('  ' + problem)
    if problems:
        print(f'check_documents: {len(problems)} problems')
        sys.exit(1)
    print(
        'check_documents: no number typed by hand; '
        f'{n_references} references cited in order; '
        f'{n_labels} labels resolved; {len(stated)} claims hold'
    )


if __name__ == '__main__':
    main()
