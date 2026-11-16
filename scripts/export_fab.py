#!/usr/bin/env python3
"""One-click fabrication export: Gerbers + drill + PDF preview + 3D render.

Usage:  python3 export_fab.py <board.kicad_pcb> <out_dir> [kicad-cli-path]

Produces the full fab package:
  gerbers  -> top/bottom Cu, Silks, Mask, Fab, Edge.Cuts   (.gtl/.gbl/...)
  drill    -> Excellon .drl + report
  pdf      -> layered assembly previews
  3D       -> top/bottom/iso PNG renders (for docs & articles)
"""
import subprocess
import sys
from pathlib import Path

DEFAULT_CLI = r"D:/Program Files/KiCad/10.99/bin/kicad-cli.exe"

GERBER_LAYERS = ('F.Cu,B.Cu,F.SilkS,B.SilkS,F.Mask,B.Mask,'
                 'Edge.Cuts,F.Fab,B.Fab')


def sh(cli, *args):
    r = subprocess.run([cli, *args], capture_output=True, text=True)
    ok = r.returncode == 0
    print(('OK  ' if ok else 'FAIL') + '  ' + ' '.join(args[:3]) + ' ...')
    if not ok:
        print(r.stdout[-500:] or r.stderr[-500:])
    return ok


def run(board: Path, out: Path, cli: str):
    out.mkdir(parents=True, exist_ok=True)
    ok = True
    # NOTE (battle scar): the gerbers flag is -o / --output, NOT --output-dir.
    ok &= sh(cli, 'pcb', 'export', 'gerbers',
             '-o', str(out), '-l', GERBER_LAYERS, str(board))
    # Drill takes a directory (trailing slash on Windows matters in some builds)
    ok &= sh(cli, 'pcb', 'export', 'drill',
             '-o', str(out) + '/', str(board))
    ok &= sh(cli, 'pcb', 'export', 'pdf',
             '-o', str(out.parent / f'{board.stem}-assembly.pdf'),
             '--layers', 'F.Cu,B.Cu,F.SilkS,B.SilkS,Edge.Cuts', str(board))
    # 3D renders (slow, ~1 min each at high quality)
    for tag, extra in [('3d-top', ['--side', 'top']),
                       ('3d-bottom', ['--side', 'bottom']),
                       ('3d-iso', ['--side', 'front', '--rotate', '-30,0,35'])]:
        ok &= sh(cli, 'pcb', 'render',
                 '-o', str(out.parent / f'{tag}.png'),
                 '--quality', 'high', '--width', '1600', '--height', '1000',
                 '--floor', *extra, str(board))
    files = sorted(p.name for p in out.iterdir())
    print(f'\nFab package in {out}: {len(files)} files')
    for f in files:
        print('  ' + f)
    return 0 if ok else 1


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    cli = sys.argv[3] if len(sys.argv) > 3 else DEFAULT_CLI
    sys.exit(run(Path(sys.argv[1]), Path(sys.argv[2]), cli))
