#!/usr/bin/env python3
"""PCB generator template — write .kicad_pcb as text (layout + optional tracks).

Adapted from a battle-tested NE555+CD4017 board (0 shorts / 0 unconnected).
Pipeline: layout table → footprint embedding (net-injected pads) → edge →
tracks. Keep the layout-only variant as your pristine reset point.
"""
import os
import re
import sys
import uuid

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))
from pcb_tools import emit_segment, emit_via, pad_pos, uid  # noqa: E402

KICAD_FP = "D:/Program Files/KiCad/10.99/share/kicad/footprints"

# ── 1. Net table: name → id (MUST match the schematic netlist) ──
NETS = {'+5V': 1, 'GND': 2}  # ...

# ── 2. Layout: ref → (padset, x, y, rot, footprint_relpath, value,
#        {padnum: net_name}) ──
LAYOUT = {
    # 'U1': ('DIP8', 25.0, 25.0, 0,
    #        'Package_DIP.pretty/DIP-8_W7.62mm.kicad_mod', 'NE555',
    #        {'1': 'GND', ...}),
}

BOARD_W, BOARD_H = 100.0, 70.0

def read_fp(rel):
    return open(os.path.join(KICAD_FP, rel), encoding='utf-8').read()

def parse_fp_children(raw):
    """Top-level children of a .kicad_mod, minus the (footprint "...") header.
    KiCad 9/10 .kicad_mod files contain version/generator attrs that are NOT
    valid inside a board-level footprint instance — drop them here."""
    nl = raw.find('\n')
    inner = raw[nl + 1:].rstrip()
    if inner.endswith(')'):
        inner = inner[:-1]
    children, i, n = [], 0, len(inner)
    while i < n:
        if inner[i] == '(':
            depth, j = 0, i
            while j < n:
                if inner[j] == '(':
                    depth += 1
                elif inner[j] == ')':
                    depth -= 1
                    if depth == 0:
                        break
                j += 1
            block = inner[i:j + 1]
            head = block.split(None, 1)[0][1:]
            if head not in ('version', 'generator', 'layer'):
                children.append(block)
            i = j + 1
        else:
            i += 1
    return children

def inject_pad_net(block, padnum, net_name):
    """Insert (net N "name") before a pad's final close paren.
    KiCad 9/10 pads have NO uuid field to anchor on — match the pad block by
    its opening (pad "N" and inject at ITS closing paren."""
    nc = NETS[net_name]
    m = re.search(r'\(pad\s+"' + re.escape(padnum) + r'"', block)
    if not m:
        return block
    depth, end = 0, m.start()
    for i in range(m.start(), len(block)):
        if block[i] == '(':
            depth += 1
        elif block[i] == ')':
            depth -= 1
            if depth == 0:
                end = i
                break
    return block[:end] + f'\n\t\t\t(net {nc} "{net_name}")' + block[end:]

def emit_footprint(ref, x, y, rot, fp_rel, value, net_map):
    raw = read_fp(fp_rel)
    children = parse_fp_children(raw)
    body = '\n\t'.join(c.replace('\n', '\n\t') for c in children)
    for padnum, net in net_map.items():
        if net:
            body = inject_pad_net(body, padnum, net)
    at = f'(at {x} {y} {rot})' if rot else f'(at {x} {y})'
    return (f'\t(footprint "{os.path.basename(fp_rel)}"\n'
            f'\t\t{at}\n\t\t(layer "F.Cu")\n'
            f'\t\t(property "Reference" "{ref}" (at 0 0 0) '
            f'(effects (font (size 1.27 1.27))))\n'
            f'\t\t(property "Value" "{value}" (at 0 0 0) '
            f'(effects (font (size 1.27 1.27))))\n'
            f'\t\t{body}\n\t)\n')

def emit_edge(w, h):
    pts = [(0, 0), (w, 0), (w, h), (0, h)]
    segs = []
    for (x1, y1), (x2, y2) in zip(pts, pts[1:] + [pts[0]]):
        segs.append(f'\t(gr_line (start {x1} {y1}) (end {x2} {y2}) '
                    f'(stroke (width 0.1) (type solid)) (layer "Edge.Cuts") '
                    f'(uuid "{uid()}"))')
    return '\n'.join(segs)

def generate(pcb_path, with_tracks=True):
    out = ['(kicad_pcb (version 20240108) (generator "codegen")',
           '\t(general (thickness 1.6))',
           '\t(paper "A4")',
           '\t(layers (0 "F.Cu" signal) (31 "B.Cu" signal) '
           '(44 "Edge.Cuts") (45 "F.SilkS") (46 "B.SilkS"))',
           ]
    # Net declarations
    for name, nc in sorted(NETS.items(), key=lambda kv: kv[1]):
        out.append(f'\t(net {nc} "{name}")')
    # Footprints
    for ref, (ps, x, y, rot, fp_rel, value, net_map) in LAYOUT.items():
        out.append(emit_footprint(ref, x, y, rot, fp_rel, value, net_map))
    # Edge
    out.append(emit_edge(BOARD_W, BOARD_H))
    # Tracks (see pcb_tools.emit_segment; design corridors first!)
    if with_tracks:
        pass  # tracks = [emit_segment(...)] ; out += tracks
    out.append('\t(embedded_fonts no)')
    out.append(')')
    text = '\n'.join(out) + '\n'
    open(pcb_path, 'w', encoding='utf-8').write(text)
    o, c, d = text.count('('), text.count(')'), text.count('(') - text.count(')')
    print(f'wrote {pcb_path} — paren balance {o}/{c} (must be 0, got {d})')

if __name__ == '__main__':
    # Always emit the layout-only reset point first
    generate('template-layout-only.kicad_pcb', with_tracks=False)
