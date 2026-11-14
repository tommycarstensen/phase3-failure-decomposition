#!/usr/bin/env bash
# Build a manuscript and its supplement as PDFs in paper/. Runs from any directory.
#   bash build_pdf.sh       the preprint: paper/manuscript.pdf and paper/supplement.pdf
#   bash build_pdf.sh jce   the journal version, which keeps the name of the first journal it was cut for: paper/jce.pdf and paper/jce_supplement.pdf
# Both are LaTeX and read their numbers from paper/numbers.tex and their table bodies from paper/tables/, which reproduce.sh writes.
# Each document refers to the other by label (the manuscript to the supplementary tables, the supplement to the sections and limitations of the main text), so the two are built in rounds until neither log asks for another run and neither .aux file changed in the last round; a clean checkout needs two or three. The second test is needed because some packages print from the .aux without asking for a rerun: elsarticle's \ead does, so a changed email address reached jce.pdf only one build late.
# The auxiliary files go to paper/build/, where pdflatex also looks for the other document's labels; only the two PDFs land beside the sources.
set -euo pipefail
case "${1:-preprint}" in
  preprint) main=manuscript supp=supplement ;;
  jce) main=jce supp=jce_supplement ;;
  *) echo "usage: bash build_pdf.sh [jce]"; exit 1 ;;
esac
cd "$(dirname "$0")/paper"
mkdir -p build

settled=no
aux_before=$(cat "build/$main.aux" "build/$supp.aux" 2>/dev/null | shasum || true)
for round in 1 2 3 4 5 6; do
  for doc in "$supp" "$main"; do
    pdflatex -interaction=nonstopmode -halt-on-error -output-directory=build "$doc.tex" >/dev/null || { tail -20 "build/$doc.log"; exit 1; }
  done
  aux_after=$(cat "build/$main.aux" "build/$supp.aux" | shasum)
  # natbib, which elsarticle loads for jce.tex, reports its own undefined or changed citations
  if [ "$aux_after" = "$aux_before" ] && ! grep -q "Rerun to get cross-references right\|There were undefined references\|There were undefined citations\|Citation(s) may have changed" "build/$main.log" "build/$supp.log"; then
    settled=yes
    break
  fi
  aux_before=$aux_after
done
if [ "$settled" != yes ]; then
  echo "the cross-references did not settle in $round rounds:"
  grep -h "Rerun to get cross-references right\|undefined\|may have changed" "build/$main.log" "build/$supp.log" | sort | uniq -c
  exit 1
fi
mv "build/$main.pdf" "build/$supp.pdf" .
echo "wrote paper/$main.pdf and paper/$supp.pdf (settled in round $round)"
