# Structured-data reporting shapes the apparent causes of phase-3 trial failure

Code, labels and data for the paper "Structured-data reporting shapes the apparent causes of phase-3 trial failure: an automated decomposition of ClinicalTrials.gov records" by Tommy Carstensen.

The paper classifies why phase-3 trials fail, using only ClinicalTrials.gov and linked PubMed abstracts, and asks where a registry-only answer is misleading. Its reference point is the manual study of Hwang et al. (JAMA Intern Med 2016). Every number in the manuscript and the supplement is written by the scripts in this repository.

To read the paper: `bash build_pdf.sh` builds `paper/manuscript.pdf` and `paper/supplement.pdf` from the sources in `paper/`; the link to the posted preprint is added here when there is one.

## Findings

The numbers in this section are filled in by `scripts/write_numbers.py`; the wording is in `paper/readme_findings.md`.

<!-- findings:start -->
1. **Counting registrations that never enrolled changes the answer.** 32.2% of the stopped registrations that started in 2017-2026 were withdrawn before enrolling anyone. With them counted as failures, operational causes (40.2%) outrank efficacy (27.2%). Among trials that enrolled, efficacy is 37.1% of failures and operational causes 36.5%.
2. **Endpoint reporting under-fills the efficacy bucket.** Only 47.3% of completed trials with posted results that started in 2017-2026 carry a usable primary p-value, and the trials without one are far more often single-arm (27.3% against 2.8%). Imputing misses only for unreported trials that have a comparator arm raises the efficacy share to 46.8% and lowers the operational share to 30.9%. If every such trial had missed, efficacy would be 62.3%.
3. **In the big-pharma stratum the efficacy share is not distinguishable from that of Hwang et al., a comparison by proxy that does not establish agreement.** 53.7% of 382 failures against 56.7% of 344 (program-clustered p = 0.46; difference -11.0 to 5.0 percentage points). The share is 48.3% among trials of drugs with no earlier phase-3 win, the closer counterpart of their cohort (unclustered p = 0.057), and 51.1% with 18 mid-size companies added (clustered p = 0.14). It is lower than theirs when withdrawn registrations are counted (45.8%, clustered p = 0.0052).
4. **Structured data record few safety failures.** Safety is 2.5% of failures (3.1% in the big-pharma stratum) against 17.2% in Hwang et al. The registry fields cannot show how many safety-driven stops are registered as sponsor or business decisions: with every bare sponsor decision counted as safety the share would be 9.3%, and with every business or strategic stop as well, 22.2%.
5. **A reason is stated or can be recovered for most stopped trials.** 89.4% of the stopped trials that enrolled and started in 2017-2026, and 82.1% over all years. Counting every label other than "unclear" as a reason gives 98.2% and 86.6%.
6. **About three in ten trials with a usable primary p-value miss the primary endpoint, with no evidence of a linear trend.** 31.5% over all years. By start year the rate ran between 25.8% and 37.8% across 2005-2021 (Cochran-Armitage p = 0.54). Requiring every primary outcome with a usable p-value to be significant raises it to 36.9%, and to 44.0% if an outcome without one counts as not significant. Under those two rules efficacy would be 39.9% and 43.3% of the failures of all sponsors among trials that enrolled and started in 2017-2026.
7. **Big-pharma trials miss less often.** 25.4% against 34.9% for all other sponsors, among trials with a verdict that started in 2017-2026.
8. **A naive p-value parser is itself a source of bias.** Stripping the comparison operator from a string such as `<0.05` scores a win as a miss. Honouring the operator changes 108 trial verdicts (`record_sig` in `failure_decomp.py`).
<!-- findings:end -->

## Reproduce

Python with the packages in `requirements.txt`. The code is written for Python 3.12 or later; it was run, and the committed outputs produced, with Python 3.14 and the pinned versions only.

    pip install -r requirements.txt
    bash reproduce.sh

`reproduce.sh` runs every analysis script against the archived data, rewrites the numbers, tables and figures, checks the documents against the numbers (`check_documents.py`), and then checks that everything it regenerated is identical to the committed copy. It takes under a minute. The figures are redrawn from the numbers it has just checked; on another platform or with another matplotlib version their bytes can differ from the committed files, which `reproduce.sh` reports without failing.

`bash build_pdf.sh` builds `paper/manuscript.pdf` and `paper/supplement.pdf`. It needs `pdflatex` from a LaTeX distribution that has the packages the two documents load (`geometry`, `amsmath`, `amssymb`, `graphicx`, `booktabs`, `url`, `hyperref`, `parskip`, `enumitem`, `tikz`, `array`, `float` and `xr`); TeX Live and MacTeX have them all.

## Layout

| folder | content |
|--------|---------|
| `paper/` | `manuscript.tex` and `supplement.tex`, with what they read: `numbers.tex`, `tables/` and `figures/`, all written by the scripts |
| `scripts/` | every Python script; the Pipeline table below says what each one does |
| `numbers/` | the recorded numbers, one JSON file per analysis script |
| `data/registry/` | the archived ClinicalTrials.gov retrievals, which are the data of record |
| `data/labels/` | the labels of each classification pass (`why_out/`, `detail_out/`, `pub_out/`) and the two merged label files |
| `data/validation/` | the validation sample and its adjudication |
| `data/pubmed/` | the PMIDs of the publications linked to the registrations that were still without a reason after the second pass |
| `prompts/` | the classification prompts |

`reproduce.sh` and `build_pdf.sh` are at the top level and run from any directory, as does each script.

## Data of record

The ClinicalTrials.gov API returns the current version of each record, so a new pull returns today's registry, not the one the paper analysed. The retrievals the paper was computed from are archived in `data/registry/` and are the data of record:

| file | retrieved | content |
|------|-----------|---------|
| `ph3_results.json`, `ph3_stopped.json` | 9 July 2026 | phase-3 registrations with posted results; phase-3 registrations terminated, withdrawn or suspended |
| `ph3_meta.json`, `ph3_conditions.json`, `ph3_arms.json` | 9 July 2026 | start date, lead sponsor, drugs, conditions and arm groups of every registration in either cohort |
| `unclear_enriched.json`, `residual_refs.json` | 9 July 2026 | detailed description, enrollment and linked references of stopped registrations whose reason was not clear from `whyStopped` |
| `ph3_primary_analyses.json` | 20 August 2026 | the full primary-outcome statistical-analysis records |

The pull scripts refuse to replace these files unless `--overwrite` is given. Running them with `--overwrite` gives a newer registry and therefore different numbers. A phase filter of 3 also returns registrations designated Phase 2/Phase 3.

The PubMed abstracts read in the third classification pass are third-party text and are not redistributed. `fetch_pubmed.py` retrieves them from the PMIDs in `residual_refs.json` into `data/pubmed/`, beside `nct_pmids.json`, which lists the PMIDs of each of those registrations. No analysis script needs them.

Sources: ClinicalTrials.gov API v2 and the NCBI E-utilities. Both are public and need no key. Registry data are provided by the U.S. National Library of Medicine; this work is not endorsed by it.

## Pipeline

Every script is in `scripts/`. In the output column, the registry files are in `data/registry/`, the label folders and label files in `data/labels/`, and `numbers.tex`, `tables/` and `figures/` in `paper/`. The prompts are in `prompts/`.

| step | script | output |
|------|--------|--------|
| Pull the two cohorts | `pull_results_stopped.py` | `ph3_results.json`, `ph3_stopped.json` |
| Pull start date, sponsor, conditions, arm groups | `pull_meta.py`, `pull_conditions.py`, `pull_arms.py` | `ph3_meta.json`, `ph3_conditions.json`, `ph3_arms.json` |
| Pull the full primary-analysis records | `pull_primary_analyses.py` | `ph3_primary_analyses.json` |
| First pass: classify the `whyStopped` string | language-model agents with `TAXONOMY.md` | `why_out/*.tsv` |
| Second pass: detailed description, plus three rules | `enrich_unclear.py`, agents with `DETAIL_TASK.md`, `reclassify.py` | `detail_out/*.tsv`, `unclear_reclassified.json` |
| Third pass: linked publications | `probe_refs.py`, `fetch_pubmed.py`, agents with `PUB_TASK.md`, `merge_pub_labels.py` | `pub_out/*.tsv`, `unclear_reclassified_v2.json` |
| Counting rules, shared by every script | `failure_decomp.py` | imported |
| Cohort counts and the p-value strings | `cohort.py` | numbers |
| Numbers quoted from other studies, with their sources | `literature.py` | numbers |
| Recoverability of termination reasons | `recoverability.py` | numbers |
| Failure decomposition and miss rate | `decomposition.py` | numbers |
| Endpoint-reporting coverage and imputation | `coverage.py` | numbers |
| Miss-rate diagnostics, taxonomy sensitivity | `sensitivity.py` | numbers, `tables/taxonomy.tex` |
| Tests and intervals | `inference.py` | numbers, `tables/yearly.tex`, `tables/covmodel.tex` |
| Endpoint design and win rules | `endpoint_design.py` | numbers |
| Subject drugs, programs, novel versus lifecycle | `subjects.py`, `dedup_arms.py`, `novelty_flag.py` | numbers, `tables/subjects.tex`, `tables/novelty.tex` |
| Therapeutic areas | `areas.py`, `stratify.py` | numbers, `tables/areas.tex` |
| Agreement with the adjudication | `validation_metrics.py` | numbers, `tables/validation.tex` |
| Merge the numbers for the documents | `write_numbers.py` | `numbers.tex`, the Findings above |
| Figures | `make_figure.py`, `make_figure_coverage.py`, `make_figure_hwang.py`, `make_figure_missrate.py` | `figures/*.pdf` |
| Check the documents: no hand-typed result, references in citation order, every stated order or test outcome borne out by the numbers | `check_documents.py` | pass or fail |

"numbers" means `numbers/<script>.json`. `paper_numbers.py` records them, `ctgov.py` is the registry client shared by the pull scripts, `repo_files.py` holds the file helpers, `figure_palette.py` the colours of the figures and `figure_style.py` their size, type and file format. In `paper/`, `manuscript.tex` and `supplement.tex` read every number as `\num{name}` from `numbers.tex` and every table body from `tables/`.

## Classification and validation

Termination reasons were classified by a large language model (Claude Sonnet, Anthropic) run as agents of the Claude Code assistant in July 2026, with the prompts in `prompts/`: `TAXONOMY.md`, `DETAIL_TASK.md` and `PUB_TASK.md`. The exact model version was not recorded. Every label is archived in `data/labels/` (`why_out/`, `detail_out/` and `pub_out/`), so the analysis does not depend on re-running the model.

The classification cannot be re-run from this repository as it stands: the input batches were assembled interactively and no script builds them, and the same is true of the validation sample and of the adjudication prompt.

The three prompts do not share one key set. `TAXONOMY.md` defines 12 categories. `DETAIL_TASK.md` adds `not_started`. `PUB_TASK.md` omits `other_operational`. A fourteenth label, `sponsor_undisclosed`, is assigned only by a rule in `reclassify.py`.

**Where the final label is.** Each stopped registration in `data/registry/ph3_stopped.json`, withdrawn ones included, has one final label: its value in `data/labels/unclear_reclassified_v2.json` if it is there (the registrations that went to the second pass), and otherwise its label in `data/labels/why_out/`. `load(include_withdrawn=True)` in `scripts/failure_decomp.py` returns exactly that as `stopcat`. The `batch_*.tsv` files have no header: registration number, tab, label; the JSON files map the registration number to the label. `efficacy_positive` is a stop for benefit, not a failure, and a completed trial that missed its primary endpoint has no label: its verdict comes from `data/registry/ph3_primary_analyses.json`. By pass: `why_out/` is the first pass; `detail_out/` holds the second-pass model labels, which the rules in `reclassify.py` can override, giving `unclear_reclassified.json`; `merge_pub_labels.py` then overlays `pub_out/`, giving the `_v2` file. No file records the pass that each final label came from. Limitation 8 of the manuscript and section S7 of the supplement list second-pass labels that the registry text does not support.

**To trace a number.** A number printed in the paper is `\num{name}` in the source; `paper/numbers.tex` has its value and `numbers/<script>.json` the script that recorded it. In a name such as `decomp.enrolled.era.big.eff.pct`, `enrolled` or `registered` says whether withdrawn registrations are counted, `era`, `complete` or `all` is the window (the main window, the part of it that has read out, all years), and `all`, `big` or `rest` the sponsors.

Validation is model-based and covers the first pass only; its files are in `data/validation/`. A sample of first-pass labels stratified by category (`gold_sample.tsv`, with the labels in `gold_truth.json`) was labelled again, blind, by a stronger model (Claude Opus; `gold_adjudicated.tsv`). Labels assigned by the second and third passes and by the rules were not adjudicated, and no human labels were collected.

## Limitations

The manuscript's Limitations section is the full list.

## Cite

Carstensen T. Structured-data reporting shapes the apparent causes of phase-3 trial failure: an automated decomposition of ClinicalTrials.gov records. Preprint, 2026 (not peer reviewed; DOI to follow on posting). Repository: <https://github.com/tommycarstensen/phase3-failure-decomposition>. See [`CITATION.cff`](CITATION.cff) for the structured form that GitHub reads.

## Contact

Tommy Carstensen, independent researcher. Correspondence: `metaarxiv@tommycarstensen.com`. ORCID [0000-0002-3672-9931](https://orcid.org/0000-0002-3672-9931).

## Licence

Code is under the MIT licence (`LICENSE`). The labels, numbers, tables, figures, manuscript text, this README, the prompts in `prompts/` and the finding wording in `paper/readme_findings.md` are under the Creative Commons Attribution 4.0 International licence (`LICENSE-CC-BY-4.0`). Neither licence applies to the registry records in `data/registry/` or to the `whyStopped` strings reproduced in `data/validation/gold_sample.tsv`: they are public data from ClinicalTrials.gov, redistributed under its terms of use, and the Creative Commons licence covers only this repository's own labels, numbers, tables, figures and text.
