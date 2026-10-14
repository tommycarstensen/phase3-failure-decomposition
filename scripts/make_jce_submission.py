"""Make the files to upload to the Journal of Clinical Epidemiology.

The journal takes the LaTeX source, not a PDF, and each figure as a separate
file. jce.tex as it stands is not self-contained: it reads the supplement's
labels from the build directory (xr) and draws the flow diagram from flow.tex.
This script writes a folder that the journal's system can compile on its own:

  manuscript.tex   jce.tex with every reference to the supplement replaced by
                   its number (S1, S2, ...) and the figures read from the
                   files below
  numbers.tex      the recorded numbers that manuscript.tex reads
  Figure_1.pdf     the flow diagram, drawn from flow.tex in Helvetica
  Figure_2.pdf ... the other figures of jce.tex, in their order
  highlights.txt   the highlights of jce.tex, one per line
  Supplementary_material.pdf   paper/jce_supplement.pdf
  manuscript.pdf   the folder compiled on its own, to look at before upload

It builds the JCE pair first (build_pdf.sh jce), then compiles the folder in a
temporary copy and stops if a reference is undefined or a warning is printed.
It is a packaging step, not part of reproduce.sh.

Run from anywhere: python3 scripts/make_jce_submission.py [output folder]
The default folder is paper/build/jce_submission.
"""

import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from repo_files import PAPER, D

# 11pt, as in jce.tex, so the diagram has the same size of type in both
FLOW_DOCUMENT = r"""\documentclass[11pt,border=2pt]{standalone}
\usepackage{tikz}
\usetikzlibrary{positioning}
\input{numbers}
\newcommand{\era}{\num{era.first}--\num{era.last}}
\begin{document}
\fontfamily{phv}\selectfont
\input{flow}
\end{document}
"""
WARNING = re.compile(
    r'LaTeX Warning|Package \w+ Warning|Overfull|Underfull|undefined'
)


def run(command, cwd):
    """Run a command, and stop with its last lines if it fails."""
    done = subprocess.run(
        command, cwd=cwd, capture_output=True, text=True, check=False
    )
    if done.returncode != 0:
        print('\n'.join((done.stdout + done.stderr).splitlines()[-20:]))
        sys.exit(f'failed: {" ".join(command)}')


def latex(name, cwd, rounds=2):
    """Compile name.tex in cwd; return its log."""
    for _ in range(rounds):
        run(['pdflatex', '-interaction=nonstopmode', name + '.tex'], cwd)
    return (Path(cwd) / (name + '.log')).read_text(errors='replace')


def supplement_labels():
    """{label: number} from the supplement's auxiliary file."""
    aux = (Path(D) / PAPER / 'build' / 'jce_supplement.aux').read_text()
    return dict(re.findall(r'\\newlabel\{([^}]*)\}\{\{([^}]*)\}', aux))


def manuscript(source, labels):
    """jce.tex made self-contained; also the figure files it now reads."""
    text = source.replace('\\usepackage{xr}\n', '')
    text = text.replace('\\externaldocument{jce_supplement}\n', '')
    own = set(re.findall(r'\\label\{([^}]*)\}', text))

    def resolve(m):
        key = m.group(1)
        if key in own:
            return m.group(0)
        if key not in labels:
            sys.exit(f'no number for the supplement label {key}')
        # in braces, so that \S{S3} does not become the command \SS
        return '{' + labels[key] + '}'

    text = re.sub(r'\\ref\{([^}]*)\}', resolve, text)
    flow = re.search(
        r'\{\\fontfamily\{phv\}\\selectfont'
        r'\\resizebox\{\\linewidth\}\{!\}\{\\input\{flow\}\}\}',
        text,
    )
    if not flow:
        sys.exit(
            'the flow diagram of jce.tex is not where this script expects'
        )
    text = text.replace(
        flow.group(0), '\\includegraphics[width=\\linewidth]{Figure_1}'
    )
    figures = []
    for path in re.findall(r'\\includegraphics\[[^\]]*\]\{([^}]*)\}', text):
        if path == 'Figure_1':
            continue
        name = f'Figure_{len(figures) + 2}'
        figures.append((path, name))
        text = text.replace('{' + path + '}', '{' + name + '}', 1)
    return text, figures


def highlights(source):
    """The highlights of jce.tex, one string each."""
    start = source.index('\\begin{highlights}')
    end = source.index('\\end{highlights}')
    return [x.strip() for x in re.findall(r'\\item (.*)', source[start:end])]


def main():
    out = Path(sys.argv[1] if len(sys.argv) > 1 else D + PAPER).resolve()
    if len(sys.argv) == 1:
        out = out / 'build' / 'jce_submission'
    print(f'making the JCE submission files in {out}')
    run(['bash', 'build_pdf.sh', 'jce'], D)
    paper = Path(D) / PAPER
    source = (paper / 'jce.tex').read_text()
    text, figures = manuscript(source, supplement_labels())
    items = highlights(source)
    too_long = [h for h in items if len(h) > 85]
    if too_long:
        sys.exit(f'highlights over 85 characters: {too_long}')

    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        shutil.copy(paper / 'numbers.tex', work)
        shutil.copy(paper / 'flow.tex', work)
        (work / 'Figure_1.tex').write_text(FLOW_DOCUMENT)
        log = latex('Figure_1', work, rounds=1)
        if WARNING.search(log):
            sys.exit('Figure_1.tex: the log has a warning')
        for path, name in figures:
            shutil.copy(paper / path, work / (name + '.pdf'))
        (work / 'manuscript.tex').write_text(text)
        log = latex('manuscript', work)
        found = sorted(set(WARNING.findall(log)))
        if found:
            sys.exit(f'manuscript.tex compiled on its own warns: {found}')

        out.mkdir(parents=True, exist_ok=True)
        for old in out.iterdir():
            if old.is_file():
                old.unlink()
        files = ['manuscript.tex', 'numbers.tex', 'manuscript.pdf']
        files += [f'Figure_{k}.pdf' for k in range(1, len(figures) + 2)]
        for name in files:
            shutil.copy(work / name, out)
    shutil.copy(
        paper / 'jce_supplement.pdf', out / 'Supplementary_material.pdf'
    )
    (out / 'highlights.txt').write_text('\n'.join(items) + '\n')
    print(f'  {len(figures) + 1} figures, {len(items)} highlights')
    print(f'  manuscript.tex compiles on its own without a warning: {out}')


if __name__ == '__main__':
    main()
