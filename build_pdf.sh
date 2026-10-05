#!/usr/bin/env bash
# Build the manuscript and supplement PDFs in paper/. Runs from any directory: bash build_pdf.sh
# Both are LaTeX and read their numbers from paper/numbers.tex and their table bodies from paper/tables/, which reproduce.sh writes.
# Each document refers to the other by label (the manuscript to the supplementary tables, the supplement to the sections and limitations of the main text), so the two are built in rounds until neither log asks for another run; a clean checkout needs three.
# The auxiliary files go to paper/build/, where pdflatex also looks for the other document's labels; only the two PDFs land beside the sources.
set -euo pipefail
cd "$(dirname "$0")/paper"
mkdir -p build

settled=no
for round in 1 2 3 4 5; do
  for doc in supplement manuscript; do
    pdflatex -interaction=nonstopmode -halt-on-error -output-directory=build "$doc.tex" >/dev/null || { tail -20 "build/$doc.log"; exit 1; }
  done
  if ! grep -q "Rerun to get cross-references right\|There were undefined references" build/manuscript.log build/supplement.log; then
    settled=yes
    break
  fi
done
if [ "$settled" != yes ]; then
  echo "the cross-references did not settle in $round rounds:"
  grep -h "Rerun to get cross-references right\|undefined" build/manuscript.log build/supplement.log | sort | uniq -c
  exit 1
fi
mv build/manuscript.pdf build/supplement.pdf .
echo "wrote paper/manuscript.pdf and paper/supplement.pdf (settled after $round rounds)"
