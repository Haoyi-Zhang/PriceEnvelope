#!/usr/bin/env python3
"""Compile with the separately supplied SIAM macro ZIP, without redistributing it."""
from pathlib import Path
import argparse
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile

from audit_references import audit as audit_references

DEPENDENCIES = ('siamart251216.cls', 'siamplain.bst')
# Current checked layout baseline, not an official SICOMP page limit.
EXPECTED_PAGES = 41

def sync_companion_article(source_pdf: Path, artifact: Path) -> None:
    """Refresh the standalone article and its consumed integrity entry together."""
    target = artifact / 'proofs' / 'theory.pdf'
    manifest = artifact / 'RELEASE-MANIFEST.sha256'
    lines = manifest.read_text(encoding='utf-8').splitlines(keepends=True)
    matching = [i for i, line in enumerate(lines)
                if line.rstrip().endswith('  proofs/theory.pdf')]
    if len(matching) != 1:
        raise ValueError('Expected one standalone article entry in the release manifest.')
    data = source_pdf.read_bytes()
    lines[matching[0]] = hashlib.sha256(data).hexdigest() + '  proofs/theory.pdf\n'
    pending = target.with_name('.' + target.name + '.building')
    try:
        pending.write_bytes(data)
        pending.replace(target)
        manifest.write_text(''.join(lines), encoding='utf-8')
    finally:
        pending.unlink(missing_ok=True)

def stage_sources(source: Path, work: Path) -> None:
    """Copy the manuscript and its local include dependencies, not publisher macros."""
    for item in ('main.tex', 'references.bib', 'current-authors.tex',
                 'project-repository.tex'):
        shutil.copyfile(source/item, work/item)
    for directory in ('sections', 'figures'):
        shutil.copytree(source/directory, work/directory)

def capture(command: list[str], directory: Path, environment: dict[str, str],
            timeout: int = 120) -> subprocess.CompletedProcess:
    # Native tools may print localized diagnostics in the system code page.
    # Preserve ASCII status/page fields without allowing decoding to hide a return code.
    return subprocess.run(command, cwd=directory, env=environment,
                          text=True, encoding='utf-8', errors='replace',
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                          timeout=timeout)

def run(command: list[str], directory: Path, environment: dict[str, str]) -> None:
    completed = capture(command, directory, environment)
    if completed.returncode:
        raise RuntimeError(f"Command failed: {command[0]}\n{completed.stdout[-12000:]}")

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--template', required=True, type=Path,
                        help='Original matched TEMPLATE.zip supplied with this project')
    parser.add_argument('--output', type=Path, default=Path(__file__).resolve().parent/'main.pdf')
    args = parser.parse_args()
    pdflatex = shutil.which('pdflatex')
    # Some installations retain the usable executable under this alternate name.
    bibtex = shutil.which('bibtex') or shutil.which('bibtex.original')
    pdfinfo = shutil.which('pdfinfo')
    if not pdflatex or not bibtex or not pdfinfo:
        raise RuntimeError('Working pdflatex, BibTeX, and pdfinfo installations are required.')
    source = Path(__file__).resolve().parent
    reference_report = audit_references(source.parent)
    with tempfile.TemporaryDirectory(prefix='correlated-safety-') as scratch:
        work = Path(scratch)
        stage_sources(source, work)
        # Read only the two explicitly required members; never extract an archive tree.
        with zipfile.ZipFile(args.template) as archive:
            for name in DEPENDENCIES:
                matches = [entry for entry in archive.infolist()
                           if Path(entry.filename).name == name and not entry.is_dir()]
                if len(matches) != 1 or matches[0].file_size > 1024*1024:
                    raise ValueError(f'Expected one bounded member named {name}')
                (work/name).write_bytes(archive.read(matches[0]))
        environment = os.environ.copy()
        # Current directory first avoids an upstream example named main.tex shadowing ours.
        environment['TEXINPUTS'] = '.' + os.pathsep
        environment['BSTINPUTS'] = '.' + os.pathsep
        environment['OMP_NUM_THREADS'] = '1'
        latex = [pdflatex, '-no-shell-escape', '-interaction=nonstopmode',
                 '-halt-on-error', './main.tex']
        run(latex, work, environment)
        run([bibtex, 'main'], work, environment)
        run(latex, work, environment)
        run(latex, work, environment)
        log = (work/'main.log').read_text(errors='replace')
        if 'Overfull \\hbox' in log or 'Overfull \\vbox' in log:
            raise RuntimeError('Overfull boxes remain; inspect the typesetting before delivery.')
        if 'There were undefined references' in log or 'There were undefined citations' in log:
            raise RuntimeError('Unresolved references remain.')
        info = capture([pdfinfo, str(work/'main.pdf')], work, environment, timeout=30)
        if info.returncode:
            raise RuntimeError(f'pdfinfo failed:\n{info.stdout}')
        page_line = next((line for line in info.stdout.splitlines() if line.startswith('Pages:')), None)
        if page_line is None or int(page_line.split(':', 1)[1]) != EXPECTED_PAGES:
            raise RuntimeError(f'Expected exactly {EXPECTED_PAGES} pages; got {page_line!r}.')
        args.output.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(work/'main.pdf', args.output)
        if args.output.resolve() == (source/'main.pdf').resolve():
            sync_companion_article(args.output, source.parent/'artifact')
    print(f'Compiled PDF: {args.output}')
    print(f'Reference audit: {reference_report["reference_count"]} cited scholarly entries')

if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired,
            zipfile.BadZipFile) as exc:
        print(f'BUILD FAILED: {exc}', file=sys.stderr)
        sys.exit(1)
