#!/usr/bin/env bash
# Regenerate every number, table and figure from the archived labels and registry retrievals, check the documents against them, and check that what was regenerated is identical to the committed copy.
# Runs from any directory: bash reproduce.sh
# Uses python3 unless PYTHON names another interpreter: PYTHON=python3.14 bash reproduce.sh
set -euo pipefail
cd "$(dirname "$0")"
PY="${PYTHON:-python3}"

# labels: the second-pass rules, then the third-pass overrides
"$PY" scripts/reclassify.py            # -> data/labels/unclear_reclassified.json
"$PY" scripts/merge_pub_labels.py      # -> data/labels/unclear_reclassified_v2.json

# analysis: each script records its numbers in numbers/<script>.json
"$PY" scripts/cohort.py
"$PY" scripts/literature.py
"$PY" scripts/recoverability.py
"$PY" scripts/decomposition.py
"$PY" scripts/coverage.py
"$PY" scripts/sensitivity.py           # also paper/tables/taxonomy.tex
"$PY" scripts/inference.py             # also paper/tables/yearly.tex, covmodel.tex
"$PY" scripts/endpoint_design.py
"$PY" scripts/dedup_arms.py            # also paper/tables/subjects.tex
"$PY" scripts/novelty_flag.py          # also paper/tables/novelty.tex
"$PY" scripts/stratify.py              # also paper/tables/areas.tex
"$PY" scripts/validation_metrics.py    # also paper/tables/validation.tex

# documents: paper/numbers.tex and the README findings, the figures, then the checks
"$PY" scripts/write_numbers.py
"$PY" scripts/make_figure.py           # -> paper/figures/ph3_failure_2016_vs_2026.pdf
"$PY" scripts/make_figure_hwang.py     # -> paper/figures/ph3_bigpharma_vs_hwang.pdf
"$PY" scripts/make_figure_missrate.py  # -> paper/figures/ph3_miss_rate_by_year.pdf
"$PY" scripts/make_figure_coverage.py  # -> paper/figures/ph3_coverage_correction.pdf
"$PY" scripts/check_documents.py

echo "--- regenerated against committed ---"
if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "  not a git checkout, so there is no committed copy to compare with; skipped"
  exit 0
fi
changed="$(git status --porcelain -- numbers paper/tables paper/numbers.tex README.md data/labels/unclear_reclassified.json data/labels/unclear_reclassified_v2.json)"
if [ -n "$changed" ]; then
  echo "$changed"
  echo "the regenerated numbers, tables or labels differ from the committed ones"
  exit 1
fi
echo "  numbers, tables, labels and README findings are identical to the committed copy"
figures="$(git status --porcelain -- paper/figures)"
if [ -n "$figures" ]; then
  echo "$figures"
  echo "  the figures were redrawn from the numbers checked above, but their bytes differ from the committed files; this happens with another platform or matplotlib version"
  exit 0
fi
echo "  figures are identical to the committed copy"
echo "all committed outputs reproduce"
