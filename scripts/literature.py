"""Numbers quoted from other studies, with where each one comes from.

They are recorded like the paper's own numbers so that the documents carry no
hand-typed figure. The counts from Hwang et al. are in failure_decomp.py,
because the analysis uses them.
"""

from paper_numbers import Numbers

nums = Numbers('literature')

# Hwang et al., JAMA Intern Med 2016;176:1826. Methods: novel therapeutics
# that entered pivotal trials between 1998 and 2008.
nums.text('lit.hwang.year', 2016)
nums.text('lit.hwang.firstYear', 1998)
nums.text('lit.hwang.lastYear', 2008)

# Final Rule, 42 CFR Part 11, Fed Regist 2016;81:64982. "This rule is
# effective on January 18, 2017."
nums.text('lit.finalRule.effective', '18 January 2017')

# Razuvayevskaya et al., Nat Genet 2024;56:1862. Results: "28,561 stopped
# trials"; "99% of the trials were classified with at least one of the 15
# potential reasons"; "A total of 977 trials (3.38%) were classified as
# stopped because of 'safety or side effects'".
nums.count('lit.razuv.trials', 28561)
nums.count('lit.razuv.classified.pct', 99)
nums.share('lit.razuv.safety', 977, 28561)

# Jovanovic et al., BMC Med Res Methodol 2026;26:35. Results: 81 studies
# included, 73 using ClinicalTrials.gov; "The median failure proportion in
# all included studies was 18%, ranging from 3% ... to 51.8%"; the model of
# methodological factors "showed a 27.5% deviance reduction".
nums.count('lit.jovanovic.studies', 81)
nums.share('lit.jovanovic.ctgov', 73, 81)
nums.count('lit.jovanovic.min.pct', 3)
nums.pct('lit.jovanovic.max.pct', 51.8)
nums.pct('lit.jovanovic.deviance.pct', 27.5)

# Dechartres et al., BMC Med 2016;14:192. Results: of 2823 completed phase 3
# or 4 superiority trials with posted results, 1400 reported a treatment
# effect estimate and/or p-value, 844 of them significant; a p-value could be
# calculated for 929 of the others, 342 of them significant.
nums.count('lit.dechartres.trials', 2823)
nums.share('lit.dechartres.reported', 1400, 2823)
nums.share('lit.dechartres.reported.significant', 844, 1400)
nums.share('lit.dechartres.calculated.significant', 342, 929)

# DeVito et al., Lancet 2020;395:361. Findings: 4209 trials were due to
# report results; 2686 had results submitted at any time.
nums.count('lit.devito.due', 4209)
nums.share('lit.devito.submitted', 2686, 4209)
nums.save()
print(f'literature: {len(nums.entries)} numbers recorded')
