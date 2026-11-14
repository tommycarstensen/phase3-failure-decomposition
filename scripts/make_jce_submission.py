"""Make the files to upload to the journal, now Therapeutic Innovation &
Regulatory Science (Springer).

jce.tex keeps the name of the first journal it was cut for. As it stands it is
not self-contained: it reads the supplement's labels from the build directory
(xr) and draws the flow diagram from flow.tex. This script writes a folder that
can be compiled on its own, laid out as the journal's Instructions for Authors
(revised October 2020, read 2026-11-13) ask: double-spaced with a wide margin;
a title page with the authors, the corresponding author's postal and email
address, the running head and the keywords; then the abstract on a page of
its own, the text, the references, the figure legends, and the tables on
separate pages at the end, the figures being uploaded as files. The text is
also ranged left without hyphenation, as the journal before this one asked and
this one allows.

Every file starts with the journal's short name, JOURNAL, so that it says
where it is going wherever it is opened or uploaded:

  tirs_manuscript.tex   jce.tex in that layout, with every reference to the
                        supplement replaced by its number (S1, S2, ...)
  tirs_numbers.tex      the recorded numbers that the manuscript reads
  tirs_figure_1.pdf     the flow diagram, drawn from flow.tex in Helvetica
  tirs_figure_2.pdf ... the other figures of jce.tex, in their order
  tirs_supplement.pdf   paper/jce_supplement.pdf
  tirs_strobe_checklist.pdf   its last section, the reporting checklist,
                        which the journal asks for as a supplementary file
  tirs_manuscript.pdf   the folder compiled on its own, to look at before
                        upload
  tirs_abstract.txt     the abstract as plain text, to paste into the form

It overwrites its own files and removes old figure files, and leaves anything
else in the folder alone, such as a cover letter.

It builds the journal pair first (build_pdf.sh jce), then compiles the folder
in a temporary copy and stops if a reference is undefined or a warning is
printed. It is a packaging step, not part of reproduce.sh.

The postal address is an argument and never a line of a tracked file, because
this repository is public. Without it the title page has no such line. The
journal asks for no telephone number.

Run from anywhere:
python3 scripts/make_jce_submission.py [output folder] [address]
The default folder is paper/build/tirs_submission.
"""

import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from check_documents import jce_abstract_words, jce_words
from paper_numbers import read_numbers
from repo_files import PAPER, D

# the journal's short name, which starts the name of every file written
JOURNAL = 'tirs'
# "the shortened manuscript title followed by an ellipsis" (the guide)
RUNNING_HEAD = (
    'How ClinicalTrials.gov is read changes the apparent causes\\ldots'
)
# 11pt, as in jce.tex, so the diagram has the same size of type in both
FLOW_DOCUMENT = r"""\documentclass[11pt,border=2pt]{standalone}
\usepackage{tikz}
\usetikzlibrary{positioning}
\input{%s}
\newcommand{\era}{\num{era.first}--\num{era.last}}
\begin{document}
\fontfamily{phv}\selectfont
\input{flow}
\end{document}
"""
WARNING = re.compile(
    r'LaTeX Warning|Package \w+ Warning|Overfull|Underfull|undefined'
)
# double-spaced, ranged left, hyphenation cancelled. Loaded last, after the
# packages whose commands ragged2e changes, and with the right margin free to
# be as ragged as the words need, since none may be hyphenated
LAYOUT_PREAMBLE = r"""\usepackage{setspace}
\doublespacing
\usepackage{ragged2e}
\setlength{\RaggedRightRightskip}{0pt plus 1fil}
\AtBeginDocument{\RaggedRight}
\hyphenpenalty=10000
\exhyphenpenalty=10000
"""
STROBE_DOCUMENT = r"""\documentclass[a4paper]{article}
\usepackage{pdfpages}
\begin{document}
\includepdf[pages={%s-}]{supplement}
\end{document}
"""


def run(command, cwd):
    """Run a command, and stop with its last lines if it fails."""
    # pdflatex prints bytes of an included PDF that are not UTF-8
    done = subprocess.run(
        command,
        cwd=cwd,
        capture_output=True,
        text=True,
        errors='replace',
        check=False,
    )
    if done.returncode != 0:
        print('\n'.join((done.stdout + done.stderr).splitlines()[-20:]))
        sys.exit(f'failed: {" ".join(command)}')


def latex(name, cwd, rounds=2):
    """Compile name.tex in cwd; return its log."""
    for _ in range(rounds):
        run(['pdflatex', '-interaction=nonstopmode', name + '.tex'], cwd)
    return (Path(cwd) / (name + '.log')).read_text(errors='replace')


def named(stem):
    """The name of a file for the journal, without its extension."""
    return f'{JOURNAL}_{stem}'


def supplement_aux():
    return (Path(D) / PAPER / 'build' / 'jce_supplement.aux').read_text()


def supplement_labels():
    """{label: number} from the supplement's auxiliary file."""
    aux = supplement_aux()
    return dict(re.findall(r'\\newlabel\{([^}]*)\}\{\{([^}]*)\}', aux))


def strobe_page():
    """The page on which the supplement's STROBE checklist starts. It must be
    the last section, because the checklist file runs to the last page."""
    source = (Path(D) / PAPER / 'jce_supplement.tex').read_text()
    sections = re.findall(r'\\section\{.*\\label\{([^}]*)\}', source)
    if not sections or sections[-1] != 'supp:strobe':
        sys.exit('the STROBE checklist is not the last supplement section')
    found = re.search(
        r'\\newlabel\{supp:strobe\}\{\{[^}]*\}\{(\d+)\}', supplement_aux()
    )
    if not found:
        sys.exit('no page for the STROBE checklist in jce_supplement.aux')
    return found.group(1)


def title_page(address, keywords):
    """The lines the journal asks for on the title page, as LaTeX, with the
    word count as the journal counts it."""
    words = jce_abstract_words() + jce_words()
    lines = [
        f'\\textbf{{Running head:}} {RUNNING_HEAD}',
        f'\\textbf{{Keywords:}} {keywords}',
        (
            f'\\textbf{{Word count:}} {words:,}, abstract and text, without '
            'references, figures, tables and declarations'
        ),
    ]
    if address:
        lines.append(f'\\textbf{{Postal address:}} {address}')
    return '\\noindent ' + '\\\\\n'.join(lines) + '\n'


def environment(text, name):
    """The first \\begin{name} ... \\end{name} of text, or None."""
    start = text.find(f'\\begin{{{name}}}')
    if start < 0:
        return None
    end = text.index(f'\\end{{{name}}}', start) + len(f'\\end{{{name}}}')
    return text[start:end]


def braced(text, opening):
    """What stands inside the balanced braces that open at index `opening`."""
    depth = 0
    for i in range(opening, len(text)):
        if text[i] == '{' and text[i - 1] != '\\':
            depth += 1
        elif text[i] == '}' and text[i - 1] != '\\':
            depth -= 1
            if depth == 0:
                inside = opening + 1
                return text[inside:i]
    sys.exit('unbalanced braces in jce.tex')


def legend(figure):
    """A figure environment as its legend, a ragged paragraph in the text
    font that steps the figure counter and keeps the label, so references to
    the figure still resolve. A caption would be set justified."""
    caption = braced(figure, figure.index('\\caption{') + len('\\caption'))
    label = re.search(r'\\label\{[^}]*\}', figure)
    tail = label.group(0) if label else ''
    return (
        f'\\noindent\\refstepcounter{{figure}}{tail}'
        f'\\textbf{{Figure~\\thefigure.}} {caption}\n\n'
    )


def journal_layout(text, address):
    """jce.tex laid out as the journal asks; see the module docstring."""
    text = text.replace(
        '\\begin{document}\n', LAYOUT_PREAMBLE + '\n\\begin{document}\n', 1
    )
    text = text.replace(
        'colorlinks=true,linkcolor=blue,citecolor=blue,urlcolor=blue',
        'hidelinks',
        1,
    )
    text = text.replace(
        '\\newcommand{\\code}[1]{\\texttt{\\small #1}}',
        '\\newcommand{\\code}[1]{\\textit{#1}}',
        1,
    )
    abstract = environment(text, 'abstract')
    keywords = environment(text, 'keyword')
    if abstract is None or keywords is None:
        sys.exit('jce.tex has no abstract or no keywords')
    text = text.replace(abstract, '', 1).replace(keywords, '', 1)
    body = abstract.removeprefix('\\begin{abstract}')
    body = body.removesuffix('\\end{abstract}').strip()
    words = keywords.removeprefix('\\begin{keyword}')
    words = words.removesuffix('\\end{keyword}')
    words = '; '.join(w.strip() for w in words.split('\\sep'))
    abstract_page = '\\newpage\n\\section*{Abstract}\n' + body + '\n'
    text = text.replace(
        '\\end{frontmatter}\n',
        '\\end{frontmatter}\n\n'
        + title_page(address, words)
        + '\n'
        + abstract_page,
        1,
    )
    tables, legends = [], []
    while (table := environment(text, 'table')) is not None:
        # a minipage sets its notes justified again
        minipage = r'(\\begin\{minipage\}\{[^}]*\})'
        tables.append(re.sub(minipage, r'\1\\RaggedRight', table))
        text = text.replace(table, '', 1)
    while (figure := environment(text, 'figure')) is not None:
        legends.append(legend(figure))
        text = text.replace(figure, '', 1)
    end = (
        '\\clearpage\n\\section*{Figure legends}\n'
        + ''.join(legends)
        + ''.join(f'\\clearpage\n{t}\n' for t in tables)
        + '\\end{document}'
    )
    return text.replace('\\end{document}', end, 1)


def plain_abstract(source):
    """The abstract of jce.tex as plain text for the submission form: one
    paragraph per heading, the numbers as recorded, a hyphen kept as a hyphen
    and only a minus in math written as a minus sign."""
    begin, end = '\\begin{abstract}', '\\end{abstract}'
    start = source.index(begin) + len(begin)
    stop = source.index(end)
    body = source[start:stop]
    numbers = read_numbers()
    body = body.replace('\\era', '\\num{era.first}--\\num{era.last}')
    body = re.sub(
        r'\\num\{([^}]*)\}',
        lambda m: re.sub(r'^-', '\u2212', numbers[m.group(1)]['txt']),
        body,
    )
    body = re.sub(
        r'\$([^$]*)\$',
        lambda m: m.group(1).replace('-', '\u2212').replace('=', ' = '),
        body,
    )
    body = re.sub(r'\\textbf\{([^}]*)\}', r'\1', body)
    body = body.replace('\\noindent', '').replace('\\%', '%')
    body = body.replace('\\ ', ' ').replace('--', '\u2013')
    paragraphs = [' '.join(p.split()) for p in re.split(r'\n\s*\n', body)]
    text = '\n\n'.join(p for p in paragraphs if p) + '\n'
    left = sorted(set(re.findall(r'[\\{}$~]', text)))
    if left:
        sys.exit(f'the plain abstract still has LaTeX in it: {left}')
    return text


def manuscript(source, labels, address):
    """jce.tex made self-contained and laid out for the journal; also the
    figure files, in their order."""
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
    if '\\input{numbers}' not in text:
        sys.exit('jce.tex does not read numbers.tex where this script expects')
    text = text.replace('\\input{numbers}', f'\\input{{{named("numbers")}}}')
    flow = re.search(
        r'\{\\fontfamily\{phv\}\\selectfont'
        r'\\resizebox\{\\linewidth\}\{!\}\{\\input\{flow\}\}\}',
        text,
    )
    if not flow:
        sys.exit(
            'the flow diagram of jce.tex is not where this script expects'
        )
    first = named('figure_1')
    text = text.replace(
        flow.group(0), f'\\includegraphics[width=\\linewidth]{{{first}}}'
    )
    figures = []
    for path in re.findall(r'\\includegraphics\[[^\]]*\]\{([^}]*)\}', text):
        if path == first:
            continue
        name = named(f'figure_{len(figures) + 2}')
        figures.append((path, name))
        text = text.replace('{' + path + '}', '{' + name + '}', 1)
    return journal_layout(text, address), figures


def main():
    out = Path(sys.argv[1] if len(sys.argv) > 1 else D + PAPER).resolve()
    if len(sys.argv) == 1:
        out = out / 'build' / named('submission')
    address = sys.argv[2] if len(sys.argv) > 2 else ''
    print(f'making the journal submission files in {out}')
    if not address:
        print('  no postal address given: the title page has no such line')
    run(['bash', 'build_pdf.sh', 'jce'], D)
    paper = Path(D) / PAPER
    source = (paper / 'jce.tex').read_text()
    labels = supplement_labels()
    text, figures = manuscript(source, labels, address)

    numbers, first = named('numbers'), named('figure_1')
    article, strobe = named('manuscript'), named('strobe_checklist')
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        shutil.copy(paper / 'numbers.tex', work / f'{numbers}.tex')
        shutil.copy(paper / 'flow.tex', work)
        (work / f'{first}.tex').write_text(FLOW_DOCUMENT % numbers)
        log = latex(first, work, rounds=1)
        if WARNING.search(log):
            sys.exit(f'{first}.tex: the log has a warning')
        for path, name in figures:
            shutil.copy(paper / path, work / (name + '.pdf'))
        (work / f'{article}.tex').write_text(text)
        log = latex(article, work, rounds=3)
        found = sorted(set(WARNING.findall(log)))
        if found:
            lines = log.splitlines()
            for i, line in enumerate(lines):
                if WARNING.search(line):
                    context = lines[i:][:3]
                    print('\n'.join(context))
            sys.exit(f'{article}.tex compiled on its own warns: {found}')
        shutil.copy(paper / 'jce_supplement.pdf', work / 'supplement.pdf')
        (work / f'{strobe}.tex').write_text(STROBE_DOCUMENT % strobe_page())
        latex(strobe, work, rounds=1)

        out.mkdir(parents=True, exist_ok=True)
        for old in out.glob(named('figure_*.pdf')):
            old.unlink()
        files = [f'{article}.tex', f'{numbers}.tex', f'{article}.pdf']
        files.append(f'{strobe}.pdf')
        files += [f'{first}.pdf'] + [f'{name}.pdf' for _, name in figures]
        for name in files:
            shutil.copy(work / name, out)
    shutil.copy(
        paper / 'jce_supplement.pdf', out / f'{named("supplement")}.pdf'
    )
    abstract = plain_abstract(source)
    plain = named('abstract') + '.txt'
    (out / plain).write_text(abstract, encoding='utf-8')
    print(f'  {plain}: {len(abstract.split())} words')
    print(
        f'  {len(figures) + 1} figures, {jce_abstract_words()} words of '
        f'abstract and {jce_words()} of main text'
    )
    print(f'  {article}.tex compiles on its own without a warning: {out}')


if __name__ == '__main__':
    main()
