#!/usr/bin/env python3
"""Run kicad-cli DRC on a board and print a violation-type summary.

Usage:  python3 drc_summary.py <board.kicad_pcb> [kicad-cli-path]

NOTE (battle scar): do NOT use `--output -`; on some KiCad 10.99 builds the
dash output path makes DRC fail with "board load failed". Run plain DRC —
it writes <board-stem>-drc.rpt next to the board — then summarize.
"""
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

DEFAULT_CLI = r"D:/Program Files/KiCad/10.99/bin/kicad-cli.exe"

# Violations that block fabrication
FATAL = {'shorting_items', 'unconnected_items'}
# Cosmetic / non-blocking (typical for hobby THT boards)
COSMETIC = {'silk_overlap', 'silk_over_copper', 'courtyards_overlap',
            'pth_inside_courtyard', 'holes_co_located', 'solder_mask_bridge'}


def run(board: Path, cli: str = DEFAULT_CLI):
    subprocess.run([cli, 'pcb', 'drc', '--severity-all', str(board)],
                   capture_output=True, text=True)
    rpt = board.with_name(board.stem + '-drc.rpt')
    if not rpt.exists():
        print('ERROR: DRC report not generated:', rpt)
        return 1
    text = rpt.read_text(encoding='utf-8')
    types = Counter(re.findall(r'\[([a-z_]+)\]', text))
    total = sum(types.values())

    fatal = {t: n for t, n in types.items() if t in FATAL}
    cosmetic = {t: n for t, n in types.items() if t in COSMETIC}
    other = {t: n for t, n in types.items()
             if t not in FATAL and t not in COSMETIC}

    print(f'DRC: {total} violations total')
    print('\n== FATAL (must be 0 before fabrication) ==')
    for t in sorted(fatal):
        print(f'  {t}: {fatal[t]}')
    if not fatal:
        print('  (none) OK')
    print('\n== Cosmetic (acceptable for prototyping) ==')
    for t in sorted(cosmetic):
        print(f'  {t}: {cosmetic[t]}')
    print('\n== Other (review: clearance/copper_edge may matter) ==')
    for t in sorted(other):
        print(f'  {t}: {other[t]}')

    # Print fatal item locations for targeted fixes
    for t in FATAL:
        for m in re.findall(rf'\[{t}\][^\[]*', text):
            lines = m.strip().split('\n')
            print('\n' + lines[0])
            for ln in lines[1:3]:
                print('  ' + ln)

    return 0 if not fatal else 2


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    cli = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_CLI
    sys.exit(run(Path(sys.argv[1]), cli))
